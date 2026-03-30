"""
market/quotes.py
────────────────
Live market quotes — tries the active broker first, falls back to
Yahoo Finance (yfinance) for free ~15 min delayed data when no broker
is logged in or the broker call fails.
"""

from __future__ import annotations

from brokers.base    import Quote
from brokers.session import get_broker


def _yf_fallback_quotes(instruments: list[str]) -> dict[str, Quote]:
    """Try yfinance when broker is unavailable."""
    try:
        from market.yfinance_provider import yf_get_quotes, yf_available
        if yf_available():
            return yf_get_quotes(instruments)
    except Exception:
        pass
    return {}


def get_quote(instruments: list[str]) -> dict[str, Quote]:
    """
    Live quotes for one or more instruments.

    Args:
        instruments: List of "EXCHANGE:SYMBOL" strings.
                     e.g. ["NSE:RELIANCE", "NSE:NIFTY 50", "NFO:NIFTY24APR22900CE"]

    Returns:
        Dict keyed by instrument string → Quote dataclass.
    """
    try:
        return get_broker().get_quote(instruments)
    except (RuntimeError, Exception):
        return _yf_fallback_quotes(instruments)


def get_ltp(instrument: str) -> float:
    """
    Last traded price for a single instrument.

    Args:
        instrument: "EXCHANGE:SYMBOL"  e.g. "NSE:INFY"

    Returns:
        Last traded price as float.
    """
    try:
        return get_broker().get_ltp(instrument)
    except (RuntimeError, Exception):
        quotes = _yf_fallback_quotes([instrument])
        if instrument in quotes:
            return quotes[instrument].last_price
        return 0.0


def get_ltp_many(instruments: list[str]) -> dict[str, float]:
    """
    Last traded prices for multiple instruments in one call.

    Returns:
        Dict of instrument → ltp float.
    """
    quotes = get_quote(instruments)
    return {sym: q.last_price for sym, q in quotes.items()}


def get_ohlc(instrument: str) -> dict:
    """
    Today's OHLC + volume for a single instrument.

    Returns:
        Dict with keys: open, high, low, close, last_price, volume
    """
    quotes = get_quote([instrument])
    q = quotes.get(instrument)
    if not q:
        return {"open": 0, "high": 0, "low": 0, "close": 0,
                "last_price": 0, "volume": 0, "change": 0, "change_pct": 0}
    return {
        "open":       q.open,
        "high":       q.high,
        "low":        q.low,
        "close":      q.close,
        "last_price": q.last_price,
        "volume":     q.volume,
        "change":     q.change,
        "change_pct": q.change_pct,
    }
