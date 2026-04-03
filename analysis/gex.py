"""
analysis/gex.py
───────────────
Gamma Exposure (GEX) analysis.

Positive GEX = dealers long gamma → they sell rallies, buy dips → PINNING.
Negative GEX = dealers short gamma → they amplify moves → BREAKOUT.
GEX Flip Point = strike where dealer gamma transitions positive → negative.

Formula per strike:
  GEX_CE = OI × gamma × spot × lot_size × 100
  GEX_PE = OI × gamma × spot × lot_size × 100 × (-1)

Convention: dealers are assumed net short options (retail buys, dealers sell).

Usage:
    gex NIFTY
    gex BANKNIFTY
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel

console = Console()


# ── Core GEX Computation ─────────────────────────────────────


def compute_gex_at_strike(
    oi: int,
    gamma: float,
    spot: float,
    lot_size: int,
    is_call: bool,
) -> float:
    """
    Compute dealer GEX at a single strike.

    Calls contribute positive GEX (dealers are short calls → long gamma when hedging).
    Puts contribute negative GEX (dealers are short puts → short gamma when hedging).
    """
    gex = oi * gamma * spot * lot_size * 100
    return gex if is_call else -gex


def find_gex_flip(gex_by_strike: list[tuple[float, float]]) -> Optional[float]:
    """
    Find the GEX flip point — strike where net GEX transitions from positive to negative.

    Args:
        gex_by_strike: sorted list of (strike, net_gex) tuples.

    Returns:
        Flip strike, or None if no transition found.
    """
    for i in range(1, len(gex_by_strike)):
        prev_gex = gex_by_strike[i - 1][1]
        curr_gex = gex_by_strike[i][1]
        if prev_gex > 0 and curr_gex <= 0:
            # Interpolate
            prev_strike = gex_by_strike[i - 1][0]
            curr_strike = gex_by_strike[i][0]
            if prev_gex != curr_gex:
                ratio = prev_gex / (prev_gex - curr_gex)
                return prev_strike + ratio * (curr_strike - prev_strike)
            return curr_strike
    return None


def classify_gex_regime(total_gex: float, threshold: float = 50) -> str:
    """Classify market regime based on total net GEX."""
    if total_gex > threshold:
        return "POSITIVE"  # Mean-reverting / pinning
    elif total_gex < -threshold:
        return "NEGATIVE"  # Trending / breakout
    return "NEUTRAL"


# ── Full GEX Analysis ────────────────────────────────────────


def get_gex_analysis(underlying: str, expiry: Optional[str] = None) -> dict:
    """
    Compute full GEX analysis for an underlying.

    Returns dict with: per-strike GEX, total net GEX, flip point, regime.
    """
    try:
        from market.options import get_options_chain
        from market.quotes import get_ltp
        from analysis.options import compute_greeks

        chain = get_options_chain(underlying, expiry)
        if not chain:
            return {"error": "No options chain data available"}

        spot = get_ltp(f"NSE:{underlying}")
        if spot <= 0:
            return {"error": "Could not get spot price"}

        lot_size = chain[0].lot_size if chain else 25

        # Compute GEX at each strike
        strikes_gex = {}
        for c in chain:
            s = c.strike
            if s not in strikes_gex:
                strikes_gex[s] = {"strike": s, "ce_gex": 0, "pe_gex": 0, "net_gex": 0}

            if c.oi <= 0 or c.last_price <= 0:
                continue

            try:
                exp_str = c.expiry if c.expiry else expiry or ""
                if not exp_str:
                    continue
                greeks = compute_greeks(spot, s, exp_str, c.option_type, c.last_price)
                gamma = greeks.gamma

                gex = compute_gex_at_strike(c.oi, gamma, spot, lot_size, c.option_type == "CE")

                if c.option_type == "CE":
                    strikes_gex[s]["ce_gex"] = round(gex, 2)
                else:
                    strikes_gex[s]["pe_gex"] = round(gex, 2)
            except Exception:
                continue

        # Compute net GEX per strike
        for s in strikes_gex.values():
            s["net_gex"] = round(s["ce_gex"] + s["pe_gex"], 2)

        sorted_strikes = sorted(strikes_gex.values(), key=lambda x: x["strike"])
        total_gex = sum(s["net_gex"] for s in sorted_strikes)

        # Find flip point
        gex_tuples = [(s["strike"], s["net_gex"]) for s in sorted_strikes]
        flip = find_gex_flip(gex_tuples)

        regime = classify_gex_regime(total_gex)

        # Find max GEX strike
        max_gex_strike = (
            max(sorted_strikes, key=lambda x: abs(x["net_gex"]))["strike"] if sorted_strikes else 0
        )

        return {
            "underlying": underlying,
            "spot": spot,
            "strikes": sorted_strikes,
            "total_net_gex": round(total_gex, 2),
            "flip_point": round(flip, 0) if flip else None,
            "regime": regime,
            "max_gex_strike": max_gex_strike,
            "interpretation": _interpret_gex(regime, flip, spot),
        }
    except Exception as e:
        return {"error": str(e)}


def _interpret_gex(regime: str, flip: Optional[float], spot: float) -> str:
    if regime == "POSITIVE":
        msg = "Dealers sell rallies, buy dips — expect RANGE-BOUND / PINNING."
        if flip:
            msg += f" Breakout risk above {flip:,.0f}."
        return msg
    elif regime == "NEGATIVE":
        msg = "Dealers amplify moves — expect TRENDING / BREAKOUT."
        if flip:
            msg += f" Stabilizes below {flip:,.0f}."
        return msg
    return "Gamma exposure is balanced — no strong directional bias from dealers."


def print_gex(underlying: str, expiry: Optional[str] = None) -> None:
    """Display GEX analysis."""
    data = get_gex_analysis(underlying, expiry)
    if "error" in data:
        console.print(f"[red]{data['error']}[/red]")
        return

    lines = [
        f"  Spot: ₹{data['spot']:,.0f}",
        f"  Total Net GEX: {data['total_net_gex']:,.0f}",
        f"  Regime: [bold]{data['regime']}[/bold]",
    ]
    if data.get("flip_point"):
        lines.append(f"  GEX Flip Point: {data['flip_point']:,.0f}")
    lines.append(f"  Max GEX Strike: {data['max_gex_strike']:,.0f}")
    lines.append(f"\n  {data['interpretation']}")

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]GEX Analysis — {underlying}[/bold cyan]",
            border_style="cyan",
        )
    )
