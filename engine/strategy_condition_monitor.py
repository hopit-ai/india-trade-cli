"""
engine/strategy_condition_monitor.py
─────────────────────────────────────
Strategy-condition alerts: fire an alert when all entry conditions for a saved
strategy are simultaneously met (Bollinger Band position, volume surge, ADX
threshold, RSI level).

Usage:
    from engine.strategy_condition_monitor import strategy_condition_monitor

    conditions = [
        StrategyCondition(indicator="RSI",          operator="ABOVE", threshold=70),
        StrategyCondition(indicator="VOLUME_RATIO",  operator="ABOVE", threshold=2.0),
        StrategyCondition(indicator="BB_PCT",        operator="BELOW", threshold=0.2),
    ]
    strategy_condition_monitor.add_alert("RELIANCE", "NSE", "Oversold Bounce", conditions)
    strategy_condition_monitor.start_polling(interval_seconds=300)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from analysis.technical import TechnicalSnapshot, analyse

STRATEGY_ALERTS_FILE = Path.home() / ".trading_platform" / "strategy_alerts.json"

# Minimum rows needed to compute reliable 14-period ADX
_ADX_MIN_ROWS = 28


# ── ADX helper ────────────────────────────────────────────────


def compute_adx(df: pd.DataFrame, period: int = 14) -> float:
    """
    Compute the 14-period ADX from an OHLCV DataFrame.

    Uses standard Wilder's smoothing (same as most charting platforms).
    Returns 0.0 when there is insufficient data.

    Parameters
    ----------
    df : DataFrame with columns open, high, low, close, volume
    period : smoothing period (default 14)
    """
    if df is None or len(df) < _ADX_MIN_ROWS:
        return 0.0

    high = df["high"]
    low = df["low"]
    close = df["close"]

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional movement
    up_move = high.diff()
    down_move = (-low).diff()  # note: low decreasing = positive down-move

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm_s = pd.Series(plus_dm, index=df.index)
    minus_dm_s = pd.Series(minus_dm, index=df.index)

    # Wilder's smoothing: first value = sum of first `period` values
    def wilder_smooth(series: pd.Series, p: int) -> pd.Series:
        result = pd.Series(np.nan, index=series.index)
        # First smoothed value
        result.iloc[p] = series.iloc[1 : p + 1].sum()
        for i in range(p + 1, len(series)):
            result.iloc[i] = result.iloc[i - 1] - result.iloc[i - 1] / p + series.iloc[i]
        return result

    atr_s = wilder_smooth(tr, period)
    plus_dm_smooth = wilder_smooth(plus_dm_s, period)
    minus_dm_smooth = wilder_smooth(minus_dm_s, period)

    # DI lines
    plus_di = 100 * plus_dm_smooth / atr_s.replace(0, np.nan)
    minus_di = 100 * minus_dm_smooth / atr_s.replace(0, np.nan)

    # DX
    di_sum = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / di_sum.replace(0, np.nan)

    # ADX = Wilder's smooth of DX
    adx_s = wilder_smooth(dx.fillna(0), period)

    last_val = adx_s.dropna()
    if last_val.empty:
        return 0.0

    result_val = float(last_val.iloc[-1])
    # Clamp to valid range
    return max(0.0, min(100.0, result_val))


# ── Data model ────────────────────────────────────────────────


@dataclass
class StrategyCondition:
    """A single evaluatable entry condition."""

    indicator: str  # "BB_PCT" | "VOLUME_RATIO" | "ADX" | "RSI"
    operator: str  # "ABOVE" | "BELOW" | "BETWEEN"
    threshold: float
    threshold2: float = 0.0  # only used for BETWEEN

    def evaluate(self, snapshot: TechnicalSnapshot) -> bool:
        """
        Evaluate this condition against a TechnicalSnapshot.

        BB_PCT = (ltp - bb_lower) / (bb_upper - bb_lower)
          0.0 = price at lower band, 1.0 = price at upper band

        Returns False if the indicator is unknown or value is unavailable.
        """
        indicator = self.indicator.upper()
        operator = self.operator.upper()

        value = self._extract_value(indicator, snapshot)
        if value is None:
            return False

        if operator == "ABOVE":
            return value >= self.threshold
        elif operator == "BELOW":
            return value <= self.threshold
        elif operator == "BETWEEN":
            return self.threshold <= value <= self.threshold2
        return False

    def _extract_value(self, indicator: str, snapshot: TechnicalSnapshot) -> Optional[float]:
        if indicator == "BB_PCT":
            band_width = snapshot.bb_upper - snapshot.bb_lower
            if band_width == 0:
                return None
            return (snapshot.ltp - snapshot.bb_lower) / band_width

        if indicator == "VOLUME_RATIO":
            return snapshot.volume_ratio

        if indicator == "RSI":
            return snapshot.rsi

        if indicator == "ADX":
            # ADX is not part of the standard TechnicalSnapshot; it may be
            # attached dynamically (e.g., by check_all) or as an attribute.
            return getattr(snapshot, "adx", None)

        return None


@dataclass
class StrategyAlert:
    """Alert that fires when all conditions are met for a symbol."""

    id: str
    symbol: str
    exchange: str
    strategy_name: str
    conditions: list[StrategyCondition]
    created_at: str
    triggered: bool = False
    triggered_at: Optional[str] = None


# ── Serialisation helpers ─────────────────────────────────────


def _alert_to_dict(alert: StrategyAlert) -> dict:
    return {
        "id": alert.id,
        "symbol": alert.symbol,
        "exchange": alert.exchange,
        "strategy_name": alert.strategy_name,
        "conditions": [asdict(c) for c in alert.conditions],
        "created_at": alert.created_at,
        "triggered": alert.triggered,
        "triggered_at": alert.triggered_at,
    }


def _alert_from_dict(d: dict) -> StrategyAlert:
    conditions = [StrategyCondition(**c) for c in d.get("conditions", [])]
    return StrategyAlert(
        id=d["id"],
        symbol=d["symbol"],
        exchange=d["exchange"],
        strategy_name=d["strategy_name"],
        conditions=conditions,
        created_at=d["created_at"],
        triggered=d.get("triggered", False),
        triggered_at=d.get("triggered_at"),
    )


# ── Monitor ───────────────────────────────────────────────────


class StrategyConditionMonitor:
    """
    Manages StrategyAlert objects.

    Persistence: ~/.trading_platform/strategy_alerts.json
    """

    def __init__(self) -> None:
        self._alerts_file: Path = STRATEGY_ALERTS_FILE
        self._alerts: list[StrategyAlert] = []
        self._polling: bool = False
        self._poller_thread: Optional[threading.Thread] = None
        self._load()

    # ── Public API ────────────────────────────────────────────

    def add_alert(
        self,
        symbol: str,
        exchange: str,
        strategy_name: str,
        conditions: list[StrategyCondition],
    ) -> StrategyAlert:
        """Create and persist a new strategy alert."""
        alert = StrategyAlert(
            id=str(uuid.uuid4())[:8],
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            strategy_name=strategy_name,
            conditions=list(conditions),
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._alerts.append(alert)
        self._save()
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by id. Returns True if found and removed."""
        before = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.id != alert_id]
        removed = len(self._alerts) < before
        if removed:
            self._save()
        return removed

    def list_alerts(self) -> list[StrategyAlert]:
        """Return all non-triggered alerts."""
        return [a for a in self._alerts if not a.triggered]

    def check_all(self) -> list[StrategyAlert]:
        """
        Evaluate every active alert against current market data.

        For each unique symbol, fetches a TechnicalSnapshot via analyse().
        If any alert needs ADX, fetches OHLCV and computes it on the fly.

        Returns the list of alerts that just triggered.
        """
        just_triggered: list[StrategyAlert] = []
        active = [a for a in self._alerts if not a.triggered]
        if not active:
            return just_triggered

        # Group by symbol to avoid redundant fetches
        symbols: dict[tuple[str, str], TechnicalSnapshot | None] = {}
        for alert in active:
            key = (alert.symbol, alert.exchange)
            if key not in symbols:
                symbols[key] = None

        # Fetch snapshots
        for sym, exch in list(symbols.keys()):
            try:
                snap = analyse(sym, exch)
                symbols[(sym, exch)] = snap
            except Exception:
                symbols[(sym, exch)] = None

        # Fetch ADX lazily for symbols that need it
        adx_cache: dict[tuple[str, str], float] = {}

        for alert in active:
            key = (alert.symbol, alert.exchange)
            snap = symbols.get(key)
            if snap is None:
                continue

            # Attach ADX if any condition needs it
            needs_adx = any(c.indicator.upper() == "ADX" for c in alert.conditions)
            if needs_adx and key not in adx_cache:
                adx_cache[key] = self._fetch_adx(alert.symbol, alert.exchange)
            if needs_adx:
                snap.adx = adx_cache[key]  # type: ignore[attr-defined]

            # Evaluate all conditions (AND logic)
            try:
                all_met = all(cond.evaluate(snap) for cond in alert.conditions)
            except Exception:
                all_met = False

            if all_met:
                alert.triggered = True
                alert.triggered_at = datetime.now().isoformat(timespec="seconds")
                just_triggered.append(alert)

        if just_triggered:
            self._save()

        return just_triggered

    def start_polling(self, interval_seconds: int = 300) -> None:
        """
        Start a daemon thread that calls check_all() every interval_seconds.

        Idempotent: calling again while already polling has no effect.
        """
        if self._polling:
            return
        self._polling = True
        self._poller_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_seconds,),
            daemon=True,
        )
        self._poller_thread.start()

    def stop_polling(self) -> None:
        """Signal the polling thread to stop."""
        self._polling = False

    # ── Private ───────────────────────────────────────────────

    def _poll_loop(self, interval_seconds: int) -> None:
        while self._polling:
            try:
                self.check_all()
            except Exception:
                pass
            time.sleep(interval_seconds)

    @staticmethod
    def _fetch_adx(symbol: str, exchange: str) -> float:
        """Fetch OHLCV and compute ADX. Returns 0.0 on failure."""
        try:
            from market.history import get_ohlcv

            df = get_ohlcv(symbol=symbol, exchange=exchange, days=60)
            return compute_adx(df)
        except Exception:
            return 0.0

    # ── Persistence ───────────────────────────────────────────

    def _save(self) -> None:
        try:
            self._alerts_file.parent.mkdir(parents=True, exist_ok=True)
            data = [_alert_to_dict(a) for a in self._alerts]
            self._alerts_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load(self) -> None:
        try:
            if self._alerts_file.exists():
                data = json.loads(self._alerts_file.read_text())
                self._alerts = [_alert_from_dict(d) for d in data]
        except Exception:
            self._alerts = []


# ── Singleton ─────────────────────────────────────────────────

strategy_condition_monitor = StrategyConditionMonitor()
