"""
tests/test_strategy_condition_alerts.py
────────────────────────────────────────
Tests for engine/strategy_condition_monitor.py — strategy-condition alerts.

Covers:
  - StrategyCondition.evaluate() for all indicators (BB_PCT, VOLUME_RATIO, ADX, RSI)
  - All operators (ABOVE, BELOW, BETWEEN)
  - StrategyConditionMonitor: add_alert(), remove_alert(), list_alerts()
  - check_all() with mocked analyse()
  - Persistence: save/load from JSON
  - start_polling() daemon thread
  - compute_adx() helper
  - Edge cases: BETWEEN operator, unknown indicator, triggered alerts
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from analysis.technical import TechnicalSnapshot
from engine.strategy_condition_monitor import (
    StrategyAlert,
    StrategyCondition,
    StrategyConditionMonitor,
    compute_adx,
)


# ── Helpers ───────────────────────────────────────────────────


def make_snapshot(
    symbol: str = "RELIANCE",
    ltp: float = 2800.0,
    rsi: float = 55.0,
    bb_upper: float = 3000.0,
    bb_lower: float = 2600.0,
    bb_mid: float = 2800.0,
    volume_ratio: float = 1.2,
    atr: float = 50.0,
) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        symbol=symbol,
        ltp=ltp,
        rsi=rsi,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        bb_mid=bb_mid,
        volume_ratio=volume_ratio,
        atr=atr,
    )


def make_monitor(tmp_path: Path) -> StrategyConditionMonitor:
    """Create a StrategyConditionMonitor using a temp JSON file."""
    monitor = StrategyConditionMonitor.__new__(StrategyConditionMonitor)
    monitor._alerts_file = tmp_path / "strategy_alerts.json"
    monitor._alerts: list[StrategyAlert] = []
    monitor._polling = False
    monitor._poller_thread = None
    return monitor


# ── StrategyCondition.evaluate — BB_PCT ──────────────────────


class TestStrategyConditionBBPCT:
    """BB_PCT = (ltp - bb_lower) / (bb_upper - bb_lower)."""

    def test_bb_pct_above_passes(self):
        snap = make_snapshot(ltp=2900.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = (2900 - 2600) / (3000 - 2600) = 300/400 = 0.75
        cond = StrategyCondition(indicator="BB_PCT", operator="ABOVE", threshold=0.7)
        assert cond.evaluate(snap) is True

    def test_bb_pct_above_fails(self):
        snap = make_snapshot(ltp=2700.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = (2700 - 2600) / 400 = 0.25
        cond = StrategyCondition(indicator="BB_PCT", operator="ABOVE", threshold=0.7)
        assert cond.evaluate(snap) is False

    def test_bb_pct_below_passes(self):
        snap = make_snapshot(ltp=2650.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = (2650 - 2600) / 400 = 0.125
        cond = StrategyCondition(indicator="BB_PCT", operator="BELOW", threshold=0.3)
        assert cond.evaluate(snap) is True

    def test_bb_pct_below_fails(self):
        snap = make_snapshot(ltp=2900.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = 0.75, not below 0.3
        cond = StrategyCondition(indicator="BB_PCT", operator="BELOW", threshold=0.3)
        assert cond.evaluate(snap) is False

    def test_bb_pct_between_passes(self):
        snap = make_snapshot(ltp=2800.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = 0.5, between 0.4 and 0.6
        cond = StrategyCondition(
            indicator="BB_PCT", operator="BETWEEN", threshold=0.4, threshold2=0.6
        )
        assert cond.evaluate(snap) is True

    def test_bb_pct_between_fails_below(self):
        snap = make_snapshot(ltp=2640.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = 0.1, not between 0.4 and 0.6
        cond = StrategyCondition(
            indicator="BB_PCT", operator="BETWEEN", threshold=0.4, threshold2=0.6
        )
        assert cond.evaluate(snap) is False

    def test_bb_pct_between_fails_above(self):
        snap = make_snapshot(ltp=2960.0, bb_upper=3000.0, bb_lower=2600.0)
        # BB_PCT = 0.9, not between 0.4 and 0.6
        cond = StrategyCondition(
            indicator="BB_PCT", operator="BETWEEN", threshold=0.4, threshold2=0.6
        )
        assert cond.evaluate(snap) is False

    def test_bb_pct_zero_band_width_returns_false(self):
        """When bb_upper == bb_lower, should not crash and returns False."""
        snap = make_snapshot(ltp=2800.0, bb_upper=2800.0, bb_lower=2800.0)
        cond = StrategyCondition(indicator="BB_PCT", operator="ABOVE", threshold=0.5)
        assert cond.evaluate(snap) is False


# ── StrategyCondition.evaluate — VOLUME_RATIO ────────────────


class TestStrategyConditionVolumeRatio:
    def test_volume_above_passes(self):
        snap = make_snapshot(volume_ratio=2.5)
        cond = StrategyCondition(indicator="VOLUME_RATIO", operator="ABOVE", threshold=2.0)
        assert cond.evaluate(snap) is True

    def test_volume_above_fails(self):
        snap = make_snapshot(volume_ratio=1.2)
        cond = StrategyCondition(indicator="VOLUME_RATIO", operator="ABOVE", threshold=2.0)
        assert cond.evaluate(snap) is False

    def test_volume_below_passes(self):
        snap = make_snapshot(volume_ratio=0.8)
        cond = StrategyCondition(indicator="VOLUME_RATIO", operator="BELOW", threshold=1.0)
        assert cond.evaluate(snap) is True

    def test_volume_between_passes(self):
        snap = make_snapshot(volume_ratio=1.5)
        cond = StrategyCondition(
            indicator="VOLUME_RATIO", operator="BETWEEN", threshold=1.0, threshold2=2.0
        )
        assert cond.evaluate(snap) is True


# ── StrategyCondition.evaluate — RSI ─────────────────────────


class TestStrategyConditionRSI:
    def test_rsi_above_passes(self):
        snap = make_snapshot(rsi=72.0)
        cond = StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)
        assert cond.evaluate(snap) is True

    def test_rsi_above_fails(self):
        snap = make_snapshot(rsi=65.0)
        cond = StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)
        assert cond.evaluate(snap) is False

    def test_rsi_below_passes(self):
        snap = make_snapshot(rsi=28.0)
        cond = StrategyCondition(indicator="RSI", operator="BELOW", threshold=30.0)
        assert cond.evaluate(snap) is True

    def test_rsi_between_passes(self):
        snap = make_snapshot(rsi=55.0)
        cond = StrategyCondition(
            indicator="RSI", operator="BETWEEN", threshold=50.0, threshold2=60.0
        )
        assert cond.evaluate(snap) is True

    def test_rsi_between_fails(self):
        snap = make_snapshot(rsi=45.0)
        cond = StrategyCondition(
            indicator="RSI", operator="BETWEEN", threshold=50.0, threshold2=60.0
        )
        assert cond.evaluate(snap) is False


# ── StrategyCondition.evaluate — ADX ─────────────────────────


class TestStrategyConditionADX:
    def test_adx_above_passes(self):
        snap = make_snapshot()
        cond = StrategyCondition(indicator="ADX", operator="ABOVE", threshold=25.0)
        # ADX is fetched separately; snapshot stores it as adx attribute if present
        snap.adx = 30.0  # type: ignore[attr-defined]
        assert cond.evaluate(snap) is True

    def test_adx_below_passes(self):
        snap = make_snapshot()
        snap.adx = 20.0  # type: ignore[attr-defined]
        cond = StrategyCondition(indicator="ADX", operator="BELOW", threshold=25.0)
        assert cond.evaluate(snap) is True

    def test_adx_missing_returns_false(self):
        """If snapshot has no ADX value, evaluate should return False safely."""
        snap = make_snapshot()
        # No adx attribute set
        cond = StrategyCondition(indicator="ADX", operator="ABOVE", threshold=25.0)
        assert cond.evaluate(snap) is False


# ── StrategyCondition — unknown indicator ─────────────────────


class TestStrategyConditionUnknown:
    def test_unknown_indicator_returns_false(self):
        snap = make_snapshot()
        cond = StrategyCondition(indicator="UNKNOWN_IND", operator="ABOVE", threshold=10.0)
        assert cond.evaluate(snap) is False


# ── compute_adx helper ────────────────────────────────────────


class TestComputeADX:
    def _make_ohlcv(self, n: int = 50) -> pd.DataFrame:
        np.random.seed(0)
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        close = 100 + np.cumsum(np.random.randn(n))
        high = close + np.abs(np.random.randn(n))
        low = close - np.abs(np.random.randn(n))
        volume = np.random.randint(500_000, 2_000_000, n)
        return pd.DataFrame(
            {"open": close, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )

    def test_compute_adx_returns_float(self):
        df = self._make_ohlcv()
        result = compute_adx(df)
        assert isinstance(result, float)

    def test_compute_adx_in_valid_range(self):
        df = self._make_ohlcv(100)
        result = compute_adx(df)
        assert 0.0 <= result <= 100.0

    def test_compute_adx_insufficient_data_returns_zero(self):
        df = self._make_ohlcv(5)  # too few rows
        result = compute_adx(df)
        assert result == 0.0


# ── StrategyConditionMonitor: CRUD ────────────────────────────


class TestStrategyConditionMonitorCRUD:
    def test_add_alert_returns_strategy_alert(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor.add_alert("RELIANCE", "NSE", "Momentum", conditions)
        assert isinstance(alert, StrategyAlert)
        assert alert.symbol == "RELIANCE"
        assert alert.exchange == "NSE"
        assert alert.strategy_name == "Momentum"
        assert len(alert.conditions) == 1

    def test_add_alert_gets_unique_id(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        a1 = monitor.add_alert("RELIANCE", "NSE", "Strat1", conditions)
        a2 = monitor.add_alert("INFY", "NSE", "Strat2", conditions)
        assert a1.id != a2.id

    def test_list_alerts_returns_all(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        monitor.add_alert("RELIANCE", "NSE", "S1", conditions)
        monitor.add_alert("INFY", "NSE", "S2", conditions)
        alerts = monitor.list_alerts()
        assert len(alerts) == 2

    def test_list_alerts_excludes_triggered(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor.add_alert("RELIANCE", "NSE", "S1", conditions)
        alert.triggered = True
        alerts = monitor.list_alerts()
        assert len(alerts) == 0

    def test_remove_alert_returns_true(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor.add_alert("RELIANCE", "NSE", "S1", conditions)
        result = monitor.remove_alert(alert.id)
        assert result is True
        assert len(monitor.list_alerts()) == 0

    def test_remove_alert_missing_returns_false(self, tmp_path):
        monitor = make_monitor(tmp_path)
        result = monitor.remove_alert("nonexistent-id")
        assert result is False


# ── StrategyConditionMonitor: check_all ──────────────────────


class TestStrategyConditionMonitorCheckAll:
    def test_check_all_triggers_when_conditions_met(self, tmp_path):
        monitor = make_monitor(tmp_path)
        snap = make_snapshot(rsi=75.0)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        monitor.add_alert("RELIANCE", "NSE", "RSI Strategy", conditions)

        with patch("engine.strategy_condition_monitor.analyse", return_value=snap):
            triggered = monitor.check_all()

        assert len(triggered) == 1
        assert triggered[0].symbol == "RELIANCE"
        assert triggered[0].triggered is True
        assert triggered[0].triggered_at is not None

    def test_check_all_does_not_trigger_when_condition_not_met(self, tmp_path):
        monitor = make_monitor(tmp_path)
        snap = make_snapshot(rsi=60.0)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        monitor.add_alert("RELIANCE", "NSE", "RSI Strategy", conditions)

        with patch("engine.strategy_condition_monitor.analyse", return_value=snap):
            triggered = monitor.check_all()

        assert len(triggered) == 0

    def test_check_all_all_conditions_must_pass(self, tmp_path):
        """Alert fires only when ALL conditions are met (AND logic)."""
        monitor = make_monitor(tmp_path)
        snap = make_snapshot(rsi=75.0, volume_ratio=1.2)  # vol_ratio too low
        conditions = [
            StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0),
            StrategyCondition(indicator="VOLUME_RATIO", operator="ABOVE", threshold=2.0),
        ]
        monitor.add_alert("RELIANCE", "NSE", "Combined", conditions)

        with patch("engine.strategy_condition_monitor.analyse", return_value=snap):
            triggered = monitor.check_all()

        assert len(triggered) == 0

    def test_check_all_skips_already_triggered(self, tmp_path):
        monitor = make_monitor(tmp_path)
        snap = make_snapshot(rsi=75.0)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor.add_alert("RELIANCE", "NSE", "RSI Strategy", conditions)
        alert.triggered = True  # already triggered

        with patch("engine.strategy_condition_monitor.analyse", return_value=snap):
            triggered = monitor.check_all()

        assert len(triggered) == 0

    def test_check_all_handles_analyse_exception(self, tmp_path):
        """check_all() should not crash when analyse() raises an exception."""
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        monitor.add_alert("RELIANCE", "NSE", "RSI Strategy", conditions)

        with patch(
            "engine.strategy_condition_monitor.analyse", side_effect=Exception("network error")
        ):
            triggered = monitor.check_all()

        assert triggered == []


# ── Persistence ───────────────────────────────────────────────


class TestStrategyConditionMonitorPersistence:
    def test_add_alert_saves_to_json(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        monitor.add_alert("RELIANCE", "NSE", "S1", conditions)
        assert monitor._alerts_file.exists()
        data = json.loads(monitor._alerts_file.read_text())
        assert len(data) == 1
        assert data[0]["symbol"] == "RELIANCE"

    def test_load_alerts_from_json(self, tmp_path):
        monitor1 = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor1.add_alert("RELIANCE", "NSE", "S1", conditions)

        # Create a new monitor from the same file
        monitor2 = make_monitor(tmp_path)
        monitor2._load()
        alerts = monitor2.list_alerts()
        assert len(alerts) == 1
        assert alerts[0].id == alert.id
        assert alerts[0].symbol == "RELIANCE"

    def test_remove_alert_updates_json(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0)]
        alert = monitor.add_alert("RELIANCE", "NSE", "S1", conditions)
        monitor.remove_alert(alert.id)
        data = json.loads(monitor._alerts_file.read_text())
        assert len(data) == 0

    def test_conditions_survive_json_roundtrip(self, tmp_path):
        monitor = make_monitor(tmp_path)
        conditions = [
            StrategyCondition(indicator="RSI", operator="ABOVE", threshold=70.0),
            StrategyCondition(indicator="BB_PCT", operator="BELOW", threshold=0.2),
        ]
        monitor.add_alert("INFY", "NSE", "Multi", conditions)

        monitor2 = make_monitor(tmp_path)
        monitor2._load()
        loaded = monitor2.list_alerts()[0]
        assert len(loaded.conditions) == 2
        assert loaded.conditions[0].indicator == "RSI"
        assert loaded.conditions[1].threshold == 0.2


# ── start_polling ─────────────────────────────────────────────


class TestStartPolling:
    def test_start_polling_launches_daemon_thread(self, tmp_path):
        monitor = make_monitor(tmp_path)
        with patch.object(monitor, "check_all", return_value=[]):
            monitor.start_polling(interval_seconds=3600)
            assert monitor._poller_thread is not None
            assert monitor._poller_thread.is_alive()
            assert monitor._poller_thread.daemon is True
            monitor._polling = False  # signal stop

    def test_start_polling_idempotent(self, tmp_path):
        """Calling start_polling twice should not create a second thread."""
        monitor = make_monitor(tmp_path)
        with patch.object(monitor, "check_all", return_value=[]):
            monitor.start_polling(interval_seconds=3600)
            first_thread = monitor._poller_thread
            monitor.start_polling(interval_seconds=3600)
            assert monitor._poller_thread is first_thread
            monitor._polling = False
