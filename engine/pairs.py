"""
engine/pairs.py
───────────────
Pair trading / relative value analysis for Indian stocks.

Identifies:
  - Cointegrated pairs (stocks that move together)
  - Spread z-score (is the spread stretched?)
  - Mean reversion signals
  - Sector-relative strength

Usage:
    from engine.pairs import find_pairs, analyze_pair, print_pair_analysis

    # Find cointegrated pairs from a watchlist
    pairs = find_pairs(["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK"])

    # Analyze a specific pair
    result = analyze_pair("HDFCBANK", "ICICIBANK")
    result.print_analysis()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class PairAnalysis:
    """Result of analyzing a stock pair for relative value trading."""

    stock_a: str
    stock_b: str
    correlation: float  # -1 to +1
    spread_zscore: float  # current spread z-score
    spread_mean: float  # historical mean spread
    spread_std: float  # spread standard deviation
    signal: str  # "LONG_A_SHORT_B" / "LONG_B_SHORT_A" / "NO_SIGNAL"
    signal_strength: str  # "STRONG" / "MODERATE" / "WEAK"
    half_life: Optional[float] = None  # mean reversion half-life in days
    hedge_ratio: float = 1.0  # how many units of B per unit of A

    # Recent performance
    a_return_30d: float = 0.0  # 30-day return %
    b_return_30d: float = 0.0
    spread_return: float = 0.0  # A return - B return (30d)

    def print_analysis(self) -> None:
        sig_style = {
            "LONG_A_SHORT_B": "green",
            "LONG_B_SHORT_A": "red",
        }.get(self.signal, "yellow")

        lines = [
            f"  [bold]{self.stock_a} vs {self.stock_b}[/bold]",
            f"  Correlation      : {self.correlation:.2f}",
            f"  Spread Z-Score   : {self.spread_zscore:+.2f}",
            f"  Spread Mean      : {self.spread_mean:.2f}",
            f"  Hedge Ratio      : {self.hedge_ratio:.3f}",
            "",
            f"  30d Return {self.stock_a:6s} : {self.a_return_30d:+.1f}%",
            f"  30d Return {self.stock_b:6s} : {self.b_return_30d:+.1f}%",
            f"  Spread Return    : {self.spread_return:+.1f}%",
            "",
            f"  Signal           : [{sig_style}]{self.signal}[/{sig_style}] ({self.signal_strength})",
        ]

        if self.half_life:
            lines.append(f"  Half-life        : {self.half_life:.1f} days")

        if self.signal != "NO_SIGNAL":
            if self.signal == "LONG_A_SHORT_B":
                lines.append(
                    f"\n  Trade: BUY {self.stock_a}, SELL {self.stock_b} (spread to narrow)"
                )
            else:
                lines.append(
                    f"\n  Trade: BUY {self.stock_b}, SELL {self.stock_a} (spread to narrow)"
                )

        console.print(
            Panel(
                "\n".join(lines), title="[bold cyan]Pair Analysis[/bold cyan]", border_style="cyan"
            )
        )


# ── Common Indian Pairs ──────────────────────────────────────

KNOWN_PAIRS = [
    ("HDFCBANK", "ICICIBANK"),  # private banks
    ("HDFCBANK", "KOTAKBANK"),
    ("TCS", "INFY"),  # IT
    ("INFY", "WIPRO"),
    ("SBIN", "BANKBARODA"),  # PSU banks
    ("TATASTEEL", "JSWSTEEL"),  # metals
    ("SUNPHARMA", "DRREDDY"),  # pharma
    ("MARUTI", "TATAMOTORS"),  # auto
    ("RELIANCE", "BHARTIARTL"),  # telecom/conglomerate
    ("ITC", "HINDUNILVR"),  # FMCG
    ("ASIANPAINT", "BERGEPAINT"),  # paints
    ("NTPC", "POWERGRID"),  # power utilities
]


def analyze_pair(
    stock_a: str,
    stock_b: str,
    lookback_days: int = 252,
) -> PairAnalysis:
    """Analyze a pair of stocks for relative value trading signals."""
    stock_a = stock_a.upper()
    stock_b = stock_b.upper()

    returns_a = _get_closes(stock_a, lookback_days)
    returns_b = _get_closes(stock_b, lookback_days)

    if returns_a is None or returns_b is None:
        return PairAnalysis(
            stock_a=stock_a,
            stock_b=stock_b,
            correlation=0,
            spread_zscore=0,
            spread_mean=0,
            spread_std=0,
            signal="NO_SIGNAL",
            signal_strength="WEAK",
        )

    # Align lengths
    min_len = min(len(returns_a), len(returns_b))
    a = returns_a[-min_len:]
    b = returns_b[-min_len:]

    # Correlation
    correlation = float(np.corrcoef(a, b)[0, 1])

    # Hedge ratio (OLS regression: A = beta * B + alpha)
    beta = float(np.cov(a, b)[0, 1] / np.var(b)) if np.var(b) > 0 else 1.0

    # Spread = A - beta * B
    spread = a - beta * b
    spread_mean = float(np.mean(spread))
    spread_std = float(np.std(spread))
    current_spread = float(spread[-1])
    zscore = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0

    # Half-life of mean reversion (using AR(1) model)
    half_life = _compute_half_life(spread)

    # 30-day returns
    if len(a) >= 22:
        a_ret = (a[-1] - a[-22]) / a[-22] * 100
        b_ret = (b[-1] - b[-22]) / b[-22] * 100
    else:
        a_ret = b_ret = 0.0

    # Signal generation
    signal = "NO_SIGNAL"
    strength = "WEAK"

    if abs(zscore) > 2.0 and correlation > 0.5:
        strength = "STRONG"
        signal = "LONG_A_SHORT_B" if zscore < -2.0 else "LONG_B_SHORT_A"
    elif abs(zscore) > 1.5 and correlation > 0.5:
        strength = "MODERATE"
        signal = "LONG_A_SHORT_B" if zscore < -1.5 else "LONG_B_SHORT_A"
    elif abs(zscore) > 1.0 and correlation > 0.6:
        strength = "WEAK"
        signal = "LONG_A_SHORT_B" if zscore < -1.0 else "LONG_B_SHORT_A"

    return PairAnalysis(
        stock_a=stock_a,
        stock_b=stock_b,
        correlation=round(correlation, 3),
        spread_zscore=round(zscore, 2),
        spread_mean=round(spread_mean, 2),
        spread_std=round(spread_std, 2),
        signal=signal,
        signal_strength=strength,
        half_life=round(half_life, 1) if half_life else None,
        hedge_ratio=round(beta, 3),
        a_return_30d=round(a_ret, 1),
        b_return_30d=round(b_ret, 1),
        spread_return=round(a_ret - b_ret, 1),
    )


def find_pairs(
    symbols: Optional[list[str]] = None,
    min_correlation: float = 0.6,
) -> list[PairAnalysis]:
    """
    Scan a list of symbols for tradeable pairs.
    Returns pairs sorted by signal strength.
    """
    if symbols and len(symbols) >= 2:
        # Generate all combinations
        pairs_to_check = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                pairs_to_check.append((symbols[i].upper(), symbols[j].upper()))
    else:
        pairs_to_check = KNOWN_PAIRS

    results = []
    for a, b in pairs_to_check:
        try:
            analysis = analyze_pair(a, b)
            if analysis.correlation >= min_correlation:
                results.append(analysis)
        except Exception:
            continue

    # Sort: signals first, then by z-score magnitude
    signal_order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2}
    results.sort(
        key=lambda x: (
            0 if x.signal != "NO_SIGNAL" else 1,
            signal_order.get(x.signal_strength, 3),
            -abs(x.spread_zscore),
        )
    )

    return results


def print_pairs_scan(symbols: Optional[list[str]] = None) -> None:
    """Display pair trading opportunities."""
    pairs = find_pairs(symbols)
    if not pairs:
        console.print("[dim]No tradeable pairs found.[/dim]")
        return

    table = Table(title="Pair Trading Opportunities", show_lines=False)
    table.add_column("Pair", style="bold", width=22)
    table.add_column("Corr", justify="right", width=6)
    table.add_column("Z-Score", justify="right", width=8)
    table.add_column("Signal", width=22)
    table.add_column("Strength", width=10)
    table.add_column("Spread 30d", justify="right", width=10)

    for p in pairs:
        sig_style = {
            "LONG_A_SHORT_B": "green",
            "LONG_B_SHORT_A": "red",
        }.get(p.signal, "dim")
        str_style = {"STRONG": "bold", "MODERATE": "", "WEAK": "dim"}.get(p.signal_strength, "")

        table.add_row(
            f"{p.stock_a} / {p.stock_b}",
            f"{p.correlation:.2f}",
            f"{p.spread_zscore:+.2f}",
            f"[{sig_style}]{p.signal}[/{sig_style}]",
            f"[{str_style}]{p.signal_strength}[/{str_style}]" if str_style else p.signal_strength,
            f"{p.spread_return:+.1f}%",
        )

    console.print(table)


# ── Helpers ──────────────────────────────────────────────────


def _get_closes(symbol: str, days: int = 252) -> Optional[np.ndarray]:
    """Get closing prices from yfinance."""
    try:
        from market.yfinance_provider import yf_get_ohlcv

        data = yf_get_ohlcv(symbol, period="1y")
        if not data or len(data) < 30:
            return None
        return np.array([d["close"] for d in data if d["close"] and d["close"] > 0])
    except Exception:
        return None


def _compute_half_life(spread: np.ndarray) -> Optional[float]:
    """Compute mean-reversion half-life using AR(1) model."""
    try:
        lag = spread[:-1]
        delta = np.diff(spread)
        if len(lag) < 10:
            return None
        # OLS: delta = alpha + beta * lag + epsilon
        X = np.column_stack([np.ones(len(lag)), lag])
        beta = np.linalg.lstsq(X, delta, rcond=None)[0][1]
        if beta >= 0:
            return None  # not mean-reverting
        half_life = -np.log(2) / beta
        return float(half_life) if 1 < half_life < 200 else None
    except Exception:
        return None
