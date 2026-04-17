# Spec: Reflect-and-Remember (#92)

## Problem
`engine/memory.py` stores trade outcomes (WIN/LOSS, P&L) but never extracts learnable lessons.
The `SYNTHESIS_PROMPT` has a `{memory_context}` placeholder that feeds past analyses into the
Fund Manager, but the lessons from past wins/losses are not explicitly surfaced.

## Solution

### engine/memory.py — add `lesson` field + `reflect_and_remember()`

Add `lesson: str = ""` to `TradeRecord` (backward compatible — defaults to "").

Add `reflect_and_remember(trade_id, llm_provider=None) -> str`:
1. Load the trade record by ID
2. Build a reflection prompt summarising the trade (verdict, conditions, outcome, P&L)
3. Call LLM (or rule-based fallback if no provider) to extract a 1-3 sentence lesson
4. Store the lesson on `record.lesson` and persist
5. Return the lesson string

### app/repl.py — add `memory reflect <trade_id>` command

Parse the command and call `trade_memory.reflect_and_remember(trade_id, llm_provider)`.
Print the lesson to the console.

### get_context_for_symbol() — include lessons

Update the method to include the lesson text in the per-record summary if present.

## Rule-based fallback (no LLM)

When `llm_provider=None`:
- WIN → "The {verdict} signal on {symbol} was correct — the trade closed with a gain."
- LOSS → "The {verdict} signal on {symbol} was incorrect — consider tightening stop-loss."
- HOLD → "The {symbol} trade was a wash — market conditions may have changed."

## Acceptance Criteria
- `reflect_and_remember("nonexistent-id")` returns "" and does not crash
- For a WIN trade, the lesson mentions the verdict and symbol
- For a LOSS trade, the lesson advises tightening or reviewing the thesis
- `record.lesson` is persisted to JSON
- Backward compat: existing records (no `lesson` field) load without error
