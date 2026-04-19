"""
engine/backtest_vectorized.py
──────────────────────────────
Vectorized backtesting engine for fast signal research (#158).

Uses pandas array operations — no bar-by-bar loop.
Trade-off: no slippage/fill simulation (use event-driven for final validation).

Target: <1 second for 1-year daily data.

Usage:
    from engine.backtest_vectorized import run_vectorized_backtest, vectorized_backtest
    import pandas as pd

    # With live data fetch:
    result = run_vectorized_backtest("RELIANCE", "rsi", "1y")

    # With pre-built DataFrame (for testing):
    result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from engine.backtest import BacktestResult

# ── Data fetcher (thin shim — reuses yfinance or broker quotes) ─


def _fetch_ohlcv(symbol: str, period: str = "1y", exchange: str = "NSE") -> pd.DataFrame:
    """
    Fetch daily OHLCV data for the symbol.
    Returns a DataFrame indexed by date with columns: open, high, low, close, volume.
    Raises ValueError on empty result.
    """
    try:
        import yfinance as yf

        suffix = ".NS" if exchange.upper() in ("NSE", "NFO") else ".BO"
        ticker = f"{symbol}{suffix}"
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        # yfinance may return MultiIndex columns like ('Close', 'INFY.NS') — flatten to plain strings
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]
        df = df.dropna()
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")
        return df
    except ImportError:
        raise ImportError("yfinance is required for vectorized backtest. Run: pip install yfinance")


# ── Signal generators ──────────────────────────────────────────


def _signals_rsi(
    close: pd.Series, period: int = 14, oversold: int = 30, overbought: int = 70
) -> pd.Series:
    """RSI strategy: buy on oversold→above cross, sell on overbought→below cross."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Signal: +1 = buy, -1 = sell, 0 = hold
    signal = pd.Series(0, index=close.index)
    signal[rsi > overbought] = -1  # sell/exit
    signal[rsi < oversold] = 1  # buy/enter
    return signal


def _signals_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> pd.Series:
    """MACD crossover: buy when MACD crosses above signal, sell on reverse."""
    ema_fast = close.ewm(span=fast, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, min_periods=slow).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal_period, min_periods=signal_period).mean()
    hist = macd - sig

    # Cross detection
    signal = pd.Series(0, index=close.index)
    signal[(hist > 0) & (hist.shift(1) <= 0)] = 1  # bullish cross
    signal[(hist < 0) & (hist.shift(1) >= 0)] = -1  # bearish cross
    return signal


def _signals_bollinger(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """Bollinger Bands: buy when price crosses above lower band, sell on upper."""
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    lower = sma - std_dev * std
    upper = sma + std_dev * std

    signal = pd.Series(0, index=close.index)
    signal[(close < lower) & (close.shift(1) >= lower.shift(1))] = 1
    signal[(close > upper) & (close.shift(1) <= upper.shift(1))] = -1
    return signal


def _signals_ma_cross(close: pd.Series, fast: int = 20, slow: int = 50) -> pd.Series:
    """Moving average crossover: buy on fast>slow cross, sell on reverse."""
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()

    signal = pd.Series(0, index=close.index)
    signal[(ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))] = 1
    signal[(ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))] = -1
    return signal


_STRATEGY_MAP = {
    "rsi": _signals_rsi,
    "macd": _signals_macd,
    "bollinger": _signals_bollinger,
    "bb": _signals_bollinger,
    "ma": _signals_ma_cross,
    "ema": _signals_ma_cross,
}


# ── Metrics helpers ─────────────────────────────────────────────


def _calc_sharpe(returns: pd.Series, risk_free: float = 0.0, periods: int = 252) -> float:
    """Annualised Sharpe ratio from daily returns."""
    excess = returns - risk_free / periods
    std = excess.std()
    if std == 0 or math.isnan(std):
        return 0.0
    return float((excess.mean() / std) * math.sqrt(periods))


def _calc_max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a negative percentage."""
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max * 100
    return float(drawdown.min())


def _calc_cagr(total_return: float, years: float) -> float:
    """CAGR from total return % and holding years."""
    if years <= 0:
        return total_return
    return ((1 + total_return / 100) ** (1 / years) - 1) * 100


# ── Vectorized backtest core ────────────────────────────────────


def vectorized_backtest(
    df: pd.DataFrame,
    strategy_name: str = "rsi",
    symbol: str = "UNKNOWN",
) -> BacktestResult:
    """
    Run vectorized backtest on pre-loaded OHLCV DataFrame.
    Returns BacktestResult with same fields as event-driven engine.

    Args:
        df: DataFrame with columns: open, high, low, close, volume. Date-indexed.
        strategy_name: One of rsi, macd, bollinger/bb, ma/ema.
        symbol: Ticker symbol for display.
    """
    close = df["close"].astype(float)
    if len(close) < 30:
        raise ValueError(f"Not enough data: {len(close)} bars (need ≥30)")

    # Get signal function
    signal_fn = _STRATEGY_MAP.get(strategy_name.lower(), _signals_rsi)
    signals = signal_fn(close)

    # ── Generate trades ────────────────────────────────────────
    # Position: 1 = long, 0 = flat. Enter on buy signal, exit on sell.
    position = pd.Series(0, index=close.index, dtype=int)
    in_trade = False
    entries: list[tuple] = []
    exits: list[tuple] = []
    entry_price = 0.0
    entry_date = None

    for i, (date, sig) in enumerate(signals.items()):
        price = float(close.iloc[i])
        if sig == 1 and not in_trade:
            in_trade = True
            entry_price = price
            entry_date = date
            position.iloc[i] = 1
        elif sig == -1 and in_trade:
            in_trade = False
            pct = (price / entry_price - 1) * 100
            entries.append((entry_date, entry_price))
            exits.append((date, price, pct))
            position.iloc[i] = 0
        elif in_trade:
            position.iloc[i] = 1

    # Close any open trade at end
    if in_trade:
        last_price = float(close.iloc[-1])
        pct = (last_price / entry_price - 1) * 100
        entries.append((entry_date, entry_price))
        exits.append((close.index[-1], last_price, pct))

    # ── Equity curve ────────────────────────────────────────────
    daily_returns = close.pct_change().fillna(0)
    strategy_returns = daily_returns * position.shift(1).fillna(0)
    equity = (1 + strategy_returns).cumprod() * 100
    equity_list = equity.tolist()

    # ── Metrics ────────────────────────────────────────────────
    trade_rets = [e[2] for e in exits]
    wins = [r for r in trade_rets if r > 0]
    losses = [r for r in trade_rets if r <= 0]

    total_return = float(equity.iloc[-1] - 100)
    bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

    years = len(close) / 252
    cagr = _calc_cagr(total_return, years)
    sharpe = _calc_sharpe(strategy_returns)
    max_dd = _calc_max_drawdown(equity)

    win_rate = len(wins) / max(len(trade_rets), 1) * 100
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    profit_factor = (
        abs(sum(wins)) / max(abs(sum(losses)), 1e-9)
        if losses
        else float(sum(wins))
        if wins
        else 0.0
    )

    start_date = str(close.index[0])[:10]
    end_date = str(close.index[-1])[:10]

    return BacktestResult(
        symbol=symbol.upper(),
        strategy_name=strategy_name.lower(),
        period=f"{round(years, 1)}y",
        start_date=start_date,
        end_date=end_date,
        total_return=round(total_return, 2),
        cagr=round(cagr, 2),
        sharpe_ratio=round(sharpe, 2),
        max_drawdown=round(max_dd, 2),
        total_trades=len(trade_rets),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(win_rate, 1),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2),
        avg_hold_days=0.0,
        buy_hold_return=round(bh_return, 2),
        equity_curve=equity_list,
    )


# ── Public entry point ──────────────────────────────────────────


def run_vectorized_backtest(
    symbol: str,
    strategy_name: str = "rsi",
    period: str = "1y",
    exchange: str = "NSE",
) -> BacktestResult:
    """
    Fetch OHLCV data and run vectorized backtest.
    Uses yfinance for data. Returns BacktestResult.
    """
    df = _fetch_ohlcv(symbol, period=period, exchange=exchange)
    return vectorized_backtest(df, strategy_name=strategy_name, symbol=symbol)
