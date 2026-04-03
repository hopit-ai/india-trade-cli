"""
market/active_stocks.py
───────────────────────
NSE Most Active Stocks — proxy for retail/institutional interest.

A stock appearing in most-active with unusual volume is a signal
worth feeding into sentiment analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class ActiveStock:
    symbol: str
    volume: int
    value_cr: float  # traded value in crores
    ltp: float
    change_pct: float


def get_most_active(by: str = "volume", limit: int = 20) -> list[ActiveStock]:
    """
    Fetch most active stocks from NSE.

    Args:
        by: "volume" or "value"
        limit: max results

    Returns:
        List of ActiveStock, sorted by activity. Empty list on failure.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)

        url = f"https://www.nseindia.com/api/live-analysis-most-active-securities?index={by}"
        r = session.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get("data", [])[:limit]:
            try:
                # NSE uses totalTradedValue (in rupees) and lastPrice
                traded_val = float(
                    item.get("totalTradedValue", 0) or item.get("turnoverInLakhs", 0) or 0
                )
                value_cr = (
                    round(traded_val / 1e7, 1) if traded_val > 1e6 else round(traded_val / 100, 1)
                )
                results.append(
                    ActiveStock(
                        symbol=item.get("symbol", ""),
                        volume=int(
                            item.get("quantityTraded", 0) or item.get("totalTradedVolume", 0) or 0
                        ),
                        value_cr=value_cr,
                        ltp=float(item.get("lastPrice", 0) or item.get("ltp", 0) or 0),
                        change_pct=float(item.get("pChange", 0)),
                    )
                )
            except (ValueError, TypeError):
                continue
        return results

    except Exception:
        return []


def print_most_active(by: str = "volume", limit: int = 15) -> None:
    """Display most active stocks as a Rich table."""
    stocks = get_most_active(by=by, limit=limit)
    if not stocks:
        console.print("[dim]Could not fetch most active stocks from NSE.[/dim]")
        return

    table = Table(title=f"Most Active Stocks (by {by})")
    table.add_column("Symbol", style="cyan bold")
    table.add_column("LTP", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Value (Cr)", justify="right")

    for s in stocks:
        chg_style = "green" if s.change_pct >= 0 else "red"
        table.add_row(
            s.symbol,
            f"₹{s.ltp:,.2f}" if s.ltp else "—",
            f"[{chg_style}]{s.change_pct:+.1f}%[/{chg_style}]",
            f"{s.volume:,}",
            f"₹{s.value_cr:,.0f}",
        )

    console.print(table)
