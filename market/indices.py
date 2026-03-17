"""
market/indices.py
─────────────────
Indian market indices snapshot — NIFTY 50, BANKNIFTY, India VIX,
SENSEX, sector indices, and a market posture helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing      import Optional

from brokers.base    import Quote
from brokers.session import get_broker


# ── Key instruments ──────────────────────────────────────────

INDEX_INSTRUMENTS = {
    "NIFTY50":    "NSE:NIFTY 50",
    "BANKNIFTY":  "NSE:NIFTY BANK",
    "VIX":        "NSE:INDIA VIX",
    "SENSEX":     "BSE:SENSEX",
    "FINNIFTY":   "NSE:NIFTY FIN SERVICE",
    "MIDCAP":     "NSE:NIFTY MIDCAP 100",
    "IT":         "NSE:NIFTY IT",
    "PHARMA":     "NSE:NIFTY PHARMA",
    "AUTO":       "NSE:NIFTY AUTO",
    "FMCG":       "NSE:NIFTY FMCG",
    "REALTY":     "NSE:NIFTY REALTY",
    "METAL":      "NSE:NIFTY METAL",
    "ENERGY":     "NSE:NIFTY ENERGY",
}


@dataclass
class IndexSnapshot:
    name:       str
    instrument: str
    ltp:        float
    change:     float
    change_pct: float
    open:       float
    high:       float
    low:        float


@dataclass
class MarketSnapshot:
    nifty:     IndexSnapshot
    banknifty: IndexSnapshot
    vix:       IndexSnapshot
    sensex:    Optional[IndexSnapshot]
    posture:   str          # "BULLISH" | "BEARISH" | "NEUTRAL" | "VOLATILE"
    posture_reason: str


def get_index(name: str) -> IndexSnapshot:
    """
    Snapshot for a single named index.
    name: "NIFTY50" | "BANKNIFTY" | "VIX" | "SENSEX" | etc.
    """
    instrument = INDEX_INSTRUMENTS.get(name.upper())
    if not instrument:
        raise ValueError(f"Unknown index: {name}. Valid: {list(INDEX_INSTRUMENTS)}")

    quotes = get_broker().get_quote([instrument])
    q      = quotes[instrument]

    return IndexSnapshot(
        name       = name,
        instrument = instrument,
        ltp        = q.last_price,
        change     = q.change,
        change_pct = q.change_pct,
        open       = q.open,
        high       = q.high,
        low        = q.low,
    )


def get_market_snapshot() -> MarketSnapshot:
    """
    Full market pulse: NIFTY, BANKNIFTY, VIX, SENSEX + posture.
    Single batched quote call for efficiency.
    """
    instruments = [
        INDEX_INSTRUMENTS["NIFTY50"],
        INDEX_INSTRUMENTS["BANKNIFTY"],
        INDEX_INSTRUMENTS["VIX"],
        INDEX_INSTRUMENTS["SENSEX"],
    ]
    quotes = get_broker().get_quote(instruments)

    def snap(name: str) -> IndexSnapshot:
        inst = INDEX_INSTRUMENTS[name]
        q    = quotes.get(inst)
        if not q:
            return IndexSnapshot(name, inst, 0, 0, 0, 0, 0, 0)
        return IndexSnapshot(
            name       = name,
            instrument = inst,
            ltp        = q.last_price,
            change     = q.change,
            change_pct = q.change_pct,
            open       = q.open,
            high       = q.high,
            low        = q.low,
        )

    nifty     = snap("NIFTY50")
    banknifty = snap("BANKNIFTY")
    vix       = snap("VIX")
    sensex    = snap("SENSEX")

    posture, reason = _market_posture(nifty, vix)

    return MarketSnapshot(
        nifty          = nifty,
        banknifty      = banknifty,
        vix            = vix,
        sensex         = sensex,
        posture        = posture,
        posture_reason = reason,
    )


def _market_posture(nifty: IndexSnapshot, vix: IndexSnapshot) -> tuple[str, str]:
    """
    Simple rules-based market posture from NIFTY change + VIX level.

    VIX thresholds (India):
        < 12  : Very low — complacent, good for selling premium
        12-15 : Low — normal, balanced conditions
        15-20 : Elevated — cautious, prefer hedged strategies
        20-25 : High — fearful, avoid naked positions
        > 25  : Very high — crisis zone
    """
    vix_level = vix.ltp
    nifty_chg = nifty.change_pct

    if vix_level > 20:
        return "VOLATILE", f"VIX={vix_level:.1f} (danger zone >20). Hedge everything."

    if vix_level < 12:
        vix_note = f"VIX={vix_level:.1f} (very low — sell premium)"
    elif vix_level < 15:
        vix_note = f"VIX={vix_level:.1f} (normal)"
    else:
        vix_note = f"VIX={vix_level:.1f} (elevated — prefer spreads)"

    if nifty_chg > 0.5:
        return "BULLISH", f"NIFTY {nifty_chg:+.2f}%, {vix_note}"
    elif nifty_chg < -0.5:
        return "BEARISH", f"NIFTY {nifty_chg:+.2f}%, {vix_note}"
    else:
        return "NEUTRAL", f"NIFTY {nifty_chg:+.2f}% (range-bound), {vix_note}"


def get_vix() -> float:
    """Quick India VIX level."""
    q = get_broker().get_quote([INDEX_INSTRUMENTS["VIX"]])
    return q[INDEX_INSTRUMENTS["VIX"]].last_price


def get_sector_snapshot() -> list[IndexSnapshot]:
    """Return snapshots for all sector indices in one batched call."""
    sector_keys = ["IT", "PHARMA", "AUTO", "FMCG", "REALTY", "METAL", "ENERGY"]
    instruments = [INDEX_INSTRUMENTS[k] for k in sector_keys]
    quotes      = get_broker().get_quote(instruments)

    snaps = []
    for key in sector_keys:
        inst = INDEX_INSTRUMENTS[key]
        q    = quotes.get(inst)
        if q:
            snaps.append(IndexSnapshot(
                name=key, instrument=inst,
                ltp=q.last_price, change=q.change, change_pct=q.change_pct,
                open=q.open, high=q.high, low=q.low,
            ))
    return snaps
