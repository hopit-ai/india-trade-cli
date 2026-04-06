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

import pandas as pd

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ── Data Models ──────────────────────────────────────────────


@dataclass
class Trade:
    """A single completed trade (entry + exit)."""

    entry_date: str
    exit_date: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    hold_days: int
    signal: str = ""  # what triggered this trade


@dataclass
class BacktestResult:
    """Complete backtest output."""

    symbol: str
    strategy_name: str
    period: str
    start_date: str
    end_date: str

    # Performance
    total_return: float  # %
    cagr: float  # %
    sharpe_ratio: float
    max_drawdown: float  # %
    max_drawdown_date: str = ""

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0  # %
    avg_loss: float = 0.0  # %
    profit_factor: float = 0.0
    avg_hold_days: float = 0.0

    # Comparison
    buy_hold_return: float = 0.0  # %

    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

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
            "  [bold]Returns[/bold]",
            f"  Total Return   : [{ret_style}]{self.total_return:+.2f}%[/{ret_style}]",
            f"  CAGR           : [{ret_style}]{self.cagr:+.2f}%[/{ret_style}]",
            f"  Buy & Hold     : [{bh_style}]{self.buy_hold_return:+.2f}%[/{bh_style}]",
            f"  Alpha          : [{alpha_style}]{alpha:+.2f}%[/{alpha_style}]",
            "",
            "  [bold]Risk[/bold]",
            f"  Sharpe Ratio   : {self.sharpe_ratio:.2f}",
            f"  Max Drawdown   : [red]{self.max_drawdown:.2f}%[/red]",
            "",
            "  [bold]Trades[/bold]",
            f"  Total          : {self.total_trades}",
            f"  Win Rate       : {self.win_rate:.1f}%",
            f"  Avg Win        : [green]{self.avg_win:+.2f}%[/green]",
            f"  Avg Loss       : [red]{self.avg_loss:+.2f}%[/red]",
            f"  Profit Factor  : {self.profit_factor:.2f}",
            f"  Avg Hold       : {self.avg_hold_days:.1f} days",
        ]

        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold cyan]Backtest: {self.strategy_name} on {self.symbol}[/bold cyan]",
                border_style="cyan",
            )
        )

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
                t.entry_date[:10],
                t.exit_date[:10],
                t.direction,
                f"{t.entry_price:,.1f}",
                f"{t.exit_price:,.1f}",
                f"[{pnl_style}]{t.pnl_pct:+.2f}%[/{pnl_style}]",
                str(t.hold_days),
            )
        console.print(table)


# ── Strategy Interface ───────────────────────────────────────


class Strategy(ABC):
    """Base class for backtesting strategies."""

    name: str = "Base"

    # Override this for multi-symbol strategies (e.g., pairs trading)
    symbols: list[str] = []

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series | pd.DataFrame:
        """
        Generate trading signals from OHLCV data.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                (indexed by date)

        Returns:
            - pd.Series of signals: 1 = BUY, -1 = SELL, 0 = HOLD
              (single-symbol mode)
            - pd.DataFrame with one column per symbol, each containing
              1 (LONG), -1 (SHORT), 0 (FLAT)
              (multi-symbol / pairs mode)
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
    "rsi": lambda args: RSIStrategy(
        buy_level=int(args[0]) if args else 30,
        sell_level=int(args[1]) if len(args) > 1 else 70,
    ),
    "ma": lambda args: MACrossStrategy(
        fast=int(args[0]) if args else 20,
        slow=int(args[1]) if len(args) > 1 else 50,
    ),
    "ema": lambda args: MACrossStrategy(
        fast=int(args[0]) if args else 20,
        slow=int(args[1]) if len(args) > 1 else 50,
    ),
    "macd": lambda args: MACDStrategy(),
    "bollinger": lambda args: BollingerStrategy(),
    "bb": lambda args: BollingerStrategy(),
    "supertrend": lambda args: SupertrendStrategy(
        period=int(args[0]) if args else 10,
        multiplier=float(args[1]) if len(args) > 1 else 3.0,
    ),
    "heikin_ashi": lambda args: HeikinAshiStrategy(
        ema_period=int(args[0]) if args else 21,
    ),
    "donchian": lambda args: DonchianStrategy(
        period=int(args[0]) if args else 20,
    ),
    "psar": lambda args: ParabolicSARStrategy(
        step=float(args[0]) if args else 0.02,
        max_step=float(args[1]) if len(args) > 1 else 0.20,
    ),
    "zscore": lambda args: ZScoreStrategy(
        lookback=int(args[0]) if args else 20,
        entry_z=float(args[1]) if len(args) > 1 else 2.0,
    ),
    "keltner": lambda args: KeltnerStrategy(
        ema_period=int(args[0]) if args else 20,
        atr_multiplier=float(args[1]) if len(args) > 1 else 2.0,
    ),
    "inside_bar": lambda args: InsideBarStrategy(),
    "dual_momentum": lambda args: DualMomentumStrategy(
        lookback=int(args[0]) if args else 90,
    ),
}


# ── Extended Strategy Classes ─────────────────────────────────


class SupertrendStrategy(Strategy):
    """ATR-based trailing stop that flips direction on trend change."""

    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier
        self.name = f"Supertrend({period}, {multiplier})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]

        # ATR
        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
        ).max(axis=1)
        atr = tr.rolling(self.period).mean()

        hl2 = (high + low) / 2
        upper_band = hl2 + self.multiplier * atr
        lower_band = hl2 - self.multiplier * atr

        # Iteratively compute Supertrend direction
        trend_arr = [1] * len(df)  # 1 = bullish, -1 = bearish
        fu = upper_band.to_numpy(dtype=float).copy()
        fl = lower_band.to_numpy(dtype=float).copy()
        cl = close.to_numpy(dtype=float)

        import math

        for i in range(1, len(df)):
            curr_lb = lower_band.iloc[i]
            curr_ub = upper_band.iloc[i]

            if math.isnan(curr_lb):
                # ATR not ready yet — hold previous values
                fl[i] = fl[i - 1]
                fu[i] = fu[i - 1]
            elif math.isnan(fl[i - 1]):
                # Bootstrap: first bar with valid ATR
                fl[i] = curr_lb
                fu[i] = curr_ub
            else:
                # Lower band (support): raise only, never lower below previous
                fl[i] = curr_lb if curr_lb > fl[i - 1] or cl[i - 1] < fl[i - 1] else fl[i - 1]
                # Upper band (resistance): lower only, never raise above previous
                fu[i] = curr_ub if curr_ub < fu[i - 1] or cl[i - 1] > fu[i - 1] else fu[i - 1]

            # Trend direction flip
            if trend_arr[i - 1] == -1 and cl[i] > fu[i - 1]:
                trend_arr[i] = 1
            elif trend_arr[i - 1] == 1 and cl[i] < fl[i - 1]:
                trend_arr[i] = -1
            else:
                trend_arr[i] = trend_arr[i - 1]

        trend = pd.Series(trend_arr, index=df.index)

        # Signal: 1 on flip to bullish, -1 on flip to bearish
        signals = pd.Series(0, index=df.index)
        prev_trend = trend.shift(1)
        signals[(prev_trend == -1) & (trend == 1)] = 1
        signals[(prev_trend == 1) & (trend == -1)] = -1
        return signals


class HeikinAshiStrategy(Strategy):
    """Trade on full Heikin Ashi candles (no opposing wicks) with EMA filter."""

    def __init__(self, ema_period: int = 21):
        self.ema_period = ema_period
        self.name = f"Heikin Ashi(EMA {ema_period})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # Compute Heikin Ashi candles
        ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        ha_open = ha_close.copy()
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2
        ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)

        # Full bullish HA candle: no lower wick (ha_low == ha_open), green (close > open)
        bull_no_lower = (ha_low == ha_open) & (ha_close > ha_open)
        # Full bearish HA candle: no upper wick (ha_high == ha_open), red (close < open)
        bear_no_upper = (ha_high == ha_open) & (ha_close < ha_open)

        # EMA filter
        from analysis.technical import ema as calc_ema

        ema_vals = calc_ema(df["close"], self.ema_period)

        signals = pd.Series(0, index=df.index)
        signals[bull_no_lower & (df["close"] > ema_vals)] = 1
        signals[bear_no_upper & (df["close"] < ema_vals)] = -1
        return signals


class DonchianStrategy(Strategy):
    """Turtle Trading: buy 20-day high breakout, sell 20-day low breakdown."""

    def __init__(self, period: int = 20, filter_period: int = 50):
        self.period = period
        self.filter_period = filter_period
        self.name = f"Donchian({period})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        high_break = df["high"].rolling(self.period).max().shift(1)
        low_break = df["low"].rolling(self.period).min().shift(1)
        filter_high = df["high"].rolling(self.filter_period).max().shift(1)
        filter_low = df["low"].rolling(self.filter_period).min().shift(1)

        signals = pd.Series(0, index=df.index)
        # Buy on new N-day high only if price is above 50-day Donchian mid
        mid_filter = (filter_high + filter_low) / 2
        signals[(df["close"] > high_break) & (df["close"] > mid_filter)] = 1
        signals[(df["close"] < low_break) & (df["close"] < mid_filter)] = -1
        return signals


class ParabolicSARStrategy(Strategy):
    """Trailing stop that accelerates with the trend — flip on SAR touch."""

    def __init__(self, step: float = 0.02, max_step: float = 0.20):
        self.step = step
        self.max_step = max_step
        self.name = f"Parabolic SAR({step}, {max_step})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        high, low = df["high"].values, df["low"].values
        n = len(df)

        sar = low[0]
        ep = high[0]
        af = self.step
        bull = True  # current trend direction

        sar_vals = [sar]
        trend = [1]

        for i in range(1, n):
            prev_sar = sar
            if bull:
                sar = prev_sar + af * (ep - prev_sar)
                sar = min(sar, low[i - 1], low[max(0, i - 2)])
                if low[i] < sar:
                    bull = False
                    sar = ep
                    ep = low[i]
                    af = self.step
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + self.step, self.max_step)
            else:
                sar = prev_sar + af * (ep - prev_sar)
                sar = max(sar, high[i - 1], high[max(0, i - 2)])
                if high[i] > sar:
                    bull = True
                    sar = ep
                    ep = high[i]
                    af = self.step
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + self.step, self.max_step)

            sar_vals.append(sar)
            trend.append(1 if bull else -1)

        trend_series = pd.Series(trend, index=df.index)
        prev_trend = trend_series.shift(1)
        signals = pd.Series(0, index=df.index)
        signals[(prev_trend == -1) & (trend_series == 1)] = 1
        signals[(prev_trend == 1) & (trend_series == -1)] = -1
        return signals


class ZScoreStrategy(Strategy):
    """Rolling z-score mean reversion: fade extremes, exit at mean."""

    def __init__(self, lookback: int = 20, entry_z: float = 2.0):
        self.lookback = lookback
        self.entry_z = entry_z
        self.name = f"Z-Score({lookback}, ±{entry_z})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        roll_mean = close.rolling(self.lookback).mean()
        roll_std = close.rolling(self.lookback).std()
        z = (close - roll_mean) / roll_std.replace(0, float("nan"))

        signals = pd.Series(0, index=df.index)
        signals[z < -self.entry_z] = 1  # oversold → buy
        signals[z > self.entry_z] = -1  # overbought → sell
        return signals.fillna(0).astype(int)


class KeltnerStrategy(Strategy):
    """ATR-based Keltner Channel: fade price at extreme bands."""

    def __init__(self, ema_period: int = 20, atr_multiplier: float = 2.0, atr_period: int = 10):
        self.ema_period = ema_period
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.name = f"Keltner({ema_period}, {atr_multiplier}×ATR)"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        from analysis.technical import ema as calc_ema

        mid = calc_ema(df["close"], self.ema_period)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift()).abs(),
                (df["low"] - df["close"].shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(self.atr_period).mean()

        upper = mid + self.atr_multiplier * atr
        lower = mid - self.atr_multiplier * atr

        signals = pd.Series(0, index=df.index)
        signals[df["close"] < lower] = 1
        signals[df["close"] > upper] = -1
        return signals


class InsideBarStrategy(Strategy):
    """Inside bar (range within prior candle) breakout on daily charts."""

    def __init__(self):
        self.name = "Inside Bar Breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        prev_high = df["high"].shift(1)
        prev_low = df["low"].shift(1)

        # Inside bar: current high < prev high AND current low > prev low
        is_inside = (df["high"] < prev_high) & (df["low"] > prev_low)

        # Signal fires on the candle AFTER the inside bar
        inside_shifted = is_inside.shift(1)
        signals = pd.Series(0, index=df.index)
        # Break above prior high after inside bar = bullish
        signals[inside_shifted & (df["close"] > prev_high)] = 1
        # Break below prior low after inside bar = bearish
        signals[inside_shifted & (df["close"] < prev_low)] = -1
        return signals


class DualMomentumStrategy(Strategy):
    """
    Antonacci Dual Momentum: absolute + relative momentum with monthly rebalance.

    Absolute: if N-day return > 0 → stay in equities.
    Signal on rebalance days only (approx every 21 trading days).
    """

    def __init__(self, lookback: int = 90):
        self.lookback = lookback
        self.name = f"Dual Momentum({lookback}d)"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        momentum = close / close.shift(self.lookback) - 1  # N-day return

        signals = pd.Series(0, index=df.index)
        # Rebalance approximately monthly (every 21 trading days)
        rebalance_days = range(self.lookback, len(df), 21)
        for i in rebalance_days:
            if i < len(df):
                if momentum.iloc[i] > 0:
                    signals.iloc[i] = 1  # positive momentum → stay/go long
                else:
                    signals.iloc[i] = -1  # negative → exit / go to safety
        return signals


# ── Backtester Engine ────────────────────────────────────────


class Backtester:
    """
    Run a strategy against historical OHLCV data.

    Fetches data via market/history.py (broker API or yfinance fallback).
    """

    def __init__(
        self,
        symbol: str,
        exchange: str = "NSE",
        period: str = "1y",
        capital: float = 100000,
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
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "3y": 1095,
            "5y": 1825,
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

    def run(self, strategy: Strategy) -> BacktestResult | MultiBacktestResult:
        """Execute the backtest and return results.

        If the strategy returns a DataFrame of signals (multi-symbol),
        automatically delegates to MultiBacktester.
        """
        df = self._load_data()
        signals = strategy.generate_signals(df)

        # Auto-detect multi-symbol strategies
        if isinstance(signals, pd.DataFrame) and len(signals.columns) > 1:
            symbols = list(signals.columns)
            multi = MultiBacktester(
                symbols=symbols,
                exchange=self.exchange,
                period=self.period,
                capital=self.initial_capital,
            )
            return multi.run(strategy)

        trades: list[Trade] = []
        position = 0  # 0 = flat, 1 = long
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
                    if hasattr(entry_dt, "tz") and entry_dt.tz:
                        entry_dt = entry_dt.tz_localize(None)
                    if hasattr(exit_dt, "tz") and exit_dt.tz:
                        exit_dt = exit_dt.tz_localize(None)
                    hold_days = (exit_dt - entry_dt).days
                except Exception:
                    hold_days = 0

                trades.append(
                    Trade(
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
                    )
                )
                position = 0

            equity.append(
                capital
                + (
                    position * capital * (price - entry_price) / entry_price
                    if position and entry_price
                    else 0
                )
            )

        # Close any open position at last price
        if position == 1:
            last_price = float(df.iloc[-1]["close"])
            pnl_pct = (last_price - entry_price) / entry_price * 100
            pnl = capital * pnl_pct / 100
            capital += pnl
            trades.append(
                Trade(
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
                )
            )

        # Calculate metrics
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        first_close = float(df["close"].dropna().iloc[0]) if not df["close"].dropna().empty else 1
        last_close = (
            float(df["close"].dropna().iloc[-1]) if not df["close"].dropna().empty else first_close
        )
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
        max_dd_date = (
            str(df.index[min(max_dd_idx, len(df) - 1)])[:10] if max_dd_idx < len(df) else ""
        )

        # Trade stats
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl < 0]
        win_rate = len(winners) / len(trades) * 100 if trades else 0
        avg_win = sum(t.pnl_pct for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.pnl_pct for t in losers) / len(losers) if losers else 0
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
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


# ── Multi-Symbol (Pairs) Backtester ──────────────────────────


@dataclass
class TradeLeg:
    """One leg of a multi-symbol trade."""

    symbol: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float


@dataclass
class PairTrade:
    """A complete multi-symbol trade (entry + exit on all legs)."""

    entry_date: str
    exit_date: str
    legs: list[TradeLeg]
    combined_pnl: float
    combined_pnl_pct: float
    hold_days: int


@dataclass
class MultiBacktestResult:
    """Backtest result for multi-symbol strategies (pairs, hedged, etc.)."""

    symbols: list[str]
    strategy_name: str
    period: str
    start_date: str
    end_date: str

    # Performance
    total_return: float  # %
    cagr: float  # %
    sharpe_ratio: float
    max_drawdown: float  # %

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    avg_hold_days: float = 0.0

    trades: list[PairTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

    def print_summary(self) -> None:
        """Display multi-symbol backtest results."""
        ret_style = "green" if self.total_return >= 0 else "red"

        lines = [
            f"  Strategy       : [bold]{self.strategy_name}[/bold]",
            f"  Symbols        : {', '.join(self.symbols)}",
            f"  Period         : {self.start_date} → {self.end_date}",
            "",
            "  [bold]Returns[/bold]",
            f"  Total Return   : [{ret_style}]{self.total_return:+.2f}%[/{ret_style}]",
            f"  CAGR           : [{ret_style}]{self.cagr:+.2f}%[/{ret_style}]",
            "",
            "  [bold]Risk[/bold]",
            f"  Sharpe Ratio   : {self.sharpe_ratio:.2f}",
            f"  Max Drawdown   : [red]{self.max_drawdown:.2f}%[/red]",
            "",
            "  [bold]Trades[/bold]",
            f"  Total          : {self.total_trades}",
            f"  Win Rate       : {self.win_rate:.1f}%",
            f"  Avg Win        : [green]{self.avg_win:+.2f}%[/green]",
            f"  Avg Loss       : [red]{self.avg_loss:+.2f}%[/red]",
            f"  Profit Factor  : {self.profit_factor:.2f}",
            f"  Avg Hold       : {self.avg_hold_days:.1f} days",
        ]

        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold cyan]Pairs Backtest: {self.strategy_name}[/bold cyan]",
                border_style="cyan",
            )
        )

    def print_trades(self, n: int = 20) -> None:
        """Show pair trades with all legs."""
        trades = self.trades[-n:]
        if not trades:
            console.print("[dim]No trades executed.[/dim]")
            return

        for i, t in enumerate(trades, 1):
            pnl_style = "green" if t.combined_pnl_pct >= 0 else "red"
            console.print(
                f"\n  [bold]Trade #{i}[/bold]: {t.entry_date} → {t.exit_date} "
                f"({t.hold_days}d)  "
                f"Combined P&L: [{pnl_style}]{t.combined_pnl_pct:+.2f}%[/{pnl_style}]"
            )
            for leg in t.legs:
                leg_style = "green" if leg.pnl_pct >= 0 else "red"
                dir_color = "green" if leg.direction == "LONG" else "red"
                console.print(
                    f"    [{dir_color}]{leg.direction:5s}[/{dir_color}] "
                    f"{leg.symbol:12s}  "
                    f"₹{leg.entry_price:>10,.1f} → ₹{leg.exit_price:>10,.1f}  "
                    f"[{leg_style}]{leg.pnl_pct:+.2f}%[/{leg_style}]"
                )
        console.print()


class MultiBacktester:
    """
    Backtest multi-symbol strategies (pairs, hedged, spread).

    Loads OHLCV data for all symbols, aligns to common dates,
    and tracks positions + P&L on all legs simultaneously.
    """

    def __init__(
        self,
        symbols: list[str],
        exchange: str = "NSE",
        period: str = "1y",
        capital: float = 100000,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.exchange = exchange.upper()
        self.period = period
        self.initial_capital = capital
        self._data: dict[str, pd.DataFrame] = {}

    def _load_data(self) -> dict[str, pd.DataFrame]:
        """Fetch and align OHLCV data for all symbols."""
        if self._data:
            return self._data

        from market.history import get_ohlcv

        period_days = {
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "3y": 1095,
            "5y": 1825,
        }
        days = period_days.get(self.period, 365)

        raw = {}
        for sym in self.symbols:
            df = get_ohlcv(symbol=sym, exchange=self.exchange, interval="day", days=days)
            if df.empty:
                raise RuntimeError(f"No historical data for {sym}")
            df = df.dropna(subset=["close"])
            raw[sym] = df

        # Align to common dates
        common_idx = raw[self.symbols[0]].index
        for sym in self.symbols[1:]:
            common_idx = common_idx.intersection(raw[sym].index)

        if len(common_idx) < 20:
            raise RuntimeError(
                f"Only {len(common_idx)} common trading days across {self.symbols}. "
                "Need at least 20 for a meaningful backtest."
            )

        for sym in self.symbols:
            raw[sym] = raw[sym].loc[common_idx]

        self._data = raw
        return raw

    def run(self, strategy: Strategy) -> MultiBacktestResult:
        """Execute the multi-symbol backtest."""
        data = self._load_data()

        # Build a combined DataFrame with multi-level columns for the strategy
        # The strategy's generate_signals receives the primary symbol's df
        # but can access other symbols' data internally.
        # We pass the first symbol's df as the main input.
        primary_df = data[self.symbols[0]]
        signals = strategy.generate_signals(primary_df)

        # Handle both Series and DataFrame returns
        if isinstance(signals, pd.Series):
            # Single-symbol signal applied to first symbol only
            sig_df = pd.DataFrame({self.symbols[0]: signals})
            # Fill missing symbols with 0
            for sym in self.symbols[1:]:
                sig_df[sym] = 0
        elif isinstance(signals, pd.DataFrame):
            sig_df = signals
        else:
            raise TypeError(
                f"generate_signals must return Series or DataFrame, got {type(signals)}"
            )

        # Align signals to common index
        common_idx = primary_df.index
        sig_df = sig_df.reindex(common_idx, fill_value=0)

        # Simulation: track positions per symbol
        positions: dict[str, int] = {s: 0 for s in self.symbols}  # 0=flat, 1=long, -1=short
        entry_prices: dict[str, float] = {s: 0.0 for s in self.symbols}
        entry_date = ""

        capital = self.initial_capital
        capital_per_leg = capital / max(len(self.symbols), 1)
        equity = [capital]
        trades: list[PairTrade] = []

        for i in range(1, len(common_idx)):
            date_str = str(common_idx[i])[:10]
            prices = {sym: float(data[sym].iloc[i]["close"]) for sym in self.symbols}

            # Read signals for this bar
            bar_signals = {}
            for sym in self.symbols:
                if sym in sig_df.columns:
                    bar_signals[sym] = int(sig_df[sym].iloc[i]) if i < len(sig_df) else 0
                else:
                    bar_signals[sym] = 0

            # Check for entry: all symbols go from flat to non-zero
            all_flat = all(positions[s] == 0 for s in self.symbols)
            any_signal = any(bar_signals[s] != 0 for s in self.symbols)

            if all_flat and any_signal:
                # Enter positions
                for sym in self.symbols:
                    sig = bar_signals[sym]
                    if sig != 0:
                        positions[sym] = sig
                        entry_prices[sym] = prices[sym]
                entry_date = date_str

            # Check for exit: any symbol signals to close (goes to 0 or flips)
            any_position = any(positions[s] != 0 for s in self.symbols)
            if any_position:
                # Exit if any active symbol's signal returns to 0 or flips
                should_exit = False
                for sym in self.symbols:
                    if positions[sym] != 0:
                        new_sig = bar_signals[sym]
                        if new_sig == 0 or (new_sig != 0 and new_sig != positions[sym]):
                            should_exit = True
                            break

                if should_exit:
                    # Close all positions
                    legs = []
                    total_pnl = 0.0
                    for sym in self.symbols:
                        if positions[sym] != 0:
                            ep = entry_prices[sym]
                            xp = prices[sym]
                            direction = "LONG" if positions[sym] == 1 else "SHORT"

                            if positions[sym] == 1:
                                pnl_pct = (xp - ep) / ep * 100
                            else:
                                pnl_pct = (ep - xp) / ep * 100

                            pnl = capital_per_leg * pnl_pct / 100
                            total_pnl += pnl

                            legs.append(
                                TradeLeg(
                                    symbol=sym,
                                    direction=direction,
                                    entry_price=round(ep, 2),
                                    exit_price=round(xp, 2),
                                    quantity=max(1, int(capital_per_leg / ep)) if ep > 0 else 0,
                                    pnl=round(pnl, 2),
                                    pnl_pct=round(pnl_pct, 2),
                                )
                            )

                    capital += total_pnl
                    combined_pct = (
                        total_pnl / (capital_per_leg * len([l for l in legs])) * 100 if legs else 0
                    )

                    try:
                        entry_dt = pd.Timestamp(entry_date)
                        exit_dt = pd.Timestamp(common_idx[i])
                        if hasattr(entry_dt, "tz") and entry_dt.tz:
                            entry_dt = entry_dt.tz_localize(None)
                        if hasattr(exit_dt, "tz") and exit_dt.tz:
                            exit_dt = exit_dt.tz_localize(None)
                        hold_days = (exit_dt - entry_dt).days
                    except Exception:
                        hold_days = 0

                    trades.append(
                        PairTrade(
                            entry_date=entry_date,
                            exit_date=date_str,
                            legs=legs,
                            combined_pnl=round(total_pnl, 2),
                            combined_pnl_pct=round(combined_pct, 2),
                            hold_days=hold_days,
                        )
                    )

                    # Reset
                    for sym in self.symbols:
                        positions[sym] = 0
                        entry_prices[sym] = 0.0

                    # Update capital per leg
                    capital_per_leg = capital / max(len(self.symbols), 1)

            # Update equity: mark-to-market open positions
            unrealized = 0.0
            for sym in self.symbols:
                if positions[sym] != 0:
                    ep = entry_prices[sym]
                    cp = prices[sym]
                    if positions[sym] == 1:
                        unrealized += capital_per_leg * (cp - ep) / ep
                    else:
                        unrealized += capital_per_leg * (ep - cp) / ep
            equity.append(capital + unrealized)

        # Close any open positions at last bar
        if any(positions[s] != 0 for s in self.symbols):
            last_prices = {sym: float(data[sym].iloc[-1]["close"]) for sym in self.symbols}
            legs = []
            total_pnl = 0.0
            for sym in self.symbols:
                if positions[sym] != 0:
                    ep = entry_prices[sym]
                    xp = last_prices[sym]
                    direction = "LONG" if positions[sym] == 1 else "SHORT"
                    pnl_pct = (
                        ((xp - ep) / ep * 100) if positions[sym] == 1 else ((ep - xp) / ep * 100)
                    )
                    pnl = capital_per_leg * pnl_pct / 100
                    total_pnl += pnl
                    legs.append(
                        TradeLeg(
                            sym,
                            direction,
                            round(ep, 2),
                            round(xp, 2),
                            0,
                            round(pnl, 2),
                            round(pnl_pct, 2),
                        )
                    )

            capital += total_pnl
            combined_pct = total_pnl / (capital_per_leg * len(legs)) * 100 if legs else 0
            trades.append(
                PairTrade(
                    entry_date=entry_date,
                    exit_date=str(common_idx[-1])[:10],
                    legs=legs,
                    combined_pnl=round(total_pnl, 2),
                    combined_pnl_pct=round(combined_pct, 2),
                    hold_days=0,
                )
            )

        # ── Metrics ──────────────────────────────────────────
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        days_total = (common_idx[-1] - common_idx[0]).days
        years = days_total / 365.25 if days_total > 0 else 1
        cagr = ((capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        eq = pd.Series(equity)
        daily_ret = eq.pct_change(fill_method=None).dropna()
        sharpe = 0.0
        if len(daily_ret) > 1 and daily_ret.std() > 0:
            sharpe = (daily_ret.mean() / daily_ret.std()) * math.sqrt(252)

        peak = eq.expanding().max()
        dd = (eq - peak) / peak * 100
        max_dd = float(dd.min())

        winners = [t for t in trades if t.combined_pnl > 0]
        losers = [t for t in trades if t.combined_pnl < 0]
        win_rate = len(winners) / len(trades) * 100 if trades else 0
        avg_win = sum(t.combined_pnl_pct for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t.combined_pnl_pct for t in losers) / len(losers) if losers else 0
        gross_profit = sum(t.combined_pnl for t in winners)
        gross_loss = abs(sum(t.combined_pnl for t in losers))
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        avg_hold = sum(t.hold_days for t in trades) / len(trades) if trades else 0

        return MultiBacktestResult(
            symbols=self.symbols,
            strategy_name=strategy.name,
            period=self.period,
            start_date=str(common_idx[0])[:10],
            end_date=str(common_idx[-1])[:10],
            total_return=round(total_return, 2),
            cagr=round(cagr, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            total_trades=len(trades),
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=round(win_rate, 1),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(pf, 2),
            avg_hold_days=round(avg_hold, 1),
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
    """Convenience function for running a named strategy.

    If strategy_name starts with "user:", loads a user-saved strategy
    from ~/.trading_platform/strategies/ via StrategyStore.
    """
    # User-saved strategies: "user:my_strategy"
    if strategy_name.startswith("user:"):
        from engine.strategy_builder import strategy_store

        user_name = strategy_name[5:]
        strategy = strategy_store.load_strategy(user_name)
        bt = Backtester(symbol=symbol, period=period, capital=capital)
        return bt.run(strategy)

    factory = STRATEGIES.get(strategy_name.lower())
    if not factory:
        # Also check user strategies as fallback
        try:
            from engine.strategy_builder import strategy_store

            strategy = strategy_store.load_strategy(strategy_name)
            bt = Backtester(symbol=symbol, period=period, capital=capital)
            return bt.run(strategy)
        except Exception:
            pass

        # Check options strategies
        try:
            from engine.options_backtest import OPTIONS_STRATEGIES, run_options_backtest

            if strategy_name.lower() in OPTIONS_STRATEGIES:
                return run_options_backtest(symbol, strategy_name, strategy_args, period, capital)
        except ImportError:
            pass

        raise ValueError(
            f"Unknown strategy: {strategy_name}. Available: {', '.join(STRATEGIES.keys())}"
        )

    strategy = factory(strategy_args or [])
    bt = Backtester(symbol=symbol, period=period, capital=capital)
    return bt.run(strategy)


# ── Walk-Forward Testing ─────────────────────────────────────


@dataclass
class WalkForwardResult:
    """Result of walk-forward analysis."""

    symbol: str
    strategy_name: str
    windows: list[dict]  # each window's metrics
    avg_return: float
    avg_sharpe: float
    avg_win_rate: float
    consistency: float  # % of windows that were profitable
    vs_buy_hold: float  # avg alpha across windows

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
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]Walk-Forward Analysis[/bold cyan]",
                border_style="cyan",
            )
        )

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
                windows.append(
                    {
                        "period": f"{w_start.strftime('%Y-%m')} → {w_end.strftime('%Y-%m')}",
                        "return": result.total_return,
                        "sharpe": result.sharpe_ratio,
                        "trades": result.total_trades,
                        "win_rate": result.win_rate,
                        "buy_hold": result.buy_hold_return,
                        "max_dd": result.max_drawdown,
                    }
                )
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
