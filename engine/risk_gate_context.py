"""
engine/risk_gate_context.py
────────────────────────────
Formats an AllowedAction into a compact text block for LLM synthesis prompts.

The output is injected into SYNTHESIS_PROMPT as a non-negotiable constraint
section — the LLM must respect the max_qty and direction limits.

Usage:
    from engine.risk_gate import AllowedAction
    from engine.risk_gate_context import format_risk_gate_for_llm

    allowed = compute_allowed_actions("INFY", "NSE")
    context_block = format_risk_gate_for_llm(allowed)
    # inject into synthesis prompt as {risk_gate_context}
"""

from __future__ import annotations

from engine.risk_gate import AllowedAction


def format_risk_gate_for_llm(allowed: AllowedAction) -> str:
    """
    Format AllowedAction as a compact block for LLM synthesis prompts.

    Example output (allowed):
    RISK GATE (pre-computed, non-negotiable):
      Status     : ALLOWED
      Direction  : BUY_ONLY
      Max qty    : 44 shares  (max capital: ₹61,600)
      Flags      : EARNINGS_PROXIMITY
      Warning    : Earnings within 1 day(s) — position halved

    These limits are HARD CONSTRAINTS. Your recommendation must not exceed them.

    Example output (blocked):
    RISK GATE (pre-computed, non-negotiable):
      Status     : BLOCKED
      Reason     : Order blocked — daily loss cap reached.

      DO NOT recommend any BUY or SELL for this symbol today.
      Recommend HOLD or "no new positions".
    """
    lines = ["RISK GATE (pre-computed, non-negotiable):"]

    if not allowed.allowed:
        lines.append("  Status     : BLOCKED")
        lines.append(f"  Reason     : {allowed.block_reason}")
        lines.append("")
        lines.append("  DO NOT recommend any BUY or SELL for this symbol today.")
        lines.append('  Recommend HOLD or "no new positions".')
    else:
        lines.append("  Status     : ALLOWED")
        lines.append(f"  Direction  : {allowed.direction}")

        if allowed.max_qty > 0:
            cap_str = f"max capital: ₹{allowed.max_capital:,.0f}"
            lines.append(f"  Max qty    : {allowed.max_qty} shares  ({cap_str})")
        else:
            lines.append("  Max qty    : 0 shares  (position limit reached)")

        if allowed.flags:
            lines.append(f"  Flags      : {', '.join(allowed.flags)}")

        for warning in allowed.warnings:
            lines.append(f"  Warning    : {warning}")

    lines.append("")
    lines.append("These limits are HARD CONSTRAINTS. Your recommendation must not exceed them.")
    if allowed.allowed and allowed.direction in ("BUY_ONLY", "SELL_ONLY"):
        blocked_dir = "SELL" if allowed.direction == "BUY_ONLY" else "BUY"
        lines.append(
            f"Do NOT recommend a {blocked_dir} — direction is restricted to {allowed.direction}."
        )
    if allowed.allowed:
        lines.append(
            f"Do not recommend a position larger than {allowed.max_qty} shares "
            f"or ₹{allowed.max_capital:,.0f}."
        )

    return "\n".join(lines)
