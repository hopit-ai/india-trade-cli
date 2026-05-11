"""
engine/signal_ensemble.py
─────────────────────────
Weighted multi-strategy signal ensemble (#167).

Five strategies vote on direction; final signal = weighted majority.

Strategy weights:
  trend       25% — EMA-20/50 crossover + ADX > 20 confirmation
  mean_rev    20% — RSI extremes (30/70) + Bollinger Band touch
  momentum    25% — 1M / 3M / 6M return momentum (weighted blend)
  volatility  15% — ATR regime: low vol leans bullish, high vol caution
  statistical 15% — Hurst exponent: trending vs mean-reverting regime

Usage:
    from engine.signal_ensemble import ensemble_signal

    df = get_ohlcv("INFY", days=200)          # pandas DataFrame, lowercase columns
    sig = ensemble_signal(df)
    print(sig.verdict, sig.confidence)        # "BULLISH", 0.72
    print(sig.breakdown)                      # per-strategy votes
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


# ── Strategy weights ─────────────────────────────────────────────


STRATEGY_WEIGHTS: dict[str, float] = {
    "trend": 0.25,
    "mean_rev": 0.20,
    "momentum": 0.25,
    "volatility": 0.15,
    "statistical": 0.15,
}

_SIGNAL_LABELS = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}


# ── Result dataclasses ───────────────────────────────────────────


@dataclass
class StrategyVote:
    """A single strategy's vote in the ensemble."""

    signal: int  # +1 bullish, -1 bearish, 0 neutral
    weight: float
    label: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    detail: str = ""  # human-readable reason


@dataclass
class EnsembleSignal:
    """Aggregated ensemble verdict."""

    signal: int  # +1 | 0 | -1 consensus direction
    verdict: str  # "BULLISH" | "NEUTRAL" | "BEARISH"
    confidence: float  # 0.0–1.0 weighted majority strength
    bull_score: float  # sum of bullish weights
    bear_score: float  # sum of bearish weights
    breakdown: dict[str, StrategyVote] = field(default_factory=dict)
    hurst: Optional[float] = None  # Hurst exponent value (for reference)
    adx: Optional[float] = None  # latest ADX value (for reference)


# ── Technical helpers ────────────────────────────────────────────


def _adx(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index + DI+ / DI- lines.

    Returns: (adx_series, di_plus_series, di_minus_series)
    All normalised to 0-100.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # True range
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Directional movement
    up_move = high.diff()
    down_move = -low.diff()

    dm_plus = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    dm_minus = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # Wilder smoothing (EWM approximation)
    atr14 = tr.ewm(span=period, min_periods=period, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(span=period, min_periods=period, adjust=False).mean() / atr14
    di_minus = 100 * dm_minus.ewm(span=period, min_periods=period, adjust=False).mean() / atr14

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx_series = dx.ewm(span=period, min_periods=period, adjust=False).mean()

    return adx_series, di_plus, di_minus


def _hurst_exponent(close: pd.Series, min_window: int = 8) -> Optional[float]:
    """
    Estimate Hurst exponent via R/S (Rescaled Range) analysis.

    H > 0.55 → trending / persistent  (momentum strategies effective)
    H < 0.45 → mean-reverting         (reversion strategies effective)
    H ≈ 0.50 → random walk / no structure

    Returns None if insufficient data (< 50 bars).
    """
    prices = close.values.astype(float)
    if len(prices) < 50:
        return None

    log_ret = np.diff(np.log(np.where(prices > 0, prices, np.nan)))
    log_ret = log_ret[~np.isnan(log_ret)]
    n = len(log_ret)
    if n < 20:
        return None

    # Build a range of window sizes
    max_window = n // 4
    if max_window < min_window:
        return None

    # Logarithmically spaced windows, at least 4 distinct sizes
    windows: list[int] = []
    w = min_window
    while w <= max_window:
        windows.append(w)
        w = max(w + 1, int(w * 1.6))
    if len(windows) < 3:
        return None

    rs_values = []
    for w in windows:
        rs_w = []
        # Non-overlapping chunks of width w
        for start in range(0, n - w + 1, w):
            chunk = log_ret[start : start + w]
            mean_c = chunk.mean()
            dev = np.cumsum(chunk - mean_c)
            r = dev.max() - dev.min()
            s = chunk.std(ddof=1)
            if s > 0:
                rs_w.append(r / s)
        if rs_w:
            rs_values.append(float(np.mean(rs_w)))

    if len(rs_values) < 3:
        return None

    windows_arr = np.array(windows[: len(rs_values)], dtype=float)
    rs_arr = np.array(rs_values)
    valid = rs_arr > 0
    if valid.sum() < 3:
        return None

    try:
        poly = np.polyfit(np.log(windows_arr[valid]), np.log(rs_arr[valid]), 1)
        h = float(poly[0])
        return round(max(0.0, min(1.0, h)), 3)
    except (np.linalg.LinAlgError, ValueError):
        return None


# ── Individual strategy signals ──────────────────────────────────


def _trend_signal(df: pd.DataFrame) -> StrategyVote:
    """
    EMA-20/50 crossover with ADX > 20 confirmation.

    Bullish:  EMA20 > EMA50 and ADX > 20
    Bearish:  EMA20 < EMA50 and ADX > 20
    Neutral:  ADX ≤ 20 (choppy/no trend)
    """
    close = df["close"]
    if len(close) < 50:
        return StrategyVote(0, STRATEGY_WEIGHTS["trend"], "NEUTRAL", "Insufficient data")

    ema20 = close.ewm(span=20, min_periods=20, adjust=False).mean()
    ema50 = close.ewm(span=50, min_periods=50, adjust=False).mean()

    adx_series, _, _ = _adx(df)
    adx_val = float(adx_series.iloc[-1]) if not math.isnan(adx_series.iloc[-1]) else 0.0

    ema20_val = float(ema20.iloc[-1])
    ema50_val = float(ema50.iloc[-1])

    if adx_val <= 20:
        return StrategyVote(
            0,
            STRATEGY_WEIGHTS["trend"],
            "NEUTRAL",
            f"ADX={adx_val:.1f} ≤ 20 — no clear trend",
        )

    if ema20_val > ema50_val:
        detail = f"EMA20={ema20_val:.1f} > EMA50={ema50_val:.1f}, ADX={adx_val:.1f}"
        return StrategyVote(1, STRATEGY_WEIGHTS["trend"], "BULLISH", detail)

    detail = f"EMA20={ema20_val:.1f} < EMA50={ema50_val:.1f}, ADX={adx_val:.1f}"
    return StrategyVote(-1, STRATEGY_WEIGHTS["trend"], "BEARISH", detail)


def _mean_rev_signal(df: pd.DataFrame) -> StrategyVote:
    """
    RSI extremes + Bollinger Band touch for mean reversion.

    Bullish:  RSI < 30 AND price ≤ BB lower band
    Bearish:  RSI > 70 AND price ≥ BB upper band
    Neutral:  otherwise
    """
    close = df["close"]
    if len(close) < 20:
        return StrategyVote(0, STRATEGY_WEIGHTS["mean_rev"], "NEUTRAL", "Insufficient data")

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi_val = float(rsi_series.iloc[-1])

    # Bollinger Bands (20, 2σ)
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std(ddof=1)
    bb_upper = (sma20 + 2 * std20).iloc[-1]
    bb_lower = (sma20 - 2 * std20).iloc[-1]
    ltp = float(close.iloc[-1])

    if rsi_val < 30 and ltp <= bb_lower:
        detail = f"RSI={rsi_val:.1f} (<30) + price≤BB_lower={bb_lower:.1f} — oversold"
        return StrategyVote(1, STRATEGY_WEIGHTS["mean_rev"], "BULLISH", detail)

    if rsi_val > 70 and ltp >= bb_upper:
        detail = f"RSI={rsi_val:.1f} (>70) + price≥BB_upper={bb_upper:.1f} — overbought"
        return StrategyVote(-1, STRATEGY_WEIGHTS["mean_rev"], "BEARISH", detail)

    detail = f"RSI={rsi_val:.1f}, ltp={ltp:.1f} (BB: {bb_lower:.1f}–{bb_upper:.1f})"
    return StrategyVote(0, STRATEGY_WEIGHTS["mean_rev"], "NEUTRAL", detail)


def _momentum_signal(df: pd.DataFrame) -> StrategyVote:
    """
    Multi-timeframe return momentum: 1M (50%) + 3M (30%) + 6M (20%).

    Bullish:  blended return > +5%
    Bearish:  blended return < -5%
    Neutral:  otherwise
    """
    close = df["close"]
    n = len(close)

    r1m = (close.iloc[-1] / close.iloc[-22] - 1) if n >= 22 else None
    r3m = (close.iloc[-1] / close.iloc[-66] - 1) if n >= 66 else None
    r6m = (close.iloc[-1] / close.iloc[-126] - 1) if n >= 126 else None

    # Weight available timeframes
    total_w = 0.0
    blended = 0.0
    components = []
    if r1m is not None:
        blended += 0.5 * r1m
        total_w += 0.5
        components.append(f"1M={r1m * 100:+.1f}%")
    if r3m is not None:
        blended += 0.3 * r3m
        total_w += 0.3
        components.append(f"3M={r3m * 100:+.1f}%")
    if r6m is not None:
        blended += 0.2 * r6m
        total_w += 0.2
        components.append(f"6M={r6m * 100:+.1f}%")

    if total_w < 0.3:
        return StrategyVote(
            0, STRATEGY_WEIGHTS["momentum"], "NEUTRAL", "Insufficient history for momentum"
        )

    # Normalise
    score = blended / total_w if total_w > 0 else 0.0
    detail = ", ".join(components) + f" → blended={score * 100:+.1f}%"

    if score > 0.05:
        return StrategyVote(1, STRATEGY_WEIGHTS["momentum"], "BULLISH", detail)
    if score < -0.05:
        return StrategyVote(-1, STRATEGY_WEIGHTS["momentum"], "BEARISH", detail)

    return StrategyVote(0, STRATEGY_WEIGHTS["momentum"], "NEUTRAL", detail)


def _volatility_signal(df: pd.DataFrame) -> StrategyVote:
    """
    ATR regime signal.

    Low volatility (ATR% < 70% of median):   lean BULLISH (calm before breakout)
    High volatility (ATR% > 150% of median): BEARISH / caution
    Normal range:                             NEUTRAL
    """
    if len(df) < 30:
        return StrategyVote(0, STRATEGY_WEIGHTS["volatility"], "NEUTRAL", "Insufficient data")

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr14 = tr.rolling(14).mean()
    atr_pct = (atr14 / close * 100).dropna()  # as % of price

    current = float(atr_pct.iloc[-1])
    median = float(atr_pct.median())

    if median == 0:
        return StrategyVote(0, STRATEGY_WEIGHTS["volatility"], "NEUTRAL", "ATR median=0")

    ratio = current / median
    detail = f"ATR%={current:.2f}%, median={median:.2f}%, ratio={ratio:.2f}x"

    if ratio < 0.70:
        return StrategyVote(
            1, STRATEGY_WEIGHTS["volatility"], "BULLISH", f"{detail} — low vol regime"
        )
    if ratio > 1.50:
        return StrategyVote(
            -1, STRATEGY_WEIGHTS["volatility"], "BEARISH", f"{detail} — elevated vol"
        )

    return StrategyVote(0, STRATEGY_WEIGHTS["volatility"], "NEUTRAL", detail)


def _statistical_signal(df: pd.DataFrame) -> tuple[StrategyVote, Optional[float]]:
    """
    Hurst exponent regime signal.

    H > 0.55 (trending):      follow the recent EMA direction
    H < 0.45 (mean-reverting): expect price to revert to BB midline
    H ≈ 0.50 (random walk):   NEUTRAL

    Returns (StrategyVote, hurst_value).
    """
    close = df["close"]
    h = _hurst_exponent(close)

    if h is None:
        vote = StrategyVote(
            0, STRATEGY_WEIGHTS["statistical"], "NEUTRAL", "Insufficient data for Hurst"
        )
        return vote, None

    if h > 0.55:
        # Trending regime — follow the trend (use 20-day EMA direction)
        ema20 = close.ewm(span=20, adjust=False).mean()
        rising = ema20.iloc[-1] > ema20.iloc[-5] if len(ema20) >= 5 else False
        sig = 1 if rising else -1
        direction = "rising" if rising else "falling"
        detail = f"H={h:.3f} (>0.55 trending), EMA20 {direction}"
        return StrategyVote(sig, STRATEGY_WEIGHTS["statistical"], _SIGNAL_LABELS[sig], detail), h

    if h < 0.45:
        # Mean-reverting — check if price is above or below midline
        bb_mid = close.rolling(20).mean()
        ltp = float(close.iloc[-1])
        mid = float(bb_mid.iloc[-1]) if not math.isnan(float(bb_mid.iloc[-1])) else ltp
        sig = 1 if ltp < mid else -1
        side = "below" if ltp < mid else "above"
        detail = f"H={h:.3f} (<0.45 mean-reverting), price {side} midline={mid:.1f}"
        return StrategyVote(sig, STRATEGY_WEIGHTS["statistical"], _SIGNAL_LABELS[sig], detail), h

    detail = f"H={h:.3f} ≈ 0.50 (random walk)"
    return StrategyVote(0, STRATEGY_WEIGHTS["statistical"], "NEUTRAL", detail), h


# ── Public API ───────────────────────────────────────────────────


def ensemble_signal(df: pd.DataFrame) -> EnsembleSignal:
    """
    Compute the weighted multi-strategy ensemble signal.

    Args:
        df: OHLCV DataFrame with columns [open, high, low, close, volume]
            and a datetime index. Needs at least 50 rows; 200 is ideal.

    Returns:
        EnsembleSignal with verdict, confidence, and per-strategy breakdown.
    """
    if df is None or len(df) < 10:
        return EnsembleSignal(
            signal=0,
            verdict="NEUTRAL",
            confidence=0.0,
            bull_score=0.0,
            bear_score=0.0,
            breakdown={},
        )

    # Ensure lowercase columns
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # Compute each strategy vote
    trend_vote = _trend_signal(df)
    mean_rev_vote = _mean_rev_signal(df)
    momentum_vote = _momentum_signal(df)
    vol_vote = _volatility_signal(df)
    stat_vote, hurst_val = _statistical_signal(df)

    adx_val: Optional[float] = None
    try:
        adx_series, _, _ = _adx(df)
        adx_val = round(float(adx_series.iloc[-1]), 1)
    except Exception:
        pass

    breakdown = {
        "trend": trend_vote,
        "mean_rev": mean_rev_vote,
        "momentum": momentum_vote,
        "volatility": vol_vote,
        "statistical": stat_vote,
    }

    # Tally weighted scores
    bull_score = 0.0
    bear_score = 0.0
    for name, vote in breakdown.items():
        if vote.signal == 1:
            bull_score += vote.weight
        elif vote.signal == -1:
            bear_score += vote.weight

    # Final signal
    if bull_score > bear_score:
        signal = 1
        verdict = "BULLISH"
        confidence = bull_score  # weighted fraction
    elif bear_score > bull_score:
        signal = -1
        verdict = "BEARISH"
        confidence = bear_score
    else:
        signal = 0
        verdict = "NEUTRAL"
        confidence = 0.5  # tie

    return EnsembleSignal(
        signal=signal,
        verdict=verdict,
        confidence=round(confidence, 3),
        bull_score=round(bull_score, 3),
        bear_score=round(bear_score, 3),
        breakdown=breakdown,
        hurst=hurst_val,
        adx=adx_val,
    )


def format_ensemble(sig: EnsembleSignal, symbol: str = "") -> str:
    """
    Pretty-print an EnsembleSignal for CLI / report output.

    Returns a compact multi-line string suitable for terminal display.
    """
    icon = {"BULLISH": "▲", "BEARISH": "▼", "NEUTRAL": "◆"}
    verdict_icon = icon.get(sig.verdict, "◆")

    header = f"Signal Ensemble{f' — {symbol}' if symbol else ''}"
    bar_bull = "█" * int(sig.bull_score * 20)
    bar_bear = "█" * int(sig.bear_score * 20)

    lines = [
        f"{'─' * 50}",
        f" {header}",
        f"{'─' * 50}",
        f" Verdict:    {verdict_icon} {sig.verdict}  (confidence {sig.confidence:.0%})",
        f" Bull score: {sig.bull_score:.2f}  {bar_bull}",
        f" Bear score: {sig.bear_score:.2f}  {bar_bear}",
    ]
    if sig.hurst is not None:
        regime = (
            "trending" if sig.hurst > 0.55 else "mean-reverting" if sig.hurst < 0.45 else "random"
        )
        lines.append(f" Hurst:      {sig.hurst:.3f} ({regime})")
    if sig.adx is not None:
        lines.append(f" ADX:        {sig.adx:.1f}")

    lines.append("")
    lines.append(" Strategy breakdown:")
    for name, vote in sig.breakdown.items():
        prefix = {"BULLISH": "▲", "BEARISH": "▼", "NEUTRAL": "◆"}[vote.label]
        lines.append(
            f"   {name:<12} {prefix} {vote.label:<8} (w={vote.weight:.0%}) {vote.detail[:55]}"
        )

    lines.append(f"{'─' * 50}")
    return "\n".join(lines)
