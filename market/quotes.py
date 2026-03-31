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


def _ws_quotes(instruments: list[str]) -> dict[str, Quote]:
    """Try WebSocket cache first (instant, no API call)."""
    try:
        from market.websocket import ws_manager
        if not ws_manager.connected:
            return {}

        result = {}
        missing = []
        for inst in instruments:
            tick = ws_manager.get_tick(inst)
            if tick and tick.ltp > 0:
                result[inst] = Quote(
                    symbol=tick.symbol.split(":")[-1].split("-")[0] if ":" in tick.symbol else tick.symbol,
                    last_price=tick.ltp,
                    open=tick.open,
                    high=tick.high,
                    low=tick.low,
                    close=tick.close,
                    volume=tick.volume,
                    change=tick.change,
                    change_pct=tick.change_pct,
                )
            else:
                missing.append(inst)

        # Subscribe to missing symbols for next time
        if missing:
            ws_manager.subscribe(missing)

        return result
    except Exception:
        return {}


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

    Priority: WebSocket cache (instant) → Broker REST API → yfinance fallback.

    Args:
        instruments: List of "EXCHANGE:SYMBOL" strings.
                     e.g. ["NSE:RELIANCE", "NSE:NIFTY 50", "NFO:NIFTY24APR22900CE"]

    Returns:
        Dict keyed by instrument string → Quote dataclass.
    """
    # 1. Try WebSocket cache (instant)
    result = _ws_quotes(instruments)
    missing = [i for i in instruments if i not in result]
    if not missing:
        return result

    # 2. Try broker REST API
    try:
        broker_quotes = get_broker().get_quote(missing)
        result.update(broker_quotes)
        missing = [i for i in instruments if i not in result]
    except (RuntimeError, Exception):
        pass

    # 3. yfinance fallback
    if missing:
        yf_quotes = _yf_fallback_quotes(missing)
        result.update(yf_quotes)

    return result


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
