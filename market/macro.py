"""
market/macro.py
───────────────
Currency and commodity linkage analysis for Indian markets.

Tracks:
  - USD/INR impact on IT exports, gold imports
  - Oil prices impact on aviation, paint, cement
  - Gold prices impact on jewelry stocks
  - US 10Y yield impact on FII flows

Uses yfinance for free macro data (forex, commodities).

Usage:
    from market.macro import get_macro_snapshot, get_stock_macro_linkages
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class MacroSnapshot:
    """Current macro indicators relevant to Indian markets."""
    usdinr:         Optional[float] = None   # USD/INR rate
    usdinr_change:  Optional[float] = None   # % change
    crude_oil:      Optional[float] = None   # Brent crude USD/bbl
    crude_change:   Optional[float] = None
    gold:           Optional[float] = None   # Gold USD/oz
    gold_change:    Optional[float] = None
    us_10y:         Optional[float] = None   # US 10Y treasury yield %
    dxy:            Optional[float] = None   # Dollar index


# Stock → macro factor sensitivity mapping
_MACRO_LINKAGES = {
    # IT exporters: benefit from weak INR (revenue in USD, costs in INR)
    "INFY":       {"usdinr": +0.8, "crude_oil": 0, "gold": 0, "us_10y": -0.3},
    "TCS":        {"usdinr": +0.8, "crude_oil": 0, "gold": 0, "us_10y": -0.3},
    "WIPRO":      {"usdinr": +0.7, "crude_oil": 0, "gold": 0, "us_10y": -0.3},
    "HCLTECH":    {"usdinr": +0.7, "crude_oil": 0, "gold": 0, "us_10y": -0.3},
    "TECHM":      {"usdinr": +0.7, "crude_oil": 0, "gold": 0, "us_10y": -0.3},

    # Oil/energy: hurt by high crude (import costs)
    "RELIANCE":   {"usdinr": -0.3, "crude_oil": +0.5, "gold": 0, "us_10y": 0},
    "ONGC":       {"usdinr": -0.2, "crude_oil": +0.7, "gold": 0, "us_10y": 0},
    "IOC":        {"usdinr": -0.3, "crude_oil": -0.6, "gold": 0, "us_10y": 0},
    "BPCL":       {"usdinr": -0.3, "crude_oil": -0.6, "gold": 0, "us_10y": 0},

    # Aviation: hurt by crude (jet fuel), benefit from strong INR (dollar-denominated leases)
    "INDIGO":     {"usdinr": -0.6, "crude_oil": -0.8, "gold": 0, "us_10y": 0},

    # Banks: hurt by rising US yields (FII selling), benefit from rate cuts
    "HDFCBANK":   {"usdinr": +0.1, "crude_oil": 0, "gold": 0, "us_10y": -0.5},
    "ICICIBANK":  {"usdinr": +0.1, "crude_oil": 0, "gold": 0, "us_10y": -0.5},
    "SBIN":       {"usdinr": +0.1, "crude_oil": 0, "gold": 0, "us_10y": -0.4},
    "KOTAKBANK":  {"usdinr": +0.1, "crude_oil": 0, "gold": 0, "us_10y": -0.5},

    # Gold/jewelry: benefit from rising gold
    "TITAN":      {"usdinr": -0.2, "crude_oil": 0, "gold": +0.6, "us_10y": 0},
    "KALYANKJIL": {"usdinr": -0.2, "crude_oil": 0, "gold": +0.7, "us_10y": 0},

    # Cement/paint: hurt by crude (input costs)
    "ULTRACEMCO": {"usdinr": -0.2, "crude_oil": -0.4, "gold": 0, "us_10y": 0},
    "ASIANPAINT": {"usdinr": -0.3, "crude_oil": -0.5, "gold": 0, "us_10y": 0},

    # Pharma: benefit from weak INR (exports), less sensitive to crude
    "SUNPHARMA":  {"usdinr": +0.5, "crude_oil": -0.1, "gold": 0, "us_10y": -0.2},
    "DRREDDY":    {"usdinr": +0.6, "crude_oil": -0.1, "gold": 0, "us_10y": -0.2},

    # Auto: hurt by crude (steel prices, logistics)
    "TATAMOTORS": {"usdinr": -0.3, "crude_oil": -0.3, "gold": 0, "us_10y": -0.2},
    "MARUTI":     {"usdinr": -0.2, "crude_oil": -0.2, "gold": 0, "us_10y": 0},
    "M&M":        {"usdinr": -0.2, "crude_oil": -0.2, "gold": 0, "us_10y": 0},

    # Metals: benefit from weak INR (exporters), commodity-linked
    "TATASTEEL":  {"usdinr": +0.3, "crude_oil": +0.2, "gold": +0.3, "us_10y": 0},
    "HINDALCO":   {"usdinr": +0.4, "crude_oil": +0.2, "gold": +0.2, "us_10y": 0},
    "JSWSTEEL":   {"usdinr": +0.3, "crude_oil": +0.2, "gold": +0.2, "us_10y": 0},
}


def get_macro_snapshot() -> MacroSnapshot:
    """Fetch current macro indicators via yfinance."""
    try:
        from market.yfinance_provider import _get_yf

        snap = MacroSnapshot()

        # USD/INR
        try:
            yf = _get_yf()
            t = yf.Ticker("INR=X")
            info = t.fast_info
            snap.usdinr = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
            prev = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
            if snap.usdinr and prev:
                snap.usdinr_change = round((snap.usdinr - prev) / prev * 100, 2)
        except Exception:
            pass

        # Brent Crude
        try:
            t = yf.Ticker("BZ=F")
            info = t.fast_info
            snap.crude_oil = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
            prev = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
            if snap.crude_oil and prev:
                snap.crude_change = round((snap.crude_oil - prev) / prev * 100, 2)
        except Exception:
            pass

        # Gold
        try:
            t = yf.Ticker("GC=F")
            info = t.fast_info
            snap.gold = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
            prev = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
            if snap.gold and prev:
                snap.gold_change = round((snap.gold - prev) / prev * 100, 2)
        except Exception:
            pass

        # US 10Y
        try:
            t = yf.Ticker("^TNX")
            info = t.fast_info
            snap.us_10y = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
        except Exception:
            pass

        # DXY
        try:
            t = yf.Ticker("DX-Y.NYB")
            info = t.fast_info
            snap.dxy = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
        except Exception:
            pass

        return snap
    except Exception:
        return MacroSnapshot()


def get_stock_macro_linkages(symbol: str) -> dict:
    """
    Get macro factor sensitivities for a stock and current macro state.

    Returns:
    - Sensitivity scores per factor (-1 to +1)
    - Current macro values
    - Impact assessment (tailwind/headwind/neutral per factor)
    """
    symbol = symbol.upper()
    linkages = _MACRO_LINKAGES.get(symbol, {})
    if not linkages:
        return {"symbol": symbol, "linkages": {}, "message": f"No macro linkage data for {symbol}"}

    snap = get_macro_snapshot()
    impacts = []

    for factor, sensitivity in linkages.items():
        if abs(sensitivity) < 0.1:
            continue

        current_val = None
        change = None
        label = factor

        if factor == "usdinr":
            current_val = snap.usdinr
            change = snap.usdinr_change
            label = "USD/INR"
        elif factor == "crude_oil":
            current_val = snap.crude_oil
            change = snap.crude_change
            label = "Crude Oil"
        elif factor == "gold":
            current_val = snap.gold
            change = snap.gold_change
            label = "Gold"
        elif factor == "us_10y":
            current_val = snap.us_10y
            label = "US 10Y Yield"

        if change is not None:
            # Positive sensitivity + positive change = tailwind
            # Negative sensitivity + positive change = headwind
            impact_score = sensitivity * (change / 100) if change else 0
            if impact_score > 0.001:
                impact = "TAILWIND"
            elif impact_score < -0.001:
                impact = "HEADWIND"
            else:
                impact = "NEUTRAL"
        else:
            impact = "N/A"

        impacts.append({
            "factor": label,
            "sensitivity": sensitivity,
            "current_value": current_val,
            "day_change_pct": change,
            "impact": impact,
        })

    return {
        "symbol": symbol,
        "linkages": impacts,
        "summary": _summarize_macro_impact(impacts),
    }


def _summarize_macro_impact(impacts: list[dict]) -> str:
    """One-line summary of macro headwinds/tailwinds."""
    tailwinds = [i["factor"] for i in impacts if i["impact"] == "TAILWIND"]
    headwinds = [i["factor"] for i in impacts if i["impact"] == "HEADWIND"]

    parts = []
    if tailwinds:
        parts.append(f"Tailwinds: {', '.join(tailwinds)}")
    if headwinds:
        parts.append(f"Headwinds: {', '.join(headwinds)}")
    if not parts:
        return "No significant macro impact today."
    return " | ".join(parts)


def get_macro_context(symbol: Optional[str] = None) -> str:
    """Generate macro context text for LLM prompts."""
    snap = get_macro_snapshot()
    parts = ["Macro snapshot:"]
    if snap.usdinr:
        parts.append(f"  USD/INR: {snap.usdinr:.2f} ({snap.usdinr_change:+.2f}%)" if snap.usdinr_change else f"  USD/INR: {snap.usdinr:.2f}")
    if snap.crude_oil:
        parts.append(f"  Crude: ${snap.crude_oil:.1f}/bbl ({snap.crude_change:+.1f}%)" if snap.crude_change else f"  Crude: ${snap.crude_oil:.1f}/bbl")
    if snap.gold:
        parts.append(f"  Gold: ${snap.gold:.0f}/oz ({snap.gold_change:+.1f}%)" if snap.gold_change else f"  Gold: ${snap.gold:.0f}/oz")
    if snap.us_10y:
        parts.append(f"  US 10Y: {snap.us_10y:.2f}%")

    if symbol:
        linkages = get_stock_macro_linkages(symbol)
        if linkages.get("summary"):
            parts.append(f"  {symbol}: {linkages['summary']}")

    return "\n".join(parts)


def print_macro_snapshot(symbol: Optional[str] = None) -> None:
    """Display macro data as Rich table."""
    snap = get_macro_snapshot()

    table = Table(title="Macro Indicators", show_lines=False)
    table.add_column("Indicator", style="bold", width=14)
    table.add_column("Value", justify="right", width=12)
    table.add_column("Change", justify="right", width=10)

    def _row(name, val, chg):
        if val is None:
            return
        chg_str = f"{chg:+.2f}%" if chg is not None else "-"
        chg_style = "green" if (chg or 0) >= 0 else "red"
        table.add_row(name, f"{val:.2f}", f"[{chg_style}]{chg_str}[/{chg_style}]")

    _row("USD/INR", snap.usdinr, snap.usdinr_change)
    _row("Crude Oil", snap.crude_oil, snap.crude_change)
    _row("Gold", snap.gold, snap.gold_change)
    if snap.us_10y:
        table.add_row("US 10Y Yield", f"{snap.us_10y:.2f}%", "-")
    if snap.dxy:
        table.add_row("Dollar Index", f"{snap.dxy:.1f}", "-")

    console.print(table)

    if symbol:
        linkages = get_stock_macro_linkages(symbol)
        if linkages.get("linkages"):
            t2 = Table(title=f"Macro Impact on {symbol}", show_lines=False)
            t2.add_column("Factor", width=14)
            t2.add_column("Sensitivity", justify="right", width=12)
            t2.add_column("Impact", width=12)

            for l in linkages["linkages"]:
                imp_style = {"TAILWIND": "green", "HEADWIND": "red"}.get(l["impact"], "yellow")
                sens = l["sensitivity"]
                sens_str = f"{'+'if sens>0 else ''}{sens:.1f}"
                t2.add_row(l["factor"], sens_str, f"[{imp_style}]{l['impact']}[/{imp_style}]")
            console.print(t2)
