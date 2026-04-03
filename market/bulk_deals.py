"""
market/bulk_deals.py
────────────────────
Bulk and block deal tracking from NSE.

Bulk deal: trade where quantity > 0.5% of listed shares.
Block deal: large trade in special 8:45-9:00 AM window.

Data sources (tried in order):
  1. NSE snapshot API  — /api/snapshot-capital-market-largedeal (today's deals)
  2. NSE historical API — /api/historical/bulk-deals (date range)
  3. NSE CSV archive   — archives.nseindia.com/content/equities/bulk.csv (fallback)

Usage:
    bulk-deals                # Recent bulk/block deals
    bulk-deals RELIANCE       # Filtered to symbol
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import httpx

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Deal:
    date:        str
    symbol:      str
    client:      str
    deal_type:   str      # "BUY" or "SELL"
    quantity:    int
    price:       float
    entity_type: str      # "FII", "MF", "DII", "PROMOTER", "OTHER"
    deal_class:  str      # "BLOCK" or "BULK"


# ── Entity classification ────────────────────────────────────

_FII_PATTERNS = [
    "GOLDMAN", "MORGAN STANLEY", "JPMORGAN", "CITIGROUP", "BARCLAYS",
    "CREDIT SUISSE", "UBS", "NOMURA", "HSBC", "DEUTSCHE", "BNP",
    "SOCIETE", "CLSA", "MACQUARIE", "VANGUARD", "BLACKROCK", "FIDELITY",
    "PTE LTD", "LLC", "FPI", "FII", "SINGAPORE", "MAURITIUS",
    "ABERDEEN", "TEMPLETON", "SCHRODERS",
]

_MF_PATTERNS = [
    "MUTUAL FUND", "ASSET MANAGEMENT", "AMC", "SBI MF", "HDFC MF",
    "ICICI PRUDENTIAL", "KOTAK MF", "AXIS MF", "NIPPON", "UTI",
    "SUNDARAM", "MOTILAL", "MIRAE", "DSP", "TATA MF", "PGIM",
    "EDELWEISS MF", "INVESCO",
]

_DII_PATTERNS = [
    "LIC", "LIFE INSURANCE", "GENERAL INSURANCE", "NEW INDIA ASSURANCE",
    "NATIONAL INSURANCE", "ORIENTAL INSURANCE", "UNITED INDIA",
    "EMPLOYEES PROVIDENT", "PROVIDENT FUND", "PENSION FUND",
]

_PROMOTER_PATTERNS = [
    "PROMOTER", "FOUNDER", "FAMILY TRUST", "FAMILY OFFICE",
]


def classify_entity(client_name: str) -> str:
    """Classify a deal participant by entity type."""
    upper = client_name.upper()

    for p in _FII_PATTERNS:
        if p in upper:
            return "FII"
    for p in _MF_PATTERNS:
        if p in upper:
            return "MF"
    for p in _DII_PATTERNS:
        if p in upper:
            return "DII"
    for p in _PROMOTER_PATTERNS:
        if p in upper:
            return "PROMOTER"

    return "OTHER"


# ── NSE session with proper browser fingerprint ──────────────

# NSE aggressively blocks non-browser requests. These headers mimic a
# real Chrome/Edge browser session to avoid 403/404 rejections.
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
    "Cache-Control": "max-age=0",
    "sec-ch-ua": '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _nse_session() -> httpx.Client:
    """Create an NSE-authenticated httpx session with proper cookie warmup.

    NSE requires:
      1. Full browser-like headers (sec-ch-ua, sec-fetch-* etc.)
      2. A pre-flight GET to nseindia.com to set session cookies
      3. Cookies forwarded on subsequent API calls
    """
    session = httpx.Client(follow_redirects=True, headers=_NSE_HEADERS)
    # Warm up cookies — NSE sets bm_sz, ak_bmsc, nsit, nseappid
    session.get("https://www.nseindia.com", timeout=8)
    return session


# ── Parse helpers ────────────────────────────────────────────

def _parse_deal_item(item: dict, deal_class: str) -> Deal:
    """Parse a single deal item from any NSE response format."""
    client = (
        item.get("clientName")
        or item.get("BD_CLIENT_NAME")
        or item.get("clientname")
        or ""
    )
    buy_sell = (
        item.get("buySell")
        or item.get("BD_BUY_SELL")
        or item.get("buysell")
        or ""
    )
    return Deal(
        date=item.get("dealDate", item.get("BD_DT_DATE", item.get("date", "")))[:12],
        symbol=item.get("symbol", item.get("BD_SYMBOL", "")),
        client=client,
        deal_type=buy_sell.strip().upper(),
        quantity=int(item.get("quantity", item.get("BD_QTY_TRD", 0)) or 0),
        price=float(item.get("tradedPrice", item.get("BD_TP_WATP", 0)) or 0),
        entity_type=classify_entity(client),
        deal_class=deal_class,
    )


# ── Block deals ──────────────────────────────────────────────

def get_block_deals() -> list[Deal]:
    """Fetch today's block deals from NSE."""
    try:
        session = _nse_session()

        # Try snapshot endpoint first (includes BLOCK_DEALS_DATA)
        r = session.get(
            "https://www.nseindia.com/api/snapshot-capital-market-largedeal",
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get("BLOCK_DEALS_DATA", [])
            if items:
                return [_parse_deal_item(it, "BLOCK") for it in items]

        # Fallback to dedicated block-deal endpoint
        r = session.get("https://www.nseindia.com/api/block-deal", timeout=8)
        if r.status_code != 200:
            return []

        data = r.json()
        items = data if isinstance(data, list) else data.get("data", [])
        return [_parse_deal_item(it, "BLOCK") for it in items]
    except Exception:
        return []


# ── Bulk deals ───────────────────────────────────────────────

def _bulk_via_snapshot(session: httpx.Client) -> list[Deal]:
    """Try the snapshot endpoint for today's bulk deals."""
    r = session.get(
        "https://www.nseindia.com/api/snapshot-capital-market-largedeal",
        timeout=10,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    items = data.get("BULK_DEALS_DATA", [])
    return [_parse_deal_item(it, "BULK") for it in items]


def _bulk_via_historical(
    session: httpx.Client, days: int, symbol: Optional[str]
) -> list[Deal]:
    """Try historical bulk-deals endpoints with date range.

    NSE migrated from /api/historical/bulk-deals to
    /api/historicalOR/bulk-block-short-deals in late 2025.
    Try the new endpoint first, fall back to the old one.
    """
    to_dt = date.today()
    from_dt = to_dt - timedelta(days=days)
    from_str = from_dt.strftime("%d-%m-%Y")
    to_str = to_dt.strftime("%d-%m-%Y")

    # New endpoint (2025+): /api/historicalOR/bulk-block-short-deals
    params_new = {
        "optionType": "bulk_deals",
        "from": from_str,
        "to": to_str,
    }
    r = session.get(
        "https://www.nseindia.com/api/historicalOR/bulk-block-short-deals",
        params=params_new,
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("data", [])
        if items:
            deals = [_parse_deal_item(it, "BULK") for it in items]
            if symbol:
                deals = [d for d in deals if d.symbol.upper() == symbol.upper()]
            return deals

    # Legacy endpoint fallback: /api/historical/bulk-deals
    params_old = {"from": from_str, "to": to_str}
    if symbol:
        params_old["symbol"] = symbol.upper()

    r = session.get(
        "https://www.nseindia.com/api/historical/bulk-deals",
        params=params_old,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    items = data if isinstance(data, list) else data.get("data", [])
    return [_parse_deal_item(it, "BULK") for it in items]


def _bulk_via_csv() -> list[Deal]:
    """Fallback: fetch bulk deals from NSE's CSV archive (no cookies needed)."""
    try:
        import pandas as pd

        url = "https://archives.nseindia.com/content/equities/bulk.csv"
        r = httpx.get(url, headers={"User-Agent": _NSE_HEADERS["User-Agent"]}, timeout=10)
        if r.status_code != 200:
            return []
        df = pd.read_csv(io.StringIO(r.text))
        deals = []
        for _, row in df.iterrows():
            client = str(row.get("Client Name", ""))
            buy_sell = str(row.get("Buy / Sell", "")).strip().upper()
            deals.append(Deal(
                date=str(row.get("Date", ""))[:12],
                symbol=str(row.get("Symbol", "")),
                client=client,
                deal_type=buy_sell,
                quantity=int(row.get("Quantity Traded", 0) or 0),
                price=float(row.get("Trade Price / Wght. Avg. Price", 0) or 0),
                entity_type=classify_entity(client),
                deal_class="BULK",
            ))
        return deals
    except Exception:
        return []


def get_bulk_deals(days: int = 5, symbol: Optional[str] = None) -> list[Deal]:
    """Fetch recent bulk deals from NSE, trying multiple sources.

    Strategy:
      1. Snapshot API (today's deals, most reliable)
      2. Historical API (date range, original endpoint)
      3. CSV archive (last resort, no auth needed)
    """
    try:
        session = _nse_session()
    except Exception:
        # If even the session warmup fails, jump to CSV
        deals = _bulk_via_csv()
        if symbol:
            deals = [d for d in deals if d.symbol.upper() == symbol.upper()]
        return deals

    # 1. Try snapshot (today's deals)
    deals = _bulk_via_snapshot(session)

    # 2. Try historical endpoint (wider date range)
    if not deals:
        deals = _bulk_via_historical(session, days, symbol)
        if deals:
            return deals  # historical already filtered by symbol via params

    # 3. CSV archive fallback
    if not deals:
        deals = _bulk_via_csv()

    if symbol:
        deals = [d for d in deals if d.symbol.upper() == symbol.upper()]
    return deals


# ── Display ──────────────────────────────────────────────────

def print_deals(symbol: Optional[str] = None, days: int = 5) -> None:
    """Display bulk and block deals."""
    block = get_block_deals()
    bulk = get_bulk_deals(days=days, symbol=symbol)

    if symbol:
        block = [d for d in block if d.symbol.upper() == symbol.upper()]

    all_deals = block + bulk
    if not all_deals:
        console.print("[dim]No bulk/block deals found.[/dim]")
        return

    table = Table(title=f"Bulk & Block Deals{f' — {symbol}' if symbol else ''}")
    table.add_column("Date", width=12, style="dim")
    table.add_column("Type", width=6)
    table.add_column("Symbol", style="cyan")
    table.add_column("Client", width=30)
    table.add_column("Action", width=6)
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Entity", width=8)

    for d in all_deals[:20]:
        action_color = "green" if d.deal_type == "BUY" else "red"
        entity_color = {"FII": "yellow", "MF": "cyan", "DII": "blue", "PROMOTER": "green"}.get(d.entity_type, "dim")
        table.add_row(
            d.date[:12],
            d.deal_class,
            d.symbol,
            d.client[:30],
            f"[{action_color}]{d.deal_type}[/{action_color}]",
            f"{d.quantity:,}",
            f"₹{d.price:,.1f}",
            f"[{entity_color}]{d.entity_type}[/{entity_color}]",
        )

    console.print(table)
