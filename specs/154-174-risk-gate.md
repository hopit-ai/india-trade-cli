# Spec: Deterministic Risk Gate + Hard Risk Limits (#154 #174)

## Overview

Two related features:

1. **#154 — Hard Risk Limits**: `engine/risk_limits.py` is fully implemented and wired into
   `engine/trade_executor.py`. The remaining gap is a `risk-status` REPL command to inspect
   current daily usage.

2. **#174 — Deterministic Risk Gate**: A pre-LLM gate that computes what actions are ALLOWED
   for a symbol *before* the LLM makes a trade recommendation. The LLM receives these
   constraints as non-negotiable hard limits injected into its synthesis prompt.

---

## #154 — Missing Piece: `risk-status` REPL command

### Command
```
risk-status
```

### Behaviour
Calls `risk_limits.get_status()` and prints a Rich table showing:

| Field                  | Value                       |
|------------------------|-----------------------------|
| Daily P&L              | ₹ value (red if negative)   |
| Daily Loss Cap         | ₹ value                     |
| Remaining Loss Room    | ₹ value                     |
| Trades Today           | N / max                     |
| Remaining Trades       | N                           |
| Max Trades per Symbol  | N                           |
| Limits Hit             | YES (red) / NO (green)      |

Wire via `elif command == "risk-status":` in `app/repl.py`.

---

## #174 — Risk Gate

### Purpose
The risk gate runs **before** the LLM. It pre-computes what actions are ALLOWED and passes
those bounds to the LLM as hard constraints. This prevents the LLM from recommending a
trade that would be blocked downstream.

### File: `engine/risk_gate.py`

#### `AllowedAction` dataclass
```python
@dataclass
class AllowedAction:
    symbol: str
    allowed: bool                    # False = blocked entirely
    direction: Literal["BUY_ONLY", "SELL_ONLY", "BOTH", "NONE"]
    max_qty: int                     # max shares allowed (0 if blocked)
    max_capital: float               # max INR value (0 if blocked)
    flags: list[str]                 # ["EARNINGS_PROXIMITY", "HIGH_VOLATILITY", "LOW_CASH"]
    block_reason: str = ""           # non-empty if allowed=False
    warnings: list[str] = field(default_factory=list)
```

#### `compute_allowed_actions()` — deterministic rule pipeline

Checks in order:

1. **Daily loss cap / trade counts** — call `risk_limits.check()` with a dummy price (0.0).
   If `RiskLimitError` is raised → `allowed=False`, `direction="NONE"`, `max_qty=0`.

2. **Earnings proximity** — check if an upcoming earnings event is within 3 calendar days.
   If yes: halve `max_qty`, add `"EARNINGS_PROXIMITY"` to `flags`.

3. **Position limit** — existing position value + new order value must not exceed 10% of
   total capital. If it would: reduce `max_qty` so the combined value stays within 10%.
   Add `"POSITION_LIMIT"` to `flags` if qty was reduced.

4. **Cash check** — if capital < price of 1 share: `allowed=False`, `block_reason="LOW_CASH"`.
   If capital < price of 5 shares: add `"LOW_CASH"` to `flags`.

5. **VIX regime** — if VIX > 20: add `"HIGH_VOLATILITY"` flag, reduce `max_qty` by 50%.

Rules are deterministic — no LLM calls, no network required for the core logic.
Portfolio and prices can be injected (for tests) or read from defaults.

### File: `engine/risk_gate_context.py`

#### `format_risk_gate_for_llm()` — LLM prompt formatter
```python
def format_risk_gate_for_llm(allowed: AllowedAction) -> str:
    """
    Format AllowedAction as a compact block for LLM synthesis prompts.

    Example output:
    RISK GATE (pre-computed, non-negotiable):
      Status     : ALLOWED
      Direction  : BUY_ONLY
      Max qty    : 44 shares  (₹60,000 position limit)
      Flags      : EARNINGS_PROXIMITY
      Warning    : Earnings within 3 days — position halved

    These limits are HARD CONSTRAINTS. Your recommendation must not exceed them.
    """
```

For `allowed=False`:
```
RISK GATE (pre-computed, non-negotiable):
  Status     : BLOCKED
  Reason     : Daily loss cap reached (-₹20,000)

  DO NOT recommend any BUY or SELL for this symbol today.
  Recommend HOLD or "no new positions".
```

### Wiring into `agent/multi_agent.py`

In `analyze()`, after `run_analysis_pipeline()` (Stage 1), before debate:

```python
from engine.risk_gate import compute_allowed_actions
from engine.risk_gate_context import format_risk_gate_for_llm

allowed = compute_allowed_actions(symbol, exchange)
risk_gate_context = format_risk_gate_for_llm(allowed)

if not allowed.allowed:
    # Skip debate + synthesis — return blocked message directly
    return f"[RISK GATE BLOCKED]\n{risk_gate_context}"
```

Inject `risk_gate_context` into `_run_synthesis()` via a new keyword argument.

### Wiring into `agent/prompts.py` `SYNTHESIS_PROMPT`

Add `{risk_gate_context}` placeholder after `{risk_context}`:

```
## Risk Gate Constraints (HARD — pre-computed before LLM)
{risk_gate_context}
```

Instructions injected at the bottom of the prompt section:
```
HARD CONSTRAINTS from risk gate — your recommendation MUST respect these limits.
Do not recommend a position larger than max_qty. Do not recommend the blocked direction.
```

---

## Tests (`tests/test_risk_gate.py`)

1. `AllowedAction` dataclass has correct fields and defaults.
2. `compute_allowed_actions()` returns `AllowedAction` even when all checks pass.
3. `earnings_proximity` flag set when upcoming event within 3 days.
4. Position limit reduces `max_qty` correctly.
5. `allowed=False` when daily loss cap already hit (mock `risk_limits`).
6. `format_risk_gate_for_llm()` output contains "RISK GATE" and "HARD CONSTRAINTS".
7. All tests pass without LLM or network calls.

---

## Acceptance Criteria

- [ ] `risk-status` command works in REPL and shows current usage.
- [ ] `compute_allowed_actions()` is deterministic — same inputs → same outputs.
- [ ] Risk gate blocks trade when daily loss cap hit.
- [ ] Earnings proximity halves max_qty.
- [ ] Position limit reduces max_qty to respect 10% cap.
- [ ] VIX > 20 reduces max_qty by 50%.
- [ ] `format_risk_gate_for_llm()` produces a compact, readable block.
- [ ] `agent/multi_agent.py` returns a blocked message when `allowed=False` without calling LLM.
- [ ] `SYNTHESIS_PROMPT` includes `{risk_gate_context}` placeholder.
- [ ] All existing tests continue to pass.
