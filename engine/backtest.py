"""
engine/backtest.py
──────────────────
Strategy backtester — test trading strategies on historical data.

Supports:
  - Simple strategies: moving average crossover, RSI, MACD
  - Custom signal functions
  - Multi-timeframe analysis
  - Performance metrics: CAGR, Sharpe, max drawdown, win rate

Usage:
    from engine.backtest import Backtester, RSIStrategy, MACrossStrategy

    bt = Backtester("RELIANCE", period="2y")
    result = bt.run(RSIStrategy(buy_level=30, sell_level=70))
    result.print_summary()

    # Or via REPL:
    backtest RELIANCE rsi           # RSI overbought/oversold
    backtest RELIANCE ma 20 50      # 20/50 EMA crossover
    backtest RELIANCE macd          # MACD signal crossover
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ── Data Models ──────────────────────────────────────────────

@dataclass
class Trade:
    """A single completed trade (entry + exit)."""
    entry_date:  str
    exit_date:   str
    direction:   str        # "LONG" or "SHORT"
    entry_price: float
    exit_price:  float
    quantity:    int
    pnl:         float
    pnl_pct:     float
    hold_days:   int
    signal:      str = ""   # what triggered this trade


@dataclass
class BacktestResult:
    """Complete backtest output."""
    symbol:         str
    strategy_name:  str
    period:         str
    start_date:     str
    end_date:       str

    # Performance
    total_return:   float       # %
    cagr:           float       # %
    sharpe_ratio:   float
    max_drawdown:   float       # %
    max_drawdown_date: str = ""

    # Trade stats
    total_trades:   int = 0
    winning_trades: int = 0
    losing_trades:  int = 0
    win_rate:       float = 0.0
    avg_win:        float = 0.0   # %
    avg_loss:       float = 0.0   # %
    profit_factor:  float = 0.0
    avg_hold_days:  float = 0.0

    # Comparison
    buy_hold_return: float = 0.0  # %

    trades:         list[Trade] = field(default_factory=list)
    equity_curve:   list[float] = field(default_factory=list)

    def print_summary(self) -> None:
        """Display backtest results as a Rich panel."""
        ret_style = "green" if self.total_return >= 0 else "red"
        bh_style = "green" if self.buy_hold_return >= 0 else "red"
        alpha = self.total_return - self.buy_hold_return
        alpha_style = "green" if alpha >= 0 else "red"

        lines = [
            f"  Strategy       : [bold]{self.strategy_name}[/bold]",
            f"  Symbol         : {self.symbol}",
            f"  Period         : {self.start_date} → {self.end_date}",
            "",
            f"  [bold]Returns[/bold]",
            f"  Total Return   : [{ret_style}]{self.total_return:+.2f}%[/{ret_style}]",
            f"  CAGR           : [{ret_style}]{self.cagr:+.2f}%[/{ret_style}]",
            f"  Buy & Hold     : [{bh_style}]{self.buy_hold_return:+.2f}%[/{bh_style}]",
            f"  Alpha          : [{alpha_style}]{alpha:+.2f}%[/{alpha_style}]",
            "",
            f"  [bold]Risk[/bold]",
            f"  Sharpe Ratio   : {self.sharpe_ratio:.2f}",
            f"  Max Drawdown   : [red]{self.max_drawdown:.2f}%[/red]",
            "",
            f"  [bold]Trades[/bold]",
            f"  Total          : {self.total_trades}",
            f"  Win Rate       : {self.win_rate:.1f}%",
            f"  Avg Win        : [green]{self.avg_win:+.2f}%[/green]",
            f"  Avg Loss       : [red]{self.avg_loss:+.2f}%[/red]",
            f"  Profit Factor  : {self.profit_factor:.2f}",
            f"  Avg Hold       : {self.avg_hold_days:.1f} days",
        ]

        console.print(Panel(
            "\n".join(lines),
            title=f"[bold cyan]Backtest: {self.strategy_name} on {self.symbol}[/bold cyan]",
            border_style="cyan",
        ))

    def print_trades(self, n: int = 20) -> None:
        """Show individual trades."""
        trades = self.trades[-n:]
        if not trades:
            console.print("[dim]No trades executed.[/dim]")
            return

        table = Table(title=f"Trades ({len(self.trades)} total, last {n})")
        table.add_column("Entry", style="dim", width=12)
        table.add_column("Exit", style="dim", width=12)
        table.add_column("Dir", width=6)
        table.add_column("Entry ₹", justify="right", width=10)
        table.add_column("Exit ₹", justify="right", width=10)
        table.add_column("P&L %", justify="right", width=8)
        table.add_column("Days", justify="right", width=6)

        for t in trades:
            pnl_style = "green" if t.pnl >= 0 else "red"
            table.add_row(
                t.entry_date[:10], t.exit_date[:10], t.direction,
                f"{t.entry_price:,.1f}", f"{t.exit_price:,.1f}",
                f"[{pnl_style}]{t.pnl_pct:+.2f}%[/{pnl_style}]",
                str(t.hold_days),
            )
        console.print(table)


# ── Strategy Interface ───────────────────────────────────────

class Strategy(ABC):
    """Base class for backtesting strategies."""

    name: str = "Base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from OHLCV data.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                (indexed by date)

        Returns:
            Series of signals: 1 = BUY, -1 = SELL, 0 = HOLD
        """


class RSIStrategy(Strategy):
    """Buy when RSI crosses below oversold, sell when crosses above overbought."""

    def __init__(self, period: int = 14, buy_level: int = 30, sell_level: int = 70):
        self.period = period
        self.buy_level = buy_level
        self.sell_level = sell_level
        self.name = f"RSI({period}, {buy_level}/{sell_level})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        from analysis.technical import rsi
        rsi_values = rsi(df["close"], self.period)
        signals = pd.Series(0, index=df.index)
        signals[rsi_values < self.buy_level] = 1
        signals[rsi_values > self.sell_level] = -1
        return signals


class MACrossStrategy(Strategy):
    """Buy when fast EMA crosses above slow EMA, sell on cross below."""

    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow
        self.name = f"EMA Cross({fast}/{slow})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        from analysis.technical import ema
        fast_ema = ema(df["close"], self.fast)
        slow_ema = ema(df["close"], self.slow)
        signals = pd.Series(0, index=df.index)

        # Cross above = buy, cross below = sell
        prev_fast = fast_ema.shift(1)
        prev_slow = slow_ema.shift(1)
        signals[(prev_fast <= prev_slow) & (fast_ema > slow_ema)] = 1
        signals[(prev_fast >= prev_slow) & (fast_ema < slow_ema)] = -1
        return signals


class MACDStrategy(Strategy):
    """Buy on MACD histogram turning positive, sell on turning negative."""

    name = "MACD Signal"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        from analysis.technical import ema
        ema12 = ema(df["close"], 12)
        ema26 = ema(df["close"], 26)
        macd_line = ema12 - ema26
        signal_line = ema(macd_line, 9)
        histogram = macd_line - signal_line

        signals = pd.Series(0, index=df.index)
        prev_hist = histogram.shift(1)
        signals[(prev_hist <= 0) & (histogram > 0)] = 1
        signals[(prev_hist >= 0) & (histogram < 0)] = -1
        return signals


class BollingerStrategy(Strategy):
    """Buy at lower band, sell at upper band."""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
        self.name = f"Bollinger({period}, {std_dev}σ)"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        from analysis.technical import sma
        mid = sma(df["close"], self.period)
        std = df["close"].rolling(self.period).std()
        upper = mid + self.std_dev * std
        lower = mid - self.std_dev * std

        signals = pd.Series(0, index=df.index)
        signals[df["close"] < lower] = 1
        signals[df["close"] > upper] = -1
        return signals


# ── Strategy Registry ────────────────────────────────────────

STRATEGIES = {
    "rsi":       lambda args: RSIStrategy(
        buy_level=int(args[0]) if args else 30,
        sell_level=int(args[1]) if len(args) > 1 else 70,
    ),
    "ma":        lambda args: MACrossStrategy(
        fast=int(args[0]) if args else 20,
        slow=int(args[1]) if len(args) > 1 else 50,
    ),
    "ema":       lambda args: MACrossStrategy(
        fast=int(args[0]) if args else 20,
        slow=int(args[1]) if len(args) > 1 else 50,
    ),
    "macd":      lambda args: MACDStrategy(),
    "bollinger": lambda args: BollingerStrategy(),
    "bb":        lambda args: BollingerStrategy(),
}


# ── Backtester Engine ────────────────────────────────────────

class Backtester:
    """
    Run a strategy against historical OHLCV data.

    Fetches data via market/history.py (broker API or yfinance fallback).
    """

    def __init__(
        self,
        symbol:   str,
        exchange: str = "NSE",
        period:   str = "1y",
        capital:  float = 100000,
    ) -> None:
        self.symbol = symbol.upper()
        self.exchange = exchange.upper()
        self.period = period
        self.initial_capital = capital
        self._df: Optional[pd.DataFrame] = None

    def _load_data(self) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        if self._df is not None:
            return self._df

        from market.history import get_ohlcv

        period_days = {
            "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "3y": 1095, "5y": 1825,
        }
        days = period_days.get(self.period, 365)

        df = get_ohlcv(
            symbol=self.symbol,
            exchange=self.exchange,
            interval="day",
            days=days,
        )

        if df.empty:
            raise RuntimeError(f"No historical data available for {self.symbol}")

        # Drop rows with NaN close prices (common in yfinance for current day)
        df = df.dropna(subset=["close"])
        self._df = df
        return df

    def run(self, strategy: Strategy) -> BacktestResult:
        """Execute the backtest and return results."""
        df = self._load_data()
        signals = strategy.generate_signals(df)

        trades: list[Trade] = []
        position = 0        # 0 = flat, 1 = long
        entry_price = 0.0
        entry_date = ""
        capital = self.initial_capital
        equity = [capital]

        for i in range(1, len(df)):
            date_str = str(df.index[i])[:10]
            price = float(df.iloc[i]["close"])
            signal = int(signals.iloc[i]) if i < len(signals) else 0

            if position == 0 and signal == 1:
                # Enter long
                position = 1
                entry_price = price
                entry_date = date_str

            elif position == 1 and signal == -1:
                # Exit long
                pnl_pct = (price - entry_price) / entry_price * 100
                pnl = capital * pnl_pct / 100
                capital += pnl

                try:
                    entry_dt = pd.Timestamp(entry_date)
                    exit_dt = pd.Timestamp(df.index[i])
                    # Strip timezone for safe subtraction
                    if hasattr(entry_dt, 'tz') and entry_dt.tz:
                        entry_dt = entry_dt.tz_localize(None)
                    if hasattr(exit_dt, 'tz') and exit_dt.tz:
                        exit_dt = exit_dt.tz_localize(None)
                    hold_days = (exit_dt - entry_dt).days
                except Exception:
                    hold_days = 0

                trades.append(Trade(
                    entry_date=entry_date,
                    exit_date=date_str,
                    direction="LONG",
                    entry_price=entry_price,
                    exit_price=price,
                    quantity=int(capital / price) if price > 0 else 0,
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                    hold_days=hold_days,
                    signal=strategy.name,
                ))
                position = 0

            equity.append(capital + (position * capital * (price - entry_price) / entry_price if position and entry_price else 0))

        # Close any open position at last price
        if position == 1:
            last_price = float(df.iloc[-1]["close"])
            pnl_pct = (last_price - entry_price) / entry_price * 100
            pnl = capital * pnl_pct / 100
            capital += pnl
            trades.append(Trade(
                entry_date=entry_date,
                exit_date=str(df.index[-1])[:10],
                direction="LONG",
                entry_price=entry_price,
                exit_price=last_price,
                quantity=0,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 2),
                hold_days=0,
                signal=strategy.name + " (open)",
            ))

        # Calculate metrics
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        first_close = float(df["close"].dropna().iloc[0]) if not df["close"].dropna().empty else 1
        last_close = float(df["close"].dropna().iloc[-1]) if not df["close"].dropna().empty else first_close
        buy_hold = (last_close - first_close) / first_close * 100 if first_close else 0

        # CAGR
        days_total = (df.index[-1] - df.index[0]).days
        years = days_total / 365.25 if days_total > 0 else 1
        cagr = ((capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Sharpe ratio (daily returns)
        equity_series = pd.Series(equity)
        daily_returns = equity_series.pct_change(fill_method=None).dropna()
        sharpe = 0.0
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * math.sqrt(252)

        # Max drawdown
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak * 100
        max_dd = float(drawdown.min())
        max_dd_idx = int(drawdown.idxmin()) if not drawdown.empty else 0
        max_dd_date = str(df.index[min(max_dd_idx, len(df) - 1)])[:10] if max_dd_idx < len(df) else ""

        # Trade stats
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl < 0]
        win_rate = len(winners) / len(trades) * 100 if trades else 0
        avg_win = sum(t.pnl_pct for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.pnl_pct for t in losers) / len(losers) if losers else 0
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_hold = sum(t.hold_days for t in trades) / len(trades) if trades else 0

        return BacktestResult(
            symbol=self.symbol,
            strategy_name=strategy.name,
            period=self.period,
            start_date=str(df.index[0])[:10],
            end_date=str(df.index[-1])[:10],
            total_return=round(total_return, 2),
            cagr=round(cagr, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_date=max_dd_date,
            total_trades=len(trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            avg_hold_days=round(avg_hold, 1),
            buy_hold_return=round(buy_hold, 2),
            trades=trades,
            equity_curve=equity,
        )


def run_backtest(
    symbol: str,
    strategy_name: str = "rsi",
    strategy_args: Optional[list[str]] = None,
    period: str = "1y",
    capital: float = 100000,
) -> BacktestResult:
    """Convenience function for running a named strategy."""
    factory = STRATEGIES.get(strategy_name.lower())
    if not factory:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. "
            f"Available: {', '.join(STRATEGIES.keys())}"
        )

    strategy = factory(strategy_args or [])
    bt = Backtester(symbol=symbol, period=period, capital=capital)
    return bt.run(strategy)


# ── Walk-Forward Testing ─────────────────────────────────────

@dataclass
class WalkForwardResult:
    """Result of walk-forward analysis."""
    symbol:          str
    strategy_name:   str
    windows:         list[dict]    # each window's metrics
    avg_return:      float
    avg_sharpe:      float
    avg_win_rate:    float
    consistency:     float         # % of windows that were profitable
    vs_buy_hold:     float         # avg alpha across windows

    def print_summary(self) -> None:
        from rich.table import Table
        from rich.panel import Panel
        console = Console()

        lines = [
            f"  Strategy    : {self.strategy_name}",
            f"  Symbol      : {self.symbol}",
            f"  Windows     : {len(self.windows)}",
            f"  Avg Return  : {self.avg_return:+.2f}%",
            f"  Avg Sharpe  : {self.avg_sharpe:.2f}",
            f"  Avg Win Rate: {self.avg_win_rate:.1f}%",
            f"  Consistency : {self.consistency:.0f}% of windows profitable",
            f"  Avg Alpha   : {self.vs_buy_hold:+.2f}% vs buy-hold",
        ]
        console.print(Panel("\n".join(lines),
                            title="[bold cyan]Walk-Forward Analysis[/bold cyan]",
                            border_style="cyan"))

        table = Table(title="Window Results", show_lines=False)
        table.add_column("Window", width=25)
        table.add_column("Return", justify="right", width=10)
        table.add_column("Sharpe", justify="right", width=8)
        table.add_column("Trades", justify="right", width=8)
        table.add_column("Win%", justify="right", width=8)
        table.add_column("B&H", justify="right", width=10)

        for w in self.windows:
            ret_style = "green" if w["return"] >= 0 else "red"
            table.add_row(
                w["period"],
                f"[{ret_style}]{w['return']:+.2f}%[/{ret_style}]",
                f"{w['sharpe']:.2f}",
                str(w["trades"]),
                f"{w['win_rate']:.0f}%",
                f"{w['buy_hold']:+.2f}%",
            )
        console.print(table)


def walk_forward_test(
    symbol: str,
    strategy_name: str = "rsi",
    strategy_args: Optional[list[str]] = None,
    total_period: str = "3y",
    window_months: int = 6,
    capital: float = 100000,
) -> WalkForwardResult:
    """
    Walk-forward backtest: split history into rolling windows,
    test strategy on each independently.

    E.g. 3 years split into 6 windows of 6 months each.
    Tests if the strategy works consistently across different regimes.
    """
    from datetime import datetime, timedelta

    factory = STRATEGIES.get(strategy_name.lower())
    if not factory:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    strategy = factory(strategy_args or [])

    period_days = {"1y": 365, "2y": 730, "3y": 1095, "5y": 1825}.get(total_period, 1095)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)

    # Build windows
    window_days = window_months * 30
    windows = []
    current = start_date

    while current + timedelta(days=window_days) <= end_date:
        w_start = current
        w_end = current + timedelta(days=window_days)

        bt = Backtester(symbol=symbol, period="1y", capital=capital)
        # Override dates
        from market.history import get_ohlcv
        df = get_ohlcv(symbol=symbol, from_date=w_start, to_date=w_end, days=window_days)
        if not df.empty:
            df = df.dropna(subset=["close"])
            bt._df = df
            try:
                result = bt.run(strategy)
                windows.append({
                    "period": f"{w_start.strftime('%Y-%m')} → {w_end.strftime('%Y-%m')}",
                    "return": result.total_return,
                    "sharpe": result.sharpe_ratio,
                    "trades": result.total_trades,
                    "win_rate": result.win_rate,
                    "buy_hold": result.buy_hold_return,
                    "max_dd": result.max_drawdown,
                })
            except Exception:
                pass

        current += timedelta(days=window_days)

    if not windows:
        raise RuntimeError(f"No valid windows for {symbol} over {total_period}")

    avg_return = sum(w["return"] for w in windows) / len(windows)
    avg_sharpe = sum(w["sharpe"] for w in windows) / len(windows)
    avg_win_rate = sum(w["win_rate"] for w in windows) / len(windows)
    profitable = sum(1 for w in windows if w["return"] > 0)
    consistency = profitable / len(windows) * 100
    avg_alpha = sum(w["return"] - w["buy_hold"] for w in windows) / len(windows)

    return WalkForwardResult(
        symbol=symbol,
        strategy_name=strategy.name,
        windows=windows,
        avg_return=round(avg_return, 2),
        avg_sharpe=round(avg_sharpe, 2),
        avg_win_rate=round(avg_win_rate, 1),
        consistency=round(consistency, 1),
        vs_buy_hold=round(avg_alpha, 2),
    )
