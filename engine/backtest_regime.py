"""
engine/backtest_regime.py
──────────────────────────
Analyse strategy performance broken down by market regime (bull/bear/sideways).

Usage:
    from engine.backtest_regime import analyse_by_regime, label_regimes, RegimeType
    from engine.backtest import Backtester, RSIStrategy

    bt = Backtester("RELIANCE", period="2y")
    result = bt.run(RSIStrategy())
    regime_analysis = analyse_by_regime(result)
    regime_analysis.print_summary()
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.table import Table

from engine.backtest import BacktestResult

console = Console()


# ── Regime type ───────────────────────────────────────────────


class RegimeType(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"


# ── Data models ───────────────────────────────────────────────


@dataclass
class RegimeStats:
    """Performance statistics for trades that occurred in a single regime."""

    regime: RegimeType
    trade_count: int
    win_count: int
    win_rate: float  # %
    avg_return: float  # % per trade
    total_return: float  # % sum of all trades in this regime
    avg_hold_days: float
    sharpe: float  # annualised Sharpe from trade returns
    best_trade: float  # % highest single trade return
    worst_trade: float  # % lowest single trade return
    regime_pct: float  # % of total backtest period in this regime


@dataclass
class BacktestRegimeResult:
    """Full regime-breakdown result wrapping an existing BacktestResult."""

    symbol: str
    strategy_name: str
    period: str
    regimes: dict[RegimeType, RegimeStats]  # keyed by regime type
    overall_result: BacktestResult  # reference to original
    regime_labels: pd.Series  # date-indexed Series of RegimeType strings

    def print_summary(self) -> None:
        """Display regime breakdown as a Rich table."""
        table = Table(
            title=f"[bold cyan]Regime Analysis: {self.strategy_name} on {self.symbol}[/bold cyan]",
            show_lines=True,
        )
        table.add_column("Regime", style="bold", width=10)
        table.add_column("Period %", justify="right", width=9)
        table.add_column("Trades", justify="right", width=8)
        table.add_column("Win Rate", justify="right", width=9)
        table.add_column("Avg Ret%", justify="right", width=9)
        table.add_column("Total Ret%", justify="right", width=11)
        table.add_column("Sharpe", justify="right", width=8)
        table.add_column("Best%", justify="right", width=8)
        table.add_column("Worst%", justify="right", width=8)
        table.add_column("Avg Days", justify="right", width=9)

        regime_colors = {
            RegimeType.BULL: "green",
            RegimeType.BEAR: "red",
            RegimeType.SIDEWAYS: "yellow",
        }

        for rtype in (RegimeType.BULL, RegimeType.BEAR, RegimeType.SIDEWAYS):
            stats = self.regimes.get(rtype)
            if stats is None:
                continue
            color = regime_colors[rtype]
            wr_color = "green" if stats.win_rate >= 50 else "red"
            tr_color = "green" if stats.total_return >= 0 else "red"

            table.add_row(
                f"[{color}]{rtype.value}[/{color}]",
                f"{stats.regime_pct:.1f}%",
                str(stats.trade_count),
                f"[{wr_color}]{stats.win_rate:.1f}%[/{wr_color}]",
                f"{stats.avg_return:+.2f}%",
                f"[{tr_color}]{stats.total_return:+.2f}%[/{tr_color}]",
                f"{stats.sharpe:.2f}",
                f"[green]{stats.best_trade:+.2f}%[/green]",
                f"[red]{stats.worst_trade:+.2f}%[/red]",
                f"{stats.avg_hold_days:.1f}",
            )

        console.print(table)

    def best_regime(self) -> RegimeType:
        """Regime with the highest win_rate."""
        return max(self.regimes, key=lambda r: self.regimes[r].win_rate)

    def worst_regime(self) -> RegimeType:
        """Regime with the lowest win_rate."""
        return min(self.regimes, key=lambda r: self.regimes[r].win_rate)


# ── Core functions ────────────────────────────────────────────


def label_regimes(
    prices: pd.Series,
    sma_period: int = 200,
    sideways_threshold: float = 0.03,
) -> pd.Series:
    """
    Label each date as BULL / BEAR / SIDEWAYS.

    Rules:
    - BULL:     price > SMA(sma_period) AND price > price[20 days ago] * (1 + sideways_threshold)
    - BEAR:     price < SMA(sma_period) AND price < price[20 days ago] * (1 - sideways_threshold)
    - SIDEWAYS: otherwise

    Returns pd.Series[RegimeType] indexed by date.
    """
    sma = prices.rolling(sma_period, min_periods=sma_period).mean()
    price_20_ago = prices.shift(20)

    bull_mask = (prices > sma) & (prices > price_20_ago * (1 + sideways_threshold))
    bear_mask = (prices < sma) & (prices < price_20_ago * (1 - sideways_threshold))

    labels = pd.Series(RegimeType.SIDEWAYS, index=prices.index, dtype=object)
    labels[bull_mask] = RegimeType.BULL
    labels[bear_mask] = RegimeType.BEAR

    # Where SMA is NaN (not enough history) → SIDEWAYS (already default)
    return labels


def _sharpe_from_returns(returns: list[float], periods_per_year: float = 252) -> float:
    """Annualised Sharpe from a list of % trade returns."""
    if len(returns) < 2:
        return 0.0
    arr = pd.Series(returns, dtype=float)
    std = arr.std(ddof=1)
    if std == 0 or math.isnan(std):
        return 0.0
    mean = arr.mean()
    return float((mean / std) * math.sqrt(periods_per_year))


def _build_regime_stats(
    regime: RegimeType,
    trades: list,
    regime_pct: float,
) -> RegimeStats:
    """Compute RegimeStats from a list of Trade objects for a single regime."""
    if not trades:
        return RegimeStats(
            regime=regime,
            trade_count=0,
            win_count=0,
            win_rate=0.0,
            avg_return=0.0,
            total_return=0.0,
            avg_hold_days=0.0,
            sharpe=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            regime_pct=regime_pct,
        )

    returns = [t.pnl_pct for t in trades]
    winners = [t for t in trades if t.pnl_pct > 0]
    win_count = len(winners)
    win_rate = win_count / len(trades) * 100
    avg_return = sum(returns) / len(returns)
    total_return = sum(returns)
    avg_hold_days = sum(t.hold_days for t in trades) / len(trades)
    sharpe = _sharpe_from_returns(returns)
    best_trade = max(returns)
    worst_trade = min(returns)

    return RegimeStats(
        regime=regime,
        trade_count=len(trades),
        win_count=win_count,
        win_rate=round(win_rate, 1),
        avg_return=round(avg_return, 2),
        total_return=round(total_return, 2),
        avg_hold_days=round(avg_hold_days, 1),
        sharpe=round(sharpe, 2),
        best_trade=round(best_trade, 2),
        worst_trade=round(worst_trade, 2),
        regime_pct=round(regime_pct, 1),
    )


def analyse_by_regime(
    result: BacktestResult,
    prices: Optional[pd.Series] = None,
    sma_period: int = 200,
) -> BacktestRegimeResult:
    """
    Split trades from result by the regime active at each trade entry_date.

    If prices is None, fetches from yfinance using result.symbol.
    """
    if prices is None:
        ticker = yf.Ticker(f"{result.symbol}.NS")
        hist = ticker.history(period="5y")
        prices = hist["Close"]
        if prices.index.tz is not None:
            prices.index = prices.index.tz_localize(None)
        prices.index = pd.to_datetime(prices.index)

    # Normalise price index to tz-naive datetime
    if prices.index.tz is not None:
        prices = prices.copy()
        prices.index = prices.index.tz_localize(None)
    prices.index = pd.to_datetime(prices.index)

    regime_labels = label_regimes(prices, sma_period=sma_period)

    # Regime coverage % across the full price series
    total_bars = len(regime_labels)
    regime_counts = regime_labels.value_counts()

    def _pct(r: RegimeType) -> float:
        return regime_counts.get(r, 0) / total_bars * 100 if total_bars else 0.0

    # Bucket each trade by its entry date regime
    bucketed: dict[RegimeType, list] = {
        RegimeType.BULL: [],
        RegimeType.BEAR: [],
        RegimeType.SIDEWAYS: [],
    }

    for trade in result.trades:
        entry_ts = pd.Timestamp(trade.entry_date)
        # Find the closest date at or before entry_ts in regime_labels
        valid_dates = regime_labels.index[regime_labels.index <= entry_ts]
        if len(valid_dates) == 0:
            # Before the earliest labelled date — default to SIDEWAYS
            regime = RegimeType.SIDEWAYS
        else:
            closest = valid_dates[-1]
            regime = regime_labels.loc[closest]
        bucketed[regime].append(trade)

    regimes = {
        rtype: _build_regime_stats(rtype, bucketed[rtype], _pct(rtype)) for rtype in RegimeType
    }

    return BacktestRegimeResult(
        symbol=result.symbol,
        strategy_name=result.strategy_name,
        period=result.period,
        regimes=regimes,
        overall_result=result,
        regime_labels=regime_labels,
    )
