"""
market/oi_profile.py
────────────────────
OI (Open Interest) profile analysis with futures overlay.

Shows OI buildup at each strike, identifies support/resistance walls,
and classifies futures OI changes (long buildup, short covering, etc.).

Usage:
    oi-profile NIFTY
    oi-profile BANKNIFTY
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


# ── OI Change Classification ────────────────────────────────

def classify_oi_change(price_up: bool, oi_up: bool) -> str:
    """Classify futures/options OI change using 4-quadrant model."""
    if price_up and oi_up:
        return "LONG_BUILDUP"      # Bullish — new longs entering
    elif price_up and not oi_up:
        return "SHORT_COVERING"    # Bullish but weak — shorts exiting
    elif not price_up and oi_up:
        return "SHORT_BUILDUP"     # Bearish — new shorts entering
    else:
        return "LONG_UNWINDING"    # Bearish but weak — longs exiting


def find_max_oi_strikes(chain_data: list[dict]) -> tuple[float, float]:
    """Find strikes with maximum call OI (resistance) and put OI (support)."""
    max_call_strike = 0
    max_call_oi = 0
    max_put_strike = 0
    max_put_oi = 0

    for row in chain_data:
        if row.get("ce_oi", 0) > max_call_oi:
            max_call_oi = row["ce_oi"]
            max_call_strike = row["strike"]
        if row.get("pe_oi", 0) > max_put_oi:
            max_put_oi = row["pe_oi"]
            max_put_strike = row["strike"]

    return max_call_strike, max_put_strike


def get_oi_profile(underlying: str, expiry: Optional[str] = None) -> dict:
    """
    Get full OI profile for an underlying.

    Returns dict with: chain (per-strike OI), max_call_oi_strike (resistance),
    max_put_oi_strike (support), pcr, spot.
    """
    try:
        from market.options import get_options_chain, get_pcr
        from market.quotes import get_ltp

        chain = get_options_chain(underlying, expiry)
        if not chain:
            return {"error": "No options chain data available"}

        spot = get_ltp(f"NSE:{underlying}")

        # Build per-strike OI data
        strikes = {}
        for c in chain:
            s = c.strike
            if s not in strikes:
                strikes[s] = {"strike": s, "ce_oi": 0, "pe_oi": 0, "ce_oi_chg": 0, "pe_oi_chg": 0}
            if c.option_type == "CE":
                strikes[s]["ce_oi"] = c.oi
                strikes[s]["ce_oi_chg"] = c.oi_change
            else:
                strikes[s]["pe_oi"] = c.oi
                strikes[s]["pe_oi_chg"] = c.oi_change

        chain_data = sorted(strikes.values(), key=lambda x: x["strike"])
        max_call, max_put = find_max_oi_strikes(chain_data)

        try:
            pcr = get_pcr(underlying, expiry)
        except Exception:
            pcr = 0.0

        return {
            "underlying": underlying,
            "spot": spot,
            "chain": chain_data,
            "max_call_oi_strike": max_call,
            "max_put_oi_strike": max_put,
            "pcr": pcr,
            "resistance": max_call,
            "support": max_put,
        }
    except Exception as e:
        return {"error": str(e)}


def print_oi_profile(underlying: str, expiry: Optional[str] = None) -> None:
    """Display OI profile as Rich table."""
    data = get_oi_profile(underlying, expiry)
    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    spot = data.get("spot", 0)
    table = Table(title=f"OI Profile — {underlying} | Spot: ₹{spot:,.0f}")
    table.add_column("Strike", justify="right", style="bold")
    table.add_column("CE OI", justify="right")
    table.add_column("CE Chg", justify="right")
    table.add_column("PE OI", justify="right")
    table.add_column("PE Chg", justify="right")
    table.add_column("Signal", width=12)

    for row in data.get("chain", []):
        strike = row["strike"]
        ce_oi = row["ce_oi"]
        pe_oi = row["pe_oi"]

        # Highlight ATM strike
        strike_style = "bold cyan" if abs(strike - spot) < 100 else ""

        signal = ""
        if ce_oi > pe_oi * 2:
            signal = "[red]Resistance[/red]"
        elif pe_oi > ce_oi * 2:
            signal = "[green]Support[/green]"

        table.add_row(
            f"[{strike_style}]{strike:,.0f}[/{strike_style}]" if strike_style else f"{strike:,.0f}",
            f"{ce_oi:,}" if ce_oi else "—",
            f"{row['ce_oi_chg']:+,}" if row['ce_oi_chg'] else "—",
            f"{pe_oi:,}" if pe_oi else "—",
            f"{row['pe_oi_chg']:+,}" if row['pe_oi_chg'] else "—",
            signal,
        )

    console.print(table)
    console.print(f"  Resistance: {data['max_call_oi_strike']:,.0f} | "
                  f"Support: {data['max_put_oi_strike']:,.0f} | "
                  f"PCR: {data.get('pcr', 0):.2f}")
