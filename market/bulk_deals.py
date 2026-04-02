"""
market/bulk_deals.py
────────────────────
Bulk and block deal tracking from NSE.

Bulk deal: trade where quantity > 0.5% of listed shares.
Block deal: large trade in special 8:45-9:00 AM window.

Usage:
    bulk-deals                # Recent bulk/block deals
    bulk-deals RELIANCE       # Filtered to symbol
"""

from __future__ import annotations

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


# ── NSE API fetch ────────────────────────────────────────────

def _nse_session() -> httpx.Client:
    """Create an NSE-authenticated httpx session."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com",
    }
    session = httpx.Client(follow_redirects=True, headers=headers)
    session.get("https://www.nseindia.com", timeout=5)
    return session


def get_block_deals() -> list[Deal]:
    """Fetch today's block deals from NSE."""
    try:
        session = _nse_session()
        r = session.get("https://www.nseindia.com/api/block-deal", timeout=8)
        if r.status_code != 200:
            return []

        data = r.json()
        deals = []
        for item in (data if isinstance(data, list) else data.get("data", [])):
            deals.append(Deal(
                date=item.get("dealDate", item.get("BD_DT_DATE", "")),
                symbol=item.get("symbol", item.get("BD_SYMBOL", "")),
                client=item.get("clientName", item.get("BD_CLIENT_NAME", "")),
                deal_type=item.get("buySell", item.get("BD_BUY_SELL", "")).upper(),
                quantity=int(item.get("quantity", item.get("BD_QTY_TRD", 0))),
                price=float(item.get("tradedPrice", item.get("BD_TP_WATP", 0))),
                entity_type=classify_entity(item.get("clientName", item.get("BD_CLIENT_NAME", ""))),
                deal_class="BLOCK",
            ))
        return deals
    except Exception:
        return []


def get_bulk_deals(days: int = 5, symbol: Optional[str] = None) -> list[Deal]:
    """Fetch recent bulk deals from NSE."""
    try:
        session = _nse_session()
        to_dt = date.today()
        from_dt = to_dt - timedelta(days=days)
        params = {
            "from": from_dt.strftime("%d-%m-%Y"),
            "to": to_dt.strftime("%d-%m-%Y"),
        }
        if symbol:
            params["symbol"] = symbol.upper()

        r = session.get("https://www.nseindia.com/api/historical/bulk-deals",
                        params=params, timeout=10)
        if r.status_code != 200:
            return []

        data = r.json()
        deals = []
        for item in (data if isinstance(data, list) else data.get("data", [])):
            deals.append(Deal(
                date=item.get("dealDate", item.get("BD_DT_DATE", "")),
                symbol=item.get("symbol", item.get("BD_SYMBOL", "")),
                client=item.get("clientName", item.get("BD_CLIENT_NAME", "")),
                deal_type=item.get("buySell", item.get("BD_BUY_SELL", "")).upper(),
                quantity=int(item.get("quantity", item.get("BD_QTY_TRD", 0))),
                price=float(item.get("tradedPrice", item.get("BD_TP_WATP", 0))),
                entity_type=classify_entity(item.get("clientName", item.get("BD_CLIENT_NAME", ""))),
                deal_class="BULK",
            ))
        return deals
    except Exception:
        return []


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
        value_cr = d.quantity * d.price / 1e7
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
