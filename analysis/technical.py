"""
analysis/technical.py
─────────────────────
Technical indicators computed on OHLCV pandas DataFrames.
Pure numpy/pandas — no external TA library dependency.

All functions accept a DataFrame with columns:
    open, high, low, close, volume  (index = datetime)

Main entry point: analyse(symbol) → TechnicalSnapshot
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from market.history import get_ohlcv


# ── Result dataclass ─────────────────────────────────────────


@dataclass
class Signal:
    name: str
    value: float | str
    verdict: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    detail: str = ""


@dataclass
class TechnicalSnapshot:
    symbol: str
    ltp: float

    # Indicators
    rsi: float = 0.0
    macd: float = 0.0
    macd_sig: float = 0.0
    macd_hist: float = 0.0
    ema20: float = 0.0
    ema50: float = 0.0
    sma200: float = 0.0
    bb_upper: float = 0.0
    bb_lower: float = 0.0
    bb_mid: float = 0.0
    atr: float = 0.0
    volume_ratio: float = 0.0  # today's vol / 20-day avg vol

    # Support / Resistance
    support: float = 0.0
    resistance: float = 0.0
    pivot: float = 0.0

    # Signals list
    signals: list[Signal] = field(default_factory=list)

    # Overall verdict
    verdict: str = "NEUTRAL"  # BULLISH | BEARISH | NEUTRAL
    score: int = 0  # -100 to +100
    summary: str = ""


# ── Core indicators ──────────────────────────────────────────


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_span: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_span)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_k: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, mid, lower)."""
    mid = sma(close, period)
    std = close.rolling(window=period).std()
    upper = mid + std_k * std
    lower = mid - std_k * std
    return upper, mid, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def pivot_points(df: pd.DataFrame) -> dict[str, float]:
    """
    Classic floor pivot points from the last completed candle.
    Returns: pivot, r1, r2, r3, s1, s2, s3
    """
    prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
    h, l, c = prev["high"], prev["low"], prev["close"]
    pivot = (h + l + c) / 3
    return {
        "pivot": round(pivot, 2),
        "r1": round(2 * pivot - l, 2),
        "r2": round(pivot + (h - l), 2),
        "r3": round(h + 2 * (pivot - l), 2),
        "s1": round(2 * pivot - h, 2),
        "s2": round(pivot - (h - l), 2),
        "s3": round(l - 2 * (h - pivot), 2),
    }


# ── Main analyser ────────────────────────────────────────────


def analyse(
    symbol: str,
    exchange: str = "NSE",
    days: int = 365,
) -> TechnicalSnapshot:
    """
    Full technical analysis for a symbol.

    Fetches OHLCV, computes all indicators, generates signals,
    and returns a TechnicalSnapshot with a score and verdict.

    Score:  +10 per bullish signal, -10 per bearish signal.
    Verdict:
        score > 30  → BULLISH
        score < -30 → BEARISH
        else        → NEUTRAL
    """
    # ── Fetch data ────────────────────────────────────────────
    try:
        df = get_ohlcv(symbol=symbol, exchange=exchange, days=days)
    except Exception:
        df = pd.DataFrame()

    if df.empty or len(df) < 30:
        return TechnicalSnapshot(symbol=symbol, ltp=0.0, verdict="INSUFFICIENT DATA")

    close = df["close"]
    ltp = float(close.iloc[-1])

    # ── Compute indicators ────────────────────────────────────
    rsi_series = rsi(close)
    rsi_val = float(rsi_series.iloc[-1])

    macd_line, sig_line, histogram = macd(close)
    macd_val = float(macd_line.iloc[-1])
    sig_val = float(sig_line.iloc[-1])
    hist_val = float(histogram.iloc[-1])

    ema20_val = float(ema(close, 20).iloc[-1])
    ema50_val = float(ema(close, 50).iloc[-1])
    sma200_val = (
        float(sma(close, 200).iloc[-1]) if len(df) >= 200 else float(sma(close, len(df)).iloc[-1])
    )

    bb_upper, bb_mid, bb_lower = bollinger_bands(close)
    bb_u = float(bb_upper.iloc[-1])
    bb_m = float(bb_mid.iloc[-1])
    bb_l = float(bb_lower.iloc[-1])

    atr_val = float(atr(df).iloc[-1])

    vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
    vol_today = float(df["volume"].iloc[-1])
    vol_ratio = round(vol_today / vol_avg, 2) if vol_avg else 1.0

    pivots = pivot_points(df)

    # ── Build signals ─────────────────────────────────────────
    signals: list[Signal] = []
    score = 0

    # RSI
    if rsi_val < 30:
        signals.append(Signal("RSI", round(rsi_val, 1), "BULLISH", "Oversold (<30)"))
        score += 15
    elif rsi_val > 70:
        signals.append(Signal("RSI", round(rsi_val, 1), "BEARISH", "Overbought (>70)"))
        score -= 15
    else:
        signals.append(
            Signal(
                "RSI",
                round(rsi_val, 1),
                "NEUTRAL",
                "Bullish zone (50-70)" if rsi_val > 50 else "Bearish zone (30-50)",
            )
        )
        score += 5 if rsi_val > 50 else -5

    # MACD crossover
    prev_hist = float(histogram.iloc[-2]) if len(histogram) >= 2 else 0
    if hist_val > 0 and prev_hist <= 0:
        signals.append(Signal("MACD", round(macd_val, 2), "BULLISH", "Bullish crossover"))
        score += 15
    elif hist_val < 0 and prev_hist >= 0:
        signals.append(Signal("MACD", round(macd_val, 2), "BEARISH", "Bearish crossover"))
        score -= 15
    elif hist_val > 0:
        signals.append(Signal("MACD", round(macd_val, 2), "BULLISH", "Above signal line"))
        score += 8
    else:
        signals.append(Signal("MACD", round(macd_val, 2), "BEARISH", "Below signal line"))
        score -= 8

    # Price vs MAs
    if ltp > ema20_val:
        signals.append(Signal("EMA20", round(ema20_val, 2), "BULLISH", "Price above EMA20"))
        score += 8
    else:
        signals.append(Signal("EMA20", round(ema20_val, 2), "BEARISH", "Price below EMA20"))
        score -= 8

    if ltp > ema50_val:
        signals.append(Signal("EMA50", round(ema50_val, 2), "BULLISH", "Price above EMA50"))
        score += 8
    else:
        signals.append(Signal("EMA50", round(ema50_val, 2), "BEARISH", "Price below EMA50"))
        score -= 8

    if ltp > sma200_val:
        signals.append(Signal("SMA200", round(sma200_val, 2), "BULLISH", "Price above 200 DMA"))
        score += 10
    else:
        signals.append(Signal("SMA200", round(sma200_val, 2), "BEARISH", "Price below 200 DMA"))
        score -= 10

    # Bollinger Bands
    if ltp < bb_l:
        signals.append(
            Signal(
                "BollingerBands",
                round(ltp, 2),
                "BULLISH",
                "Price below lower band — potential reversal",
            )
        )
        score += 10
    elif ltp > bb_u:
        signals.append(
            Signal(
                "BollingerBands",
                round(ltp, 2),
                "BEARISH",
                "Price above upper band — potential reversal",
            )
        )
        score -= 10
    else:
        bb_pos = (ltp - bb_l) / (bb_u - bb_l) if (bb_u - bb_l) else 0.5
        signals.append(
            Signal(
                "BollingerBands",
                f"{bb_pos:.0%} of band",
                "NEUTRAL",
                f"Upper={bb_u:.2f} Mid={bb_m:.2f} Lower={bb_l:.2f}",
            )
        )

    # Volume confirmation
    if vol_ratio > 1.5:
        dir_signal = "BULLISH" if ltp >= float(df["open"].iloc[-1]) else "BEARISH"
        signals.append(
            Signal(
                "Volume",
                f"{vol_ratio:.1f}x avg",
                dir_signal,
                f"High volume day ({vol_ratio:.1f}× 20-day avg)",
            )
        )
        score += 8 if dir_signal == "BULLISH" else -8
    else:
        signals.append(Signal("Volume", f"{vol_ratio:.1f}x avg", "NEUTRAL", "Normal volume"))

    # ── Verdict ───────────────────────────────────────────────
    score = max(-100, min(100, score))
    verdict = "BULLISH" if score > 30 else "BEARISH" if score < -30 else "NEUTRAL"

    bullish_count = sum(1 for s in signals if s.verdict == "BULLISH")
    bearish_count = sum(1 for s in signals if s.verdict == "BEARISH")
    summary = (
        f"{bullish_count} bullish / {bearish_count} bearish signals | "
        f"Score: {score:+d} | RSI {rsi_val:.1f} | "
        f"{'Above' if ltp > sma200_val else 'Below'} 200 DMA"
    )

    return TechnicalSnapshot(
        symbol=symbol,
        ltp=round(ltp, 2),
        rsi=round(rsi_val, 2),
        macd=round(macd_val, 4),
        macd_sig=round(sig_val, 4),
        macd_hist=round(hist_val, 4),
        ema20=round(ema20_val, 2),
        ema50=round(ema50_val, 2),
        sma200=round(sma200_val, 2),
        bb_upper=round(bb_u, 2),
        bb_lower=round(bb_l, 2),
        bb_mid=round(bb_m, 2),
        atr=round(atr_val, 2),
        volume_ratio=vol_ratio,
        support=pivots["s1"],
        resistance=pivots["r1"],
        pivot=pivots["pivot"],
        signals=signals,
        verdict=verdict,
        score=score,
        summary=summary,
    )
