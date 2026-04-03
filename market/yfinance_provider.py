"""
market/yfinance_provider.py
───────────────────────────
Free market data via Yahoo Finance — no broker login required.

Provides:
  - Historical OHLCV (daily, weekly — 20+ years of history)
  - Live quotes (~15 min delayed)
  - Index data (NIFTY 50, BANKNIFTY, SENSEX, India VIX)
  - Basic fundamentals (PE, market cap, sector)

Usage:
    from market.yfinance_provider import yf_get_quote, yf_get_ohlcv, yf_get_ltp

    # Live quote
    quote = yf_get_quote("RELIANCE")

    # Historical data
    df = yf_get_ohlcv("RELIANCE", period="1y", interval="1d")

    # LTP
    price = yf_get_ltp("RELIANCE")

Symbol mapping:
    NSE stocks  → append ".NS"  (RELIANCE → RELIANCE.NS)
    BSE stocks  → append ".BO"  (RELIANCE → RELIANCE.BO)
    NIFTY 50    → ^NSEI
    BANKNIFTY   → ^NSEBANK
    SENSEX      → ^BSESN
    India VIX   → ^INDIAVIX

Install:
    pip install yfinance
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from brokers.base import Quote


# ── Symbol mapping ───────────────────────────────────────────

# Index symbols that don't follow the .NS convention
_INDEX_MAP = {
    "NIFTY 50": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "INDIA VIX": "^INDIAVIX",
    "VIX": "^INDIAVIX",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY FIN SERVICE": "^CNXFIN",
    "NIFTY MIDCAP 100": "^CNXMIDCAP",
}


def _to_yf_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert NSE/BSE symbol to Yahoo Finance ticker."""
    # Strip exchange prefix if present (e.g. "NSE:RELIANCE" → "RELIANCE")
    if ":" in symbol:
        exchange, symbol = symbol.split(":", 1)

    upper = symbol.upper()

    # Strip Fyers-specific suffixes before index/stock lookup
    if upper.endswith("-EQ"):
        upper = upper[:-3]
        symbol = symbol[:-3]
    elif upper.endswith("-INDEX"):
        upper = upper[:-6]
        symbol = symbol[:-6]

    # Check index map first
    if upper in _INDEX_MAP:
        return _INDEX_MAP[upper]

    # Regular stocks
    if exchange.upper() == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


def _from_instrument(instrument: str) -> str:
    """Convert 'NSE:RELIANCE' or 'NSE:RELIANCE-EQ' format to yfinance ticker."""
    if ":" in instrument:
        exchange, symbol = instrument.split(":", 1)
        if symbol.endswith("-EQ"):
            symbol = symbol[:-3]
        return _to_yf_symbol(symbol, exchange)
    return _to_yf_symbol(instrument)


# ── Lazy import ──────────────────────────────────────────────


def _get_yf():
    """Lazy import yfinance to avoid import overhead when not needed."""
    try:
        import yfinance as yf

        return yf
    except ImportError:
        raise RuntimeError(
            "yfinance not installed. Run: pip install yfinance\n"
            "This is needed for free market data without a broker login."
        )


# ── Quote functions ──────────────────────────────────────────


def yf_get_quote(symbol: str, exchange: str = "NSE") -> Quote:
    """
    Get a live quote for a single stock/index.
    ~15 min delayed for Indian markets.
    """
    yf = _get_yf()
    ticker = _to_yf_symbol(symbol, exchange)

    try:
        t = yf.Ticker(ticker)
        info = t.fast_info

        last_price = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
        prev_close = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
        open_price = float(info.get("open", 0) or 0)
        day_high = float(info.get("dayHigh", 0) or info.get("day_high", 0) or 0)
        day_low = float(info.get("dayLow", 0) or info.get("day_low", 0) or 0)
        volume = int(info.get("lastVolume", 0) or info.get("last_volume", 0) or 0)

        # If fast_info is sparse, try history for today
        if not last_price:
            hist = t.history(period="1d")
            if not hist.empty:
                row = hist.iloc[-1]
                last_price = float(row.get("Close", 0))
                open_price = float(row.get("Open", 0))
                day_high = float(row.get("High", 0))
                day_low = float(row.get("Low", 0))
                volume = int(row.get("Volume", 0))

        change = round(last_price - prev_close, 2) if prev_close else 0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        return Quote(
            symbol=symbol,
            last_price=last_price,
            open=open_price,
            high=day_high,
            low=day_low,
            close=prev_close,
            volume=volume,
            change=change,
            change_pct=change_pct,
        )
    except Exception as e:
        raise RuntimeError(f"yfinance quote failed for {symbol}: {e}") from e


def yf_get_quotes(instruments: list[str]) -> dict[str, Quote]:
    """
    Get quotes for multiple instruments. Per-symbol isolation:
    one failing ticker doesn't drop the entire batch.
    instruments: list of "EXCHANGE:SYMBOL" strings.
    """
    result = {}
    for inst in instruments:
        if ":" in inst:
            exchange, symbol = inst.split(":", 1)
        else:
            exchange, symbol = "NSE", inst

        if symbol.endswith("-EQ"):
            symbol = symbol[:-3]

        try:
            quote = yf_get_quote(symbol, exchange)
            result[inst] = quote
        except Exception:
            pass  # skip failed symbol, return partial results

    return result


def yf_get_ltp(symbol: str, exchange: str = "NSE") -> float:
    """Get last traded price for a single symbol."""
    q = yf_get_quote(symbol, exchange)
    return q.last_price


# ── Historical OHLCV ─────────────────────────────────────────


def yf_get_ohlcv(
    symbol: str,
    exchange: str = "NSE",
    interval: str = "1d",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    period: str = "1y",
) -> list[dict]:
    """
    Fetch historical OHLCV data from Yahoo Finance.

    Args:
        symbol:    NSE symbol (e.g. "RELIANCE")
        exchange:  "NSE" or "BSE"
        interval:  "1d", "1wk", "1mo", "5m", "15m", "1h"
        from_date: Start date (if provided, period is ignored)
        to_date:   End date (default: now)
        period:    yfinance period string: "1d","5d","1mo","3mo","6mo","1y","2y","5y","max"

    Returns:
        List of dicts with keys: date, open, high, low, close, volume
    """
    yf = _get_yf()
    ticker = _to_yf_symbol(symbol, exchange)

    # Map our interval names to yfinance format
    interval_map = {
        "day": "1d",
        "1d": "1d",
        "week": "1wk",
        "1wk": "1wk",
        "month": "1mo",
        "1mo": "1mo",
        "minute": "1m",
        "1m": "1m",
        "5minute": "5m",
        "5m": "5m",
        "15minute": "15m",
        "15m": "15m",
        "30minute": "30m",
        "30m": "30m",
        "60minute": "1h",
        "1h": "1h",
        "ONE_DAY": "1d",
    }
    yf_interval = interval_map.get(interval, interval)

    try:
        t = yf.Ticker(ticker)

        if from_date:
            hist = t.history(
                start=from_date.strftime("%Y-%m-%d"),
                end=(to_date or datetime.now()).strftime("%Y-%m-%d"),
                interval=yf_interval,
            )
        else:
            hist = t.history(period=period, interval=yf_interval)

        if hist.empty:
            return []

        rows = []
        for idx, row in hist.iterrows():
            rows.append(
                {
                    "date": idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        return rows
    except Exception:
        return []


# ── Convenience ──────────────────────────────────────────────


def yf_available() -> bool:
    """Check if yfinance is installed."""
    try:
        import yfinance  # noqa: F401

        return True
    except ImportError:
        return False
