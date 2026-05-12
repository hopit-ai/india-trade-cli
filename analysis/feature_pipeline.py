"""
analysis/feature_pipeline.py
─────────────────────────────
Compute-once, cache, reuse feature pipeline for technical indicators.

All analysts call get_features(symbol) instead of fetching OHLCV individually.
Cache TTL = 60 seconds (intraday freshness).

Usage:
    from analysis.feature_pipeline import get_features, FeatureSet

    fs = get_features("INFY")
    print(fs.rsi, fs.atr_pct, fs.bb_pct, fs.adx)
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import pandas as pd

from market.history import get_ohlcv


# ── FeatureSet ────────────────────────────────────────────────


@dataclass
class FeatureSet:
    symbol: str
    exchange: str
    timestamp: float  # time.time() when computed

    # Price
    ltp: float = 0.0
    prev_close: float = 0.0
    change_pct: float = 0.0

    # Trend
    ema20: float = 0.0
    ema50: float = 0.0
    sma200: float = 0.0
    ema_slope_5d: float = 0.0  # (ema20[-1] - ema20[-5]) / ema20[-5] as %

    # Momentum
    rsi: float = 50.0
    rsi_slope_3d: float = 0.0  # RSI[-1] - RSI[-3]
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0

    # Volatility
    atr: float = 0.0
    atr_pct: float = 0.0  # ATR / ltp * 100
    bb_upper: float = 0.0
    bb_lower: float = 0.0
    bb_mid: float = 0.0
    bb_pct: float = 0.5  # (close - bb_lower) / (bb_upper - bb_lower)
    bb_width: float = 0.0  # (bb_upper - bb_lower) / bb_mid * 100

    # Volume
    volume_ratio: float = 1.0  # today / 20d avg
    volume_trend: float = 0.0  # 5d avg volume / 20d avg volume

    # Trend strength
    adx: float = 0.0  # 14-period ADX

    # Support/Resistance
    support: float = 0.0
    resistance: float = 0.0

    @property
    def is_fresh(self) -> bool:
        """True if computed within the last 60 seconds."""
        return (time.time() - self.timestamp) < 60.0

    def to_dict(self) -> dict:
        """Serialise to plain dict (for LLM context injection)."""
        return asdict(self)


# ── FeatureCache ──────────────────────────────────────────────


class FeatureCache:
    """Thread-safe in-memory cache keyed by (symbol, exchange)."""

    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, str], FeatureSet] = {}
        self._lock = threading.Lock()

    def get(self, symbol: str, exchange: str) -> Optional[FeatureSet]:
        with self._lock:
            fs = self._store.get((symbol, exchange))
            if fs is None:
                return None
            if (time.time() - fs.timestamp) >= self._ttl:
                del self._store[(symbol, exchange)]
                return None
            return fs

    def set(self, fs: FeatureSet) -> None:
        with self._lock:
            self._store[(fs.symbol, fs.exchange)] = fs

    def invalidate(self, symbol: str, exchange: str) -> None:
        with self._lock:
            self._store.pop((symbol, exchange), None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Module-level singleton
_cache = FeatureCache()


# ── ADX (Wilder's 14-period) ──────────────────────────────────


def _compute_adx(df: pd.DataFrame, period: int = 14) -> float:
    """
    Compute 14-period Wilder's ADX using pure pandas/numpy.

    Steps:
      1. True Range = max(high-low, |high-prev_close|, |low-prev_close|)
      2. +DM = high - prev_high  if > 0 and > (prev_low - low), else 0
      3. -DM = prev_low - low    if > 0 and > (high - prev_high), else 0
      4. Smooth TR, +DM, -DM with Wilder's EWM (alpha = 1/period)
      5. +DI = 100 * smooth_+DM / smooth_TR
      6. -DI = 100 * smooth_-DM / smooth_TR
      7. DX  = 100 * |+DI - -DI| / (+DI + -DI)
      8. ADX = Wilder EWM of DX
    """
    if len(df) < period * 2:
        return 0.0

    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Directional movement
    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm_s = pd.Series(plus_dm, index=df.index)
    minus_dm_s = pd.Series(minus_dm, index=df.index)

    # Wilder smoothing (alpha = 1/period)
    alpha = 1.0 / period
    smooth_tr = tr.ewm(alpha=alpha, adjust=False).mean()
    smooth_plus = plus_dm_s.ewm(alpha=alpha, adjust=False).mean()
    smooth_minus = minus_dm_s.ewm(alpha=alpha, adjust=False).mean()

    # Directional indices
    plus_di = 100 * smooth_plus / smooth_tr.replace(0, np.nan)
    minus_di = 100 * smooth_minus / smooth_tr.replace(0, np.nan)

    di_sum = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum

    # ADX = Wilder EWM of DX
    adx_series = dx.ewm(alpha=alpha, adjust=False).mean()

    val = float(adx_series.iloc[-1])
    if np.isnan(val) or np.isinf(val):
        return 0.0
    return max(0.0, min(100.0, val))


# ── compute_features ─────────────────────────────────────────


def compute_features(
    symbol: str,
    exchange: str = "NSE",
    df: Optional[pd.DataFrame] = None,
    period: str = "3mo",
) -> FeatureSet:
    """
    Compute all features from OHLCV.

    - If df is None, calls get_ohlcv(symbol, period, exchange)
    - ADX: 14-period Wilder's ADX using pure pandas
    """
    if df is None:
        df = get_ohlcv(symbol=symbol, exchange=exchange, days=90)

    if df.empty or len(df) < 20:
        return FeatureSet(symbol=symbol, exchange=exchange, timestamp=time.time())

    close = df["close"]
    ltp = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else ltp
    change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close else 0.0

    # ── EMA / SMA ─────────────────────────────────────────────
    ema20_s = close.ewm(span=20, adjust=False).mean()
    ema50_s = close.ewm(span=50, adjust=False).mean()
    sma200_val = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else 0.0

    ema20_val = float(ema20_s.iloc[-1])
    ema50_val = float(ema50_s.iloc[-1])

    # EMA slope: (ema20[-1] - ema20[-5]) / ema20[-5] * 100
    if len(ema20_s) >= 5 and float(ema20_s.iloc[-5]) != 0:
        ema_slope_5d = (
            (float(ema20_s.iloc[-1]) - float(ema20_s.iloc[-5])) / float(ema20_s.iloc[-5]) * 100
        )
    else:
        ema_slope_5d = 0.0

    # ── RSI ───────────────────────────────────────────────────
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi_val = float(rsi_series.iloc[-1])
    if np.isnan(rsi_val):
        rsi_val = 50.0

    # RSI slope: RSI[-1] - RSI[-3]
    if len(rsi_series) >= 3 and not np.isnan(float(rsi_series.iloc[-3])):
        rsi_slope_3d = float(rsi_series.iloc[-1]) - float(rsi_series.iloc[-3])
    else:
        rsi_slope_3d = 0.0

    # ── MACD ─────────────────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line

    macd_val = float(macd_line.iloc[-1])
    macd_signal_val = float(signal_line.iloc[-1])
    macd_hist_val = float(histogram.iloc[-1])

    # ── ATR ───────────────────────────────────────────────────
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - close.shift()).abs()
    low_close = (df["low"] - close.shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_series = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    atr_val = float(atr_series.iloc[-1])
    if np.isnan(atr_val) or atr_val < 0:
        atr_val = 0.0
    atr_pct = (atr_val / ltp * 100) if ltp else 0.0

    # ── Bollinger Bands ───────────────────────────────────────
    bb_mid_s = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper_s = bb_mid_s + 2 * bb_std
    bb_lower_s = bb_mid_s - 2 * bb_std

    bb_upper_val = float(bb_upper_s.iloc[-1])
    bb_lower_val = float(bb_lower_s.iloc[-1])
    bb_mid_val = float(bb_mid_s.iloc[-1])

    bb_band = bb_upper_val - bb_lower_val
    if bb_band > 0:
        bb_pct = (ltp - bb_lower_val) / bb_band
    else:
        bb_pct = 0.5
    bb_width = (bb_band / bb_mid_val * 100) if bb_mid_val else 0.0

    # ── Volume ────────────────────────────────────────────────
    vol = df["volume"]
    vol_20avg = float(vol.rolling(20).mean().iloc[-1])
    vol_today = float(vol.iloc[-1])
    volume_ratio = (vol_today / vol_20avg) if vol_20avg else 1.0

    vol_5avg = float(vol.rolling(5).mean().iloc[-1])
    volume_trend = (vol_5avg / vol_20avg) if vol_20avg else 0.0

    # ── ADX ───────────────────────────────────────────────────
    adx_val = _compute_adx(df)

    # ── Support / Resistance (pivot points) ───────────────────
    prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
    h, lo, c = float(prev["high"]), float(prev["low"]), float(prev["close"])
    pivot = (h + lo + c) / 3
    support = round(2 * pivot - h, 2)
    resistance = round(2 * pivot - lo, 2)

    return FeatureSet(
        symbol=symbol,
        exchange=exchange,
        timestamp=time.time(),
        ltp=round(ltp, 4),
        prev_close=round(prev_close, 4),
        change_pct=round(change_pct, 4),
        ema20=round(ema20_val, 4),
        ema50=round(ema50_val, 4),
        sma200=round(sma200_val, 4),
        ema_slope_5d=round(ema_slope_5d, 4),
        rsi=round(rsi_val, 4),
        rsi_slope_3d=round(rsi_slope_3d, 4),
        macd=round(macd_val, 6),
        macd_signal=round(macd_signal_val, 6),
        macd_hist=round(macd_hist_val, 6),
        atr=round(atr_val, 4),
        atr_pct=round(atr_pct, 4),
        bb_upper=round(bb_upper_val, 4),
        bb_lower=round(bb_lower_val, 4),
        bb_mid=round(bb_mid_val, 4),
        bb_pct=round(bb_pct, 6),
        bb_width=round(bb_width, 4),
        volume_ratio=round(volume_ratio, 4),
        volume_trend=round(volume_trend, 4),
        adx=round(adx_val, 4),
        support=support,
        resistance=resistance,
    )


# ── get_features ─────────────────────────────────────────────


def get_features(
    symbol: str,
    exchange: str = "NSE",
    force_refresh: bool = False,
) -> FeatureSet:
    """
    Return cached FeatureSet if fresh, else compute and cache.
    Thread-safe. Returns a zero-filled FeatureSet on any error (never raises).
    """
    if not force_refresh:
        cached = _cache.get(symbol, exchange)
        if cached is not None:
            return cached

    try:
        fs = compute_features(symbol=symbol, exchange=exchange)
    except Exception:
        return FeatureSet(symbol=symbol, exchange=exchange, timestamp=time.time())

    _cache.set(fs)
    return fs
