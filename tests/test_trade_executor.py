"""Tests for engine/trade_executor.py — live/paper mode detection and order execution."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from brokers.base import OrderResponse, UserProfile
from engine.trade_executor import (
    _is_paper,
    _trading_mode_override,
    execute_trade_plan,
    is_live_execution_allowed,
)
from engine.trader import ExitPlan, OrderLeg, TradePlan


@pytest.fixture(autouse=True)
def bypass_risk_limits(tmp_path, monkeypatch):
    """Isolate risk limits to a fresh temp DB for trade executor tests."""
    monkeypatch.setenv("RISK_DB_PATH", str(tmp_path / "risk_test.db"))
    # Reset the module-level singleton so it picks up the temp DB
    import engine.risk_limits as rl_mod

    rl_mod.risk_limits = rl_mod.RiskLimits()
    yield
    rl_mod.risk_limits = rl_mod.RiskLimits()


# ── Helpers ───────────────────────────────────────────────────


def _make_broker(broker_name: str) -> MagicMock:
    """Return a mock BrokerAPI with a given broker name in the profile."""
    broker = MagicMock()
    broker.get_profile.return_value = UserProfile(
        user_id="U001",
        name="Test User",
        email="test@example.com",
        broker=broker_name,
    )
    broker.place_order.return_value = OrderResponse(
        order_id="ORD123",
        status="COMPLETE",
        message="Order placed",
    )
    return broker


def _make_plan(n_legs: int = 1, with_exit: bool = True) -> TradePlan:
    """Return a minimal TradePlan with n_legs OrderLegs."""
    legs = [
        OrderLeg(
            action="BUY",
            instrument="RELIANCE",
            exchange="NSE",
            product="CNC",
            order_type="MARKET",
            quantity=10,
        )
        for _ in range(n_legs)
    ]
    exit_plan = (
        ExitPlan(
            stop_loss=2400.0,
            stop_loss_pct=-2.0,
            stop_loss_type="FIXED",
            target_1=2600.0,
            target_1_pct=4.0,
        )
        if with_exit
        else None
    )
    return TradePlan(
        symbol="RELIANCE",
        exchange="NSE",
        timestamp="2026-04-04T09:15:00",
        strategy_name="Delivery Buy",
        direction="LONG",
        instrument_type="EQUITY",
        timeframe="SWING",
        capital_deployed=25000.0,
        capital_pct=10.0,
        max_risk=500.0,
        risk_pct=2.0,
        reward_risk=2.0,
        entry_orders=legs,
        exit_plan=exit_plan,
    )


# ── _is_paper ────────────────────────────────────────────────


class TestIsPaper:
    def test_paper_broker(self):
        assert _is_paper(_make_broker("PAPER")) is True

    def test_mock_broker(self):
        assert _is_paper(_make_broker("MOCK")) is True

    def test_demo_broker(self):
        assert _is_paper(_make_broker("DEMO")) is True

    def test_fyers_broker_is_not_paper(self):
        assert _is_paper(_make_broker("FYERS")) is False

    def test_zerodha_broker_is_not_paper(self):
        assert _is_paper(_make_broker("ZERODHA")) is False

    def test_exception_defaults_to_paper(self):
        broker = MagicMock()
        broker.get_profile.side_effect = RuntimeError("network error")
        assert _is_paper(broker) is True


# ── _trading_mode_override ───────────────────────────────────


class TestTradingModeOverride:
    def test_default_is_paper(self):
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert _trading_mode_override() == "PAPER"

    def test_env_live(self):
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            assert _trading_mode_override() == "LIVE"

    def test_env_paper(self):
        with patch.dict(os.environ, {"TRADING_MODE": "PAPER"}):
            assert _trading_mode_override() == "PAPER"

    def test_env_case_insensitive(self):
        with patch.dict(os.environ, {"TRADING_MODE": "live"}):
            assert _trading_mode_override() == "LIVE"


# ── is_live_execution_allowed ────────────────────────────────


class TestIsLiveExecutionAllowed:
    def test_paper_broker_never_live(self):
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            assert is_live_execution_allowed(_make_broker("PAPER")) is False

    def test_live_broker_with_paper_env_is_not_live(self):
        with patch.dict(os.environ, {"TRADING_MODE": "PAPER"}):
            assert is_live_execution_allowed(_make_broker("FYERS")) is False

    def test_live_broker_with_live_env_is_allowed(self):
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            assert is_live_execution_allowed(_make_broker("FYERS")) is True

    def test_live_broker_with_default_env_is_not_live(self):
        """Default TRADING_MODE is PAPER — live broker still blocked."""
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            assert is_live_execution_allowed(_make_broker("FYERS")) is False


# ── execute_trade_plan ───────────────────────────────────────


class TestExecuteTradePlan:
    def test_none_plan_returns_empty(self):
        broker = _make_broker("PAPER")
        result = execute_trade_plan(None, broker)
        assert result == []
        broker.place_order.assert_not_called()

    def test_paper_broker_executes_without_confirmation(self):
        broker = _make_broker("PAPER")
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            result = execute_trade_plan(_make_plan(), broker)
        assert len(result) == 1
        assert result[0]["status"] == "COMPLETE"
        assert result[0]["mode"] == "PAPER"
        broker.place_order.assert_called_once()

    def test_paper_broker_multiple_legs(self):
        broker = _make_broker("PAPER")
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            result = execute_trade_plan(_make_plan(n_legs=3), broker)
        assert len(result) == 3
        assert broker.place_order.call_count == 3

    def test_live_broker_cancelled_returns_empty(self):
        """If user cancels the confirmation, no orders placed."""
        broker = _make_broker("FYERS")
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            with patch("engine.trade_executor.Confirm.ask", return_value=False):
                result = execute_trade_plan(_make_plan(), broker)
        assert result == []
        broker.place_order.assert_not_called()

    def test_live_broker_confirmed_places_order(self):
        broker = _make_broker("FYERS")
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            with patch("engine.trade_executor.Confirm.ask", return_value=True):
                result = execute_trade_plan(_make_plan(), broker)
        assert len(result) == 1
        assert result[0]["mode"] == "LIVE"
        assert result[0]["status"] == "COMPLETE"
        broker.place_order.assert_called_once()

    def test_skip_confirmation_bypasses_prompt(self):
        """skip_confirmation=True skips the Confirm.ask entirely for live brokers."""
        broker = _make_broker("FYERS")
        with patch.dict(os.environ, {"TRADING_MODE": "LIVE"}):
            with patch("engine.trade_executor.Confirm.ask") as mock_confirm:
                result = execute_trade_plan(_make_plan(), broker, skip_confirmation=True)
        mock_confirm.assert_not_called()
        assert len(result) == 1
        assert result[0]["mode"] == "LIVE"

    def test_failed_order_recorded_in_results(self):
        broker = _make_broker("PAPER")
        broker.place_order.side_effect = RuntimeError("API timeout")
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            result = execute_trade_plan(_make_plan(), broker)
        assert len(result) == 1
        assert result[0]["status"] == "FAILED"
        assert "API timeout" in result[0]["message"]

    def test_result_contains_expected_fields(self):
        broker = _make_broker("PAPER")
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            result = execute_trade_plan(_make_plan(), broker)
        r = result[0]
        assert "order_id" in r
        assert "symbol" in r
        assert "action" in r
        assert "quantity" in r
        assert "status" in r
        assert "mode" in r

    def test_plan_without_exit_still_executes(self):
        broker = _make_broker("PAPER")
        env = {k: v for k, v in os.environ.items() if k != "TRADING_MODE"}
        with patch.dict(os.environ, env, clear=True):
            result = execute_trade_plan(_make_plan(with_exit=False), broker)
        assert len(result) == 1
        assert result[0]["status"] == "COMPLETE"

    def test_trading_mode_paper_env_shows_warning_for_live_broker(self, capsys):
        """When TRADING_MODE=PAPER but a live broker is connected, a warning is shown."""
        broker = _make_broker("FYERS")
        with patch.dict(os.environ, {"TRADING_MODE": "PAPER"}):
            result = execute_trade_plan(_make_plan(), broker)
        # Orders still execute (as paper)
        assert len(result) == 1
        assert result[0]["mode"] == "PAPER"
