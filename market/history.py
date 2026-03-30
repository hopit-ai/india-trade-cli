"""
market/history.py
─────────────────
Historical OHLCV data. Fetches via the active broker (Zerodha/Groww/Mock).
Returns pandas DataFrames for downstream analysis.

Intervals supported (Zerodha notation):
    "minute", "3minute", "5minute", "10minute", "15minute",
    "30minute", "60minute", "day"
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing   import Optional

import pandas as pd



# ── Interval aliases ─────────────────────────────────────────

INTERVAL_MAP = {
    "1m":  "minute",
    "3m":  "3minute",
    "5m":  "5minute",
    "10m": "10minute",
    "15m": "15minute",
    "30m": "30minute",
    "1h":  "60minute",
    "1d":  "day",
    "day": "day",
}


def get_ohlcv(
    symbol:    str,
    exchange:  str = "NSE",
    interval:  str = "day",
    from_date: Optional[datetime] = None,
    to_date:   Optional[datetime] = None,
    days:      int = 365,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data as a DataFrame.

    Args:
        symbol:    Trading symbol e.g. "RELIANCE", "NIFTY 50"
        exchange:  "NSE" | "BSE" | "NFO" | "MCX"
        interval:  Candle size — "day", "1h", "15m", "5m", "1m" etc.
        from_date: Start date (default: today - days)
        to_date:   End date (default: today)
        days:      Lookback in days if from_date not given (max 2000 for day)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
        Index: date (datetime)
    """
    from brokers.session import get_broker
    broker = get_broker()

    to_date   = to_date   or datetime.now()
    from_date = from_date or (to_date - timedelta(days=days))

    # Normalize interval alias
    kite_interval = INTERVAL_MAP.get(interval, interval)

    # Use the unified broker interface; fall back to yfinance (real data)
    # if the broker doesn't support historical data, then mock as last resort.
    try:
        raw = broker.get_historical_data(
            symbol    = symbol,
            exchange  = exchange,
            interval  = kite_interval,
            from_date = from_date,
            to_date   = to_date,
        )
    except (NotImplementedError, Exception):
        raw = _yfinance_fallback(symbol, exchange, kite_interval, from_date, to_date)
        if not raw:
            raw = _mock_ohlcv(symbol, from_date, to_date)

    if not raw:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(raw)
    df.rename(columns={"date": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df.sort_index(inplace=True)
    return df


def _yfinance_fallback(
    symbol: str,
    exchange: str,
    interval: str,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """Try yfinance for real market data when broker API is unavailable."""
    try:
        from market.yfinance_provider import yf_get_ohlcv, yf_available
        if not yf_available():
            return []
        return yf_get_ohlcv(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
        )
    except Exception:
        return []


def _get_instrument_token(symbol: str, exchange: str) -> int:
    """Look up instrument token from broker's instrument list."""
    from brokers.session import get_broker
    broker = get_broker()
    if not hasattr(broker, "kite"):
        return 0
    instruments = broker.kite.instruments(exchange)
    for inst in instruments:
        if inst["tradingsymbol"] == symbol:
            return inst["instrument_token"]
    raise ValueError(f"Instrument not found: {exchange}:{symbol}")


def _mock_ohlcv(
    symbol: str,
    from_date: datetime,
    to_date: datetime,
) -> list[dict]:
    """
    Generate synthetic OHLCV data for mock/paper broker.
    Produces a realistic-looking price series using random walk.
    """
    import random
    import math

    base_prices = {
        "RELIANCE": 2650, "HDFCBANK": 1580, "INFY": 1720,
        "TCS": 3800, "ICICIBANK": 1087, "SBIN": 778,
        "NIFTY 50": 22000, "BANKNIFTY": 47000, "INDIA VIX": 14,
    }
    price = base_prices.get(symbol.upper(), 1000)

    rows = []
    current = from_date
    random.seed(hash(symbol) % 10000)

    while current <= to_date:
        # Skip weekends
        if current.weekday() < 5:
            change_pct = random.gauss(0.0003, 0.012)    # ~1.2% daily vol
            open_  = price
            close  = round(price * (1 + change_pct), 2)
            high   = round(max(open_, close) * (1 + abs(random.gauss(0, 0.004))), 2)
            low    = round(min(open_, close) * (1 - abs(random.gauss(0, 0.004))), 2)
            volume = int(random.gauss(5_000_000, 1_500_000))
            rows.append({
                "date":   current,
                "open":   open_,
                "high":   high,
                "low":    low,
                "close":  close,
                "volume": max(volume, 100_000),
            })
            price = close
        current += timedelta(days=1)

    return rows


def get_ohlcv_mock(symbol: str, days: int = 365) -> pd.DataFrame:
    """Convenience: always returns mock data regardless of broker."""
    to_date   = datetime.now()
    from_date = to_date - timedelta(days=days)
    raw = _mock_ohlcv(symbol, from_date, to_date)
    df = pd.DataFrame(raw)
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    return df[["open", "high", "low", "close", "volume"]].astype(float)
