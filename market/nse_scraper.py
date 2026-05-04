"""
market/nse_scraper.py
─────────────────────
NSE public API scraper — options chain fallback when broker is unavailable.

Uses the NSE India website's JSON endpoints (no auth required):
  - Index options:  /api/option-chain-indices?symbol=NIFTY
  - Equity options: /api/option-chain-equities?symbol=RELIANCE

These endpoints require a cookie obtained by visiting the homepage first.
Returns data in the same OptionsContract schema used by the broker adapters.

Limitations:
  - Available during market hours only (NSE servers return empty outside hours)
  - Rate-limited by NSE — not for high-frequency polling
  - ~5-15 min delayed during peak load

Usage:
    from market.nse_scraper import nse_get_options_chain, nse_available

    chain = nse_get_options_chain("NIFTY")
    chain = nse_get_options_chain("RELIANCE", expiry="2026-05-29")
"""

from __future__ import annotations

from typing import Optional

from brokers.base import OptionsContract

_NSE_BASE = "https://www.nseindia.com"
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
}

_INDEX_UNDERLYINGS = {
    "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY",
    "NIFTYNXT50", "SENSEX", "BANKEX",
}

# Session is reused across calls (cookies persist)
_session = None


def _is_index_underlying(underlying: str) -> bool:
    """Return True if underlying is an index (uses index endpoint)."""
    return underlying.upper() in _INDEX_UNDERLYINGS


def _get_session():
    """Return a requests.Session with NSE cookies."""
    global _session
    import requests

    if _session is None:
        _session = requests.Session()
        _session.headers.update(_NSE_HEADERS)
        try:
            # Prime the session — NSE requires a cookie from the homepage
            _session.get(_NSE_BASE, timeout=5)
        except Exception:
            pass
    return _session


def _fetch_nse_chain(underlying: str, is_index: bool) -> dict:
    """
    Fetch raw NSE option chain JSON for the given underlying.

    Args:
        underlying: Symbol string e.g. "NIFTY", "RELIANCE"
        is_index:   True → index endpoint; False → equity endpoint

    Returns:
        Parsed JSON dict from NSE API.

    Raises:
        Exception on network error or non-200 response.
    """
    session = _get_session()
    sym = underlying.upper()

    if is_index:
        url = f"{_NSE_BASE}/api/option-chain-indices?symbol={sym}"
    else:
        url = f"{_NSE_BASE}/api/option-chain-equities?symbol={sym}"

    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _nse_expiry_to_iso(nse_date: str) -> str:
    """
    Convert NSE expiry format "29-May-2026" to ISO "2026-05-29".
    Returns original string on parse failure.
    """
    try:
        from datetime import datetime

        return datetime.strptime(nse_date, "%d-%b-%Y").strftime("%Y-%m-%d")
    except Exception:
        return nse_date


def _parse_chain(raw: dict, underlying: str, expiry_filter: Optional[str]) -> list[OptionsContract]:
    """
    Parse NSE API response into a list of OptionsContract objects.

    Args:
        raw:           Parsed JSON from NSE API.
        underlying:    Symbol (used to build contract symbol string).
        expiry_filter: ISO date string to filter by, or None for all expiries.
    """
    contracts = []
    records = raw.get("records", {})
    data = records.get("data", [])

    for row in data:
        strike = float(row.get("strikePrice", 0))
        nse_expiry = row.get("expiryDate", "")
        iso_expiry = _nse_expiry_to_iso(nse_expiry)

        # Filter by expiry if requested
        if expiry_filter and iso_expiry != expiry_filter:
            continue

        for opt_type in ("CE", "PE"):
            leg = row.get(opt_type)
            if not leg:
                continue

            last_price = float(leg.get("lastPrice", 0) or 0)
            oi = int(leg.get("openInterest", 0) or 0)
            oi_change = int(leg.get("changeinOpenInterest", 0) or 0)
            volume = int(leg.get("totalTradedVolume", 0) or 0)
            iv = float(leg.get("impliedVolatility", 0) or 0)

            # Build symbol string matching Fyers/Zerodha convention
            sym = f"{underlying.upper()}{int(strike)}{opt_type}"

            contracts.append(
                OptionsContract(
                    symbol=sym,
                    underlying=underlying.upper(),
                    strike=strike,
                    option_type=opt_type,
                    expiry=iso_expiry,
                    last_price=last_price,
                    oi=oi,
                    oi_change=oi_change,
                    volume=volume,
                    iv=iv,
                )
            )

    return sorted(contracts, key=lambda c: (c.strike, c.option_type))


def nse_get_options_chain(
    underlying: str, expiry: Optional[str] = None
) -> list[OptionsContract]:
    """
    Fetch options chain from NSE public API.

    Args:
        underlying: Symbol e.g. "NIFTY", "BANKNIFTY", "RELIANCE"
        expiry:     ISO date "YYYY-MM-DD" to filter; None = all expiries

    Returns:
        List of OptionsContract sorted by strike then type.
        Returns [] on any failure (network, parse, NSE down).
    """
    try:
        is_index = _is_index_underlying(underlying)
        raw = _fetch_nse_chain(underlying, is_index)
        return _parse_chain(raw, underlying, expiry)
    except Exception:
        return []


def nse_available() -> bool:
    """
    Check if NSE website is reachable.
    Returns False if network is down or NSE is unreachable.
    """
    try:
        import requests

        resp = requests.get(_NSE_BASE, timeout=3, headers=_NSE_HEADERS)
        return resp.status_code == 200
    except Exception:
        return False
