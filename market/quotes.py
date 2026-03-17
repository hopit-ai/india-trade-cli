"""
market/quotes.py
────────────────
Live market quotes — thin wrapper over the active broker session.
All functions are broker-agnostic; they call get_broker() internally.
"""

from __future__ import annotations

from brokers.base    import Quote
from brokers.session import get_broker


def get_quote(instruments: list[str]) -> dict[str, Quote]:
    """
    Live quotes for one or more instruments.

    Args:
        instruments: List of "EXCHANGE:SYMBOL" strings.
                     e.g. ["NSE:RELIANCE", "NSE:NIFTY 50", "NFO:NIFTY24APR22900CE"]

    Returns:
        Dict keyed by instrument string → Quote dataclass.
    """
    return get_broker().get_quote(instruments)


def get_ltp(instrument: str) -> float:
    """
    Last traded price for a single instrument.

    Args:
        instrument: "EXCHANGE:SYMBOL"  e.g. "NSE:INFY"

    Returns:
        Last traded price as float.
    """
    return get_broker().get_ltp(instrument)


def get_ltp_many(instruments: list[str]) -> dict[str, float]:
    """
    Last traded prices for multiple instruments in one call.

    Returns:
        Dict of instrument → ltp float.
    """
    quotes = get_broker().get_quote(instruments)
    return {sym: q.last_price for sym, q in quotes.items()}


def get_ohlc(instrument: str) -> dict:
    """
    Today's OHLC + volume for a single instrument.

    Returns:
        Dict with keys: open, high, low, close, last_price, volume
    """
    q = get_broker().get_quote([instrument])[instrument]
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
