# Issue #175 — Pydantic Structured Outputs (Scoped to Synthesis)

## Problem

The synthesis LLM output in `engine/trader.py` is parsed with brittle string-scanning:
- `_parse_synthesis_verdict()` (line 1133) — uses `startswith("VERDICT:")` 
- `_extract_rationale()` (line 1069) — scans for "RATIONALE"/"WHY" sections
- `_extract_risks()` (line 1084) — scans for "RISK" sections

These fail silently on any minor LLM formatting variation and return defaults without error.

## Solution

Replace the three text-scanning functions with a single Pydantic-validated parser that:
1. Tries JSON first (if LLM returns `{...}`)
2. Falls back to structured line-by-line parsing (preserving current behavior)
3. Always returns a valid `SynthesisOutput` — never raises

## Scope

**In scope:**
- `agent/schemas.py` — Pydantic models for synthesis, analyst signal, persona signal
- `agent/schema_parser.py` — `parse_synthesis_output()` function
- `engine/trader.py` — replace `_parse_synthesis_verdict`, `_extract_rationale`, `_extract_risks`
- `agent/multi_agent.py` — update `SYNTHESIS_PROMPT` to hint at JSON option
- `tests/test_schemas.py` — unit tests (no LLM calls)
- `pyproject.toml` — add pydantic to dependencies

**Out of scope:**
- `TradeRecommendation` dataclass in `multi_agent.py` — must stay unchanged
- `TradePlan` dataclass — must stay unchanged
- Any other LLM call parsing beyond synthesis
- Database/storage changes

## Data Models

### `SynthesisOutput`

```python
class SynthesisOutput(BaseModel):
    verdict: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    confidence: int = Field(ge=0, le=100)
    winner: Literal["BULL", "BEAR", "NEUTRAL"] = "NEUTRAL"
    strategy: str = ""
    entry: str = ""
    stop_loss: str = ""
    target: str = ""
    risk_reward: str = ""
    position: str = ""
    rationale: list[str] = []
    risks: list[str] = []
```

### `AnalystSignal`

```python
class AnalystSignal(BaseModel):
    analyst: str
    verdict: Literal["BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"]
    confidence: int = Field(ge=0, le=100)
    score: float
    key_points: list[str] = []
    error: str = ""
```

### `PersonaSignal`

```python
class PersonaSignal(BaseModel):
    persona: str
    verdict: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    confidence: int = Field(ge=0, le=100)
    rationale: list[str] = []
    key_metrics: dict[str, str] = {}
```

## Parser Logic

`parse_synthesis_output(text: str) -> SynthesisOutput`:

1. **JSON path**: If `{` in text, extract the JSON block and attempt `json.loads()`. 
   Validate with `SynthesisOutput.model_validate()`. On success, return.
2. **Text path**: Line-by-line scanning:
   - `VERDICT:` → map to enum (STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL)
   - `CONFIDENCE:` → strip `%`, parse int, clamp 0-100
   - `WINNER:` → extract BULL/BEAR/NEUTRAL
   - `TRADE RECOMMENDATION:` block → parse sub-lines:
     - `Strategy  :` → `strategy`
     - `Entry     :` → `entry`
     - `Stop-Loss :` → `stop_loss`
     - `Target    :` → `target`
     - `R:R Ratio :` → `risk_reward`
     - `Position  :` → `position`
   - `RATIONALE` section → collect `- ` bullets → `rationale` (max 5)
   - `RISKS` section → collect `- ` bullets → `risks` (max 5)
3. **Fallback**: Any `ValidationError` or exception → return `SynthesisOutput()` with defaults

## SYNTHESIS_PROMPT Change

Add after the existing text format:
```
Alternatively, if your LLM supports JSON mode, you MAY return a JSON object with these exact keys:
{"verdict": "BUY", "confidence": 72, "winner": "BULL", "strategy": "...", "entry": "...",
 "stop_loss": "...", "target": "...", "risk_reward": "...", "position": "...",
 "rationale": ["...", "..."], "risks": ["...", "..."]}
The text format above is always acceptable and preferred for readability.
```

## Integration in `engine/trader.py`

Replace:
```python
verdict, confidence, strategy_hint = _parse_synthesis_verdict(synthesis)
# ...
rationale = self._extract_rationale(synthesis_text) if synthesis_text else []
risks = self._extract_risks(synthesis_text) if synthesis_text else []
```

With:
```python
from agent.schema_parser import parse_synthesis_output
parsed = parse_synthesis_output(synthesis)
verdict, confidence, strategy_hint = parsed.verdict, parsed.confidence, parsed.strategy
# ...
rationale = parse_synthesis_output(synthesis_text).rationale if synthesis_text else []
risks = parse_synthesis_output(synthesis_text).risks if synthesis_text else []
```

Or more cleanly: call `parse_synthesis_output` once and use fields.

## Tests (`tests/test_schemas.py`)

1. `SynthesisOutput` field validation:
   - Valid construction
   - Invalid verdict raises `ValidationError`
   - Confidence out of range raises `ValidationError`
   - Defaults populate correctly

2. `parse_synthesis_output` with:
   - Full well-formed text (all fields present)
   - JSON text (valid JSON)
   - Partial text (only VERDICT line)
   - Empty string
   - Malformed text

3. Field extraction:
   - VERDICT line parsing (all 5 verdicts)
   - CONFIDENCE line (with/without %)
   - TRADE RECOMMENDATION block (Entry/Stop-Loss/Target/Strategy/R:R/Position)
   - RATIONALE bullets
   - RISKS bullets
   - WINNER line

## Acceptance Criteria

- All tests in `tests/test_schemas.py` pass with no LLM calls
- `python -m ruff check --fix` and `python -m ruff format` pass on changed files
- `python -m pytest --timeout=30 -q -m "not network" --ignore=tests/test_p0_fixes.py` passes
- `_parse_synthesis_verdict`, `_extract_rationale`, `_extract_risks` are removed from `trader.py`
- `TradeRecommendation` dataclass in `multi_agent.py` is unchanged
- `pydantic>=2.0.0` added to `pyproject.toml` dependencies
