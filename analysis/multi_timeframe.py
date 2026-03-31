"""
analysis/multi_timeframe.py
───────────────────────────
Multi-timeframe analysis — check daily + hourly confluence.

A signal is stronger when both timeframes agree:
  - Daily RSI oversold + Hourly MACD bullish crossover = strong buy
  - Daily bearish + Hourly bearish = confirmed downtrend
  - Daily bullish + Hourly bearish = wait for hourly to align

Usage:
    from analysis.multi_timeframe import multi_timeframe_analysis

    result = multi_timeframe_analysis("RELIANCE")
    result.print_analysis()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class TimeframeSignal:
    """Signal from a single timeframe."""
    timeframe:  str          # "Daily" / "Hourly" / "Weekly"
    verdict:    str          # BULLISH / BEARISH / NEUTRAL
    score:      float
    rsi:        float = 0.0
    macd_signal: str = ""    # "BULLISH_CROSS" / "BEARISH_CROSS" / "NEUTRAL"
    ema_trend:  str = ""     # "ABOVE" (EMA20 > EMA50) / "BELOW"
    key_points: list[str] = field(default_factory=list)


@dataclass
class MultiTimeframeResult:
    """Result of multi-timeframe analysis."""
    symbol:         str
    signals:        list[TimeframeSignal]
    confluence:     str          # "STRONG_BUY" / "BUY" / "NEUTRAL" / "SELL" / "STRONG_SELL"
    confluence_score: float
    alignment:      str          # "ALIGNED" / "CONFLICTING" / "MIXED"
    recommendation: str

    def print_analysis(self) -> None:
        table = Table(title=f"Multi-Timeframe: {self.symbol}", show_lines=True)
        table.add_column("Timeframe", style="bold", width=10)
        table.add_column("Verdict", width=10)
        table.add_column("Score", justify="right", width=8)
        table.add_column("RSI", justify="right", width=6)
        table.add_column("MACD", width=14)
        table.add_column("EMA Trend", width=10)

        for s in self.signals:
            v_style = {"BULLISH": "green", "BEARISH": "red"}.get(s.verdict, "yellow")
            table.add_row(
                s.timeframe,
                f"[{v_style}]{s.verdict}[/{v_style}]",
                f"{s.score:+.0f}",
                f"{s.rsi:.0f}",
                s.macd_signal,
                s.ema_trend,
            )

        console.print(table)

        conf_style = "green" if "BUY" in self.confluence else "red" if "SELL" in self.confluence else "yellow"
        console.print(
            f"\n  Confluence : [{conf_style}]{self.confluence}[/{conf_style}] "
            f"(score: {self.confluence_score:+.1f})"
        )
        console.print(f"  Alignment  : {self.alignment}")
        console.print(f"  Action     : {self.recommendation}\n")


def multi_timeframe_analysis(
    symbol: str,
    exchange: str = "NSE",
) -> MultiTimeframeResult:
    """
    Run technical analysis on multiple timeframes and check confluence.
    """
    from market.history import get_ohlcv
    from analysis.technical import analyse, rsi, ema

    signals = []

    # ── Weekly ───────────────────────────────────────────────
    try:
        df_w = get_ohlcv(symbol, exchange, interval="day", days=365)
        if not df_w.empty and len(df_w) >= 50:
            # Resample to weekly
            df_weekly = df_w.resample("W").agg({
                "open": "first", "high": "max", "low": "min",
                "close": "last", "volume": "sum",
            }).dropna()
            if len(df_weekly) >= 20:
                sig = _analyze_timeframe(df_weekly, "Weekly")
                signals.append(sig)
    except Exception:
        pass

    # ── Daily ────────────────────────────────────────────────
    try:
        snap = analyse(symbol, exchange)
        daily = TimeframeSignal(
            timeframe="Daily",
            verdict=snap.verdict,
            score=snap.score,
            rsi=snap.rsi,
            macd_signal="BULLISH_CROSS" if snap.macd_hist > 0 else "BEARISH_CROSS",
            ema_trend="ABOVE" if snap.ema20 > snap.ema50 else "BELOW",
            key_points=[s.description for s in snap.signals[:3]] if hasattr(snap, 'signals') else [],
        )
        signals.append(daily)
    except Exception:
        pass

    # ── Hourly (4h) ──────────────────────────────────────────
    try:
        df_h = get_ohlcv(symbol, exchange, interval="60minute", days=30)
        if not df_h.empty and len(df_h) >= 20:
            sig = _analyze_timeframe(df_h, "Hourly")
            signals.append(sig)
    except Exception:
        pass

    # ── Confluence ───────────────────────────────────────────
    if not signals:
        return MultiTimeframeResult(
            symbol=symbol, signals=[], confluence="NEUTRAL",
            confluence_score=0, alignment="NO_DATA",
            recommendation="Insufficient data for multi-timeframe analysis.",
        )

    avg_score = sum(s.score for s in signals) / len(signals)
    verdicts = [s.verdict for s in signals]
    all_bull = all(v == "BULLISH" for v in verdicts)
    all_bear = all(v == "BEARISH" for v in verdicts)
    mixed = not all_bull and not all_bear and len(set(verdicts)) > 1

    if all_bull and avg_score > 30:
        confluence = "STRONG_BUY"
        alignment = "ALIGNED"
        rec = "All timeframes bullish — high-confidence entry. Use daily levels for entry, hourly for timing."
    elif all_bull:
        confluence = "BUY"
        alignment = "ALIGNED"
        rec = "Timeframes aligned bullish. Enter on hourly pullback to support."
    elif all_bear and avg_score < -30:
        confluence = "STRONG_SELL"
        alignment = "ALIGNED"
        rec = "All timeframes bearish — avoid longs. Consider puts or short if available."
    elif all_bear:
        confluence = "SELL"
        alignment = "ALIGNED"
        rec = "Timeframes aligned bearish. Exit longs or tighten stop-losses."
    elif mixed:
        confluence = "NEUTRAL"
        alignment = "CONFLICTING"
        rec = "Timeframes conflicting — wait for alignment before entering. Daily is the primary trend."
    else:
        confluence = "NEUTRAL"
        alignment = "MIXED"
        rec = "No clear signal across timeframes. Wait for clarity."

    return MultiTimeframeResult(
        symbol=symbol,
        signals=signals,
        confluence=confluence,
        confluence_score=round(avg_score, 1),
        alignment=alignment,
        recommendation=rec,
    )


def _analyze_timeframe(df: pd.DataFrame, label: str) -> TimeframeSignal:
    """Run basic technical indicators on a dataframe."""
    from analysis.technical import rsi as calc_rsi, ema as calc_ema

    close = df["close"]
    rsi_val = float(calc_rsi(close).iloc[-1]) if len(close) >= 14 else 50.0
    ema20 = float(calc_ema(close, 20).iloc[-1]) if len(close) >= 20 else 0
    ema50 = float(calc_ema(close, 50).iloc[-1]) if len(close) >= 50 else ema20

    # MACD
    ema12 = calc_ema(close, 12)
    ema26 = calc_ema(close, 26)
    macd_line = ema12 - ema26
    signal_line = calc_ema(macd_line, 9)
    macd_hist = float((macd_line - signal_line).iloc[-1]) if len(close) >= 26 else 0

    # Score
    score = 0.0
    if rsi_val < 30:
        score += 20
    elif rsi_val > 70:
        score -= 20
    if ema20 > ema50:
        score += 15
    else:
        score -= 15
    if macd_hist > 0:
        score += 15
    else:
        score -= 15

    verdict = "BULLISH" if score > 10 else "BEARISH" if score < -10 else "NEUTRAL"

    return TimeframeSignal(
        timeframe=label,
        verdict=verdict,
        score=score,
        rsi=rsi_val,
        macd_signal="BULLISH_CROSS" if macd_hist > 0 else "BEARISH_CROSS",
        ema_trend="ABOVE" if ema20 > ema50 else "BELOW",
    )
