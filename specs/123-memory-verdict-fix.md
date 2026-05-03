# Spec: Memory all-HOLD verdicts bug fix (#123)

## Problem
`store_from_analysis()` calls `_parse_synthesis()` to extract verdict from raw LLM
synthesis text. The regex can silently default to HOLD when the LLM uses unusual
formatting (e.g. inline bold, trailing punctuation, extra whitespace). This causes
trade memory to record HOLD even when the actual verdict was BUY or SELL.

## Solution
Move the parsing logic to a dedicated `agent/schema_parser.py` module with
`parse_synthesis_output()`. This function:
- Accepts raw synthesis text
- Returns `(verdict: str, confidence: int, strategy: str)`
- Uses multi-pass regex: explicit label, then keyword scan fallback
- Handles markdown bold (`**VERDICT: BUY**`), mixed case, trailing punctuation
- Never returns an empty string for verdict (defaults to "HOLD")

Update `engine/memory.py` to import and use `parse_synthesis_output()` instead of
the local `_parse_synthesis()`. Keep `_parse_synthesis` as a thin wrapper calling
the new function for backward compatibility.

## Tests
`tests/test_memory_timestamps.py` — class `TestParseSynthesisFixed` already covers
the key cases. Additional tests in `tests/test_memory_verdict.py`.
