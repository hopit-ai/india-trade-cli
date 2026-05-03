"""
engine/risk_gate.py
───────────────────
Deterministic risk gate — runs BEFORE any LLM call.

Pre-computes what actions are ALLOWED for a symbol and returns structured
constraints that get injected into the LLM synthesis prompt as hard limits.

Never calls the LLM. Pure deterministic rules, safe to call at any time.

Usage:
    from engine.risk_gate import compute_allowed_actions

    allowed = compute_allowed_actions("INFY", "NSE")
    if not allowed.allowed:
        # blocked — skip LLM, return a message
        ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass
class AllowedAction:
    """
    Pre-computed constraints for a symbol, produced by compute_allowed_actions().

    Passed to the LLM synthesis prompt as non-negotiable hard limits.
    """

    symbol: str
    allowed: bool  # False = blocked entirely
    direction: Literal["BUY_ONLY", "SELL_ONLY", "BOTH", "NONE"]
    max_qty: int  # max shares allowed (0 if blocked)
    max_capital: float  # max INR value (0 if blocked)
    flags: list[str]  # e.g. ["EARNINGS_PROXIMITY", "HIGH_VOLATILITY", "LOW_CASH"]
    block_reason: str = ""  # non-empty if allowed=False
    warnings: list[str] = field(default_factory=list)  # non-blocking warnings


# ── Internal helpers ──────────────────────────────────────────


def _get_risk_limits():
    """Return the global risk_limits singleton. Overridable in tests."""
    from engine.risk_limits import risk_limits

    return risk_limits


def _get_capital(capital: float | None) -> float:
    """Resolve total capital: use supplied value or fall back to env."""
    if capital is not None:
        return float(capital)
    return float(os.environ.get("TOTAL_CAPITAL", "200000"))


def _get_price(symbol: str, prices: dict | None) -> float | None:
    """Look up price from supplied prices dict (case-insensitive)."""
    if not prices:
        return None
    upper = symbol.upper()
    return prices.get(upper) or prices.get(symbol)


def _get_existing_position_value(
    symbol: str,
    portfolio: dict | None,
) -> float:
    """
    Return the current market value of an existing position for this symbol.

    portfolio: {symbol: {qty, avg_price, current_price}}
    """
    if not portfolio:
        return 0.0
    upper = symbol.upper()
    pos = portfolio.get(upper) or portfolio.get(symbol)
    if not pos:
        return 0.0
    qty = float(pos.get("qty", 0))
    price = float(pos.get("current_price") or pos.get("avg_price", 0))
    return qty * price


def _days_until_event(symbol: str, upcoming_events: dict | None) -> int | None:
    """
    Return the number of calendar days until the next earnings event for this symbol.

    upcoming_events: {symbol: "YYYY-MM-DD"}
    Returns None if no event is known.
    """
    if not upcoming_events:
        return None
    upper = symbol.upper()
    event_str = upcoming_events.get(upper) or upcoming_events.get(symbol)
    if not event_str:
        return None
    try:
        event_date = date.fromisoformat(str(event_str))
        delta = (event_date - date.today()).days
        return max(delta, 0)
    except (ValueError, TypeError):
        return None


# ── Core function ─────────────────────────────────────────────


def compute_allowed_actions(
    symbol: str,
    exchange: str = "NSE",
    portfolio: dict | None = None,  # {symbol: {qty, avg_price, current_price}}
    capital: float | None = None,  # total capital (reads from env if None)
    prices: dict | None = None,  # {symbol: current_price}
    upcoming_events: dict | None = None,  # {symbol: "YYYY-MM-DD"} earnings dates
    vix: float | None = None,  # India VIX value (None = skip VIX check)
) -> AllowedAction:
    """
    Compute what actions are allowed for this symbol before LLM sees it.

    Checks (in order):
    1. risk_limits.check() — daily loss cap, trade counts
    2. Earnings proximity — within 3 days? halve max_qty, add EARNINGS_PROXIMITY flag
    3. Position limit — existing position + new order > 10% of capital? reduce max_qty
    4. Cash check — enough capital for at least 1 share?
    5. VIX regime — if VIX > 20, add HIGH_VOLATILITY flag, reduce max_qty by 50%

    Never calls LLM. Pure deterministic rules.
    Returns AllowedAction with all constraints pre-computed.
    """
    sym = symbol.upper()
    flags: list[str] = []
    warnings: list[str] = []

    total_capital = _get_capital(capital)
    current_price = _get_price(sym, prices)

    # ── Guard: zero or missing capital ───────────────────────
    if total_capital <= 0:
        return AllowedAction(
            symbol=sym,
            allowed=False,
            direction="NONE",
            max_qty=0,
            max_capital=0.0,
            flags=flags,
            block_reason="No capital available",
            warnings=warnings,
        )

    # ── Check 1: Daily loss cap / trade counts ────────────────
    rl = _get_risk_limits()
    try:
        # Use a zero-price dummy call to just check the daily caps
        rl.check(sym, "BUY", 1, 0.0)
    except Exception as exc:
        return AllowedAction(
            symbol=sym,
            allowed=False,
            direction="NONE",
            max_qty=0,
            max_capital=0.0,
            flags=flags,
            block_reason=str(exc).splitlines()[0],  # first line only
            warnings=warnings,
        )

    # ── Compute base max_qty from position limit (10% of capital) ──
    position_limit = total_capital * 0.10  # 10% cap

    existing_value = _get_existing_position_value(sym, portfolio)
    remaining_room = position_limit - existing_value

    if current_price and current_price > 0:
        if remaining_room <= 0:
            # Already at or over the limit
            base_max_qty = 0
            flags.append("POSITION_LIMIT")
        else:
            base_max_qty = int(remaining_room / current_price)
            if existing_value > 0:
                # There IS an existing position — flag that limit is partially consumed
                flags.append("POSITION_LIMIT")
    else:
        # No price info — use a reasonable default based on capital
        base_max_qty = int(position_limit / 100)  # rough estimate

    max_qty = base_max_qty
    max_capital = min(remaining_room, position_limit) if remaining_room > 0 else 0.0

    # ── Check 2: Earnings proximity ───────────────────────────
    days_to_event = _days_until_event(sym, upcoming_events)
    if days_to_event is not None and days_to_event <= 3:
        flags.append("EARNINGS_PROXIMITY")
        warnings.append(f"Earnings within {days_to_event} day(s) — position halved")
        max_qty = max(max_qty // 2, 0)
        max_capital = max_capital / 2.0

    # ── Check 3: Cash check ───────────────────────────────────
    if current_price and current_price > 0:
        if total_capital < current_price:
            # Can't even afford 1 share
            return AllowedAction(
                symbol=sym,
                allowed=False,
                direction="NONE",
                max_qty=0,
                max_capital=0.0,
                flags=flags,
                block_reason="Insufficient capital — cannot afford 1 share",
                warnings=warnings,
            )
        if total_capital < current_price * 5:
            flags.append("LOW_CASH")
            warnings.append("Low capital — fewer than 5 shares affordable")

    # ── Check 4: VIX regime ───────────────────────────────────
    if vix is not None and vix > 20:
        flags.append("HIGH_VOLATILITY")
        warnings.append(f"VIX {vix:.1f} — high volatility, position halved")
        max_qty = max(max_qty // 2, 0)
        max_capital = max_capital / 2.0

    # ── Final: determine direction ────────────────────────────
    # Default to BOTH — caller can override based on portfolio context
    direction: Literal["BUY_ONLY", "SELL_ONLY", "BOTH", "NONE"] = "BOTH"
    if max_qty == 0:
        direction = "NONE"

    return AllowedAction(
        symbol=sym,
        allowed=True,
        direction=direction,
        max_qty=max_qty,
        max_capital=max_capital,
        flags=flags,
        block_reason="",
        warnings=warnings,
    )
