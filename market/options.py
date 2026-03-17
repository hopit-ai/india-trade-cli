"""
market/options.py
─────────────────
Options chain and expiry utilities — broker-agnostic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing   import Optional

import pandas as pd

from brokers.base    import OptionsContract
from brokers.session import get_broker


def get_options_chain(
    underlying: str,
    expiry:     Optional[str] = None,
) -> list[OptionsContract]:
    """
    Full options chain for an underlying index or stock.

    Args:
        underlying: e.g. "NIFTY", "BANKNIFTY", "RELIANCE"
        expiry:     "YYYY-MM-DD" — nearest expiry if None

    Returns:
        List of OptionsContract sorted by strike then type (CE/PE).
    """
    return get_broker().get_options_chain(underlying, expiry)


def get_expiries(underlying: str) -> list[str]:
    """
    All available expiry dates for an underlying (sorted ascending).
    Returns dates as "YYYY-MM-DD" strings.
    """
    chain = get_broker().get_options_chain(underlying)
    dates = sorted({c.expiry for c in chain})
    return dates


def chain_to_dataframe(contracts: list[OptionsContract]) -> pd.DataFrame:
    """
    Convert options chain list to a pivot-style DataFrame
    matching the standard market display format:

        Strike | CE LTP | CE OI | CE IV | PE LTP | PE OI | PE IV
    """
    if not contracts:
        return pd.DataFrame()

    rows: dict[float, dict] = {}
    for c in contracts:
        strike = c.strike
        if strike not in rows:
            rows[strike] = {"strike": strike}
        prefix = c.option_type          # "CE" or "PE"
        rows[strike][f"{prefix}_ltp"]    = c.last_price
        rows[strike][f"{prefix}_oi"]     = c.oi
        rows[strike][f"{prefix}_oi_chg"] = c.oi_change
        rows[strike][f"{prefix}_volume"] = c.volume
        rows[strike][f"{prefix}_iv"]     = c.iv or 0.0
        rows[strike][f"{prefix}_symbol"] = c.symbol

    df = pd.DataFrame(list(rows.values()))
    df = df.sort_values("strike").reset_index(drop=True)

    # Ensure all columns exist even if one side is missing
    for side in ("CE", "PE"):
        for col in ("ltp", "oi", "oi_chg", "volume", "iv"):
            full = f"{side}_{col}"
            if full not in df.columns:
                df[full] = 0.0

    col_order = [
        "strike",
        "CE_ltp", "CE_oi", "CE_oi_chg", "CE_volume", "CE_iv",
        "PE_ltp", "PE_oi", "PE_oi_chg", "PE_volume", "PE_iv",
    ]
    return df[[c for c in col_order if c in df.columns]]


def get_atm_strike(underlying: str, spot: float) -> float:
    """
    Return the at-the-money strike closest to spot price.
    """
    chain = get_broker().get_options_chain(underlying)
    strikes = sorted({c.strike for c in chain})
    if not strikes:
        return round(spot / 50) * 50    # fallback
    return min(strikes, key=lambda s: abs(s - spot))


def get_pcr(underlying: str, expiry: Optional[str] = None) -> float:
    """
    Put-Call Ratio by Open Interest for the given expiry.
    PCR > 1.2 → bearish sentiment; PCR < 0.8 → bullish.
    """
    chain = get_broker().get_options_chain(underlying, expiry)
    ce_oi = sum(c.oi for c in chain if c.option_type == "CE")
    pe_oi = sum(c.oi for c in chain if c.option_type == "PE")
    if ce_oi == 0:
        return 0.0
    return round(pe_oi / ce_oi, 3)


def get_max_pain(underlying: str, expiry: Optional[str] = None) -> float:
    """
    Max pain strike — the strike where total options losses for buyers
    are maximised (i.e. where writers profit most).

    Calculated by summing ITM losses across all strikes for CE + PE.
    """
    chain = get_broker().get_options_chain(underlying, expiry)
    strikes = sorted({c.strike for c in chain})
    if not strikes:
        return 0.0

    # Build quick lookup: strike → {CE: contract, PE: contract}
    lookup: dict[float, dict[str, OptionsContract]] = {}
    for c in chain:
        lookup.setdefault(c.strike, {})[c.option_type] = c

    pain: dict[float, float] = {}
    for test_strike in strikes:
        total_pain = 0.0
        for s, contracts in lookup.items():
            ce = contracts.get("CE")
            pe = contracts.get("PE")
            # CE holders lose if test_strike < s (their CE expires worthless)
            if ce and test_strike < s:
                total_pain += max(0, s - test_strike) * ce.oi
            # PE holders lose if test_strike > s
            if pe and test_strike > s:
                total_pain += max(0, test_strike - s) * pe.oi
        pain[test_strike] = total_pain

    return min(pain, key=pain.get)   # type: ignore[arg-type]
