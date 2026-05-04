# Spec: Named Investor Personas (#165)

## Overview

Add 5 named investor personas to the trading CLI — each representing a legendary investor's
philosophy. Users can ask any persona to evaluate a stock or run a "debate" with all 5 personas
producing their signals side-by-side.

## Personas

| ID             | Name                  | Style           |
|----------------|-----------------------|-----------------|
| buffett        | Warren Buffett        | value           |
| jhunjhunwala   | Rakesh Jhunjhunwala   | growth-value    |
| lynch          | Peter Lynch           | garp            |
| soros          | George Soros          | macro           |
| munger         | Charlie Munger        | quality         |

## Data Model

`PersonaSignal` — lives in `agent/schemas.py`:

```python
class PersonaSignal(BaseModel):
    persona: str                   # persona id
    verdict: Literal["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL"]
    confidence: int                # 0-100
    rationale: list[str]           # checklist items (pass/fail/partial)
    key_metrics: dict[str, str]    # {"ROE": "8% (need >15%)", ...}
```

`InvestorPersona` — lives in `agent/personas.py`:

```python
@dataclass
class InvestorPersona:
    id: str
    name: str
    style: str
    checklist: list[str]           # ≥5 items each
    weights: dict[str, float]      # must sum to 1.0
    system_prompt: str
```

## Files

1. `agent/schemas.py` — `PersonaSignal(BaseModel)` Pydantic model
2. `agent/personas.py` — `InvestorPersona` dataclass + `PERSONAS` dict + helpers
3. `agent/persona_agent.py` — `run_persona_analysis()` + `run_debate()`
4. `app/commands/persona.py` — CLI `run()` handler
5. `app/repl.py` — wire in `persona` and `debate` commands
6. `tests/test_personas.py` — tests (no LLM required)

## Persona Weights

| Persona      | fundamentals | macro | technicals | sentiment | options |
|--------------|-------------|-------|------------|-----------|---------|
| buffett      | 0.65        | 0.10  | 0.05       | 0.10      | 0.10    |
| jhunjhunwala | 0.40        | 0.30  | 0.20       | 0.10      | —       |
| lynch        | 0.50        | 0.10  | 0.20       | 0.20      | —       |
| soros        | 0.05        | 0.50  | 0.20       | 0.25      | —       |
| munger       | 0.55        | 0.15  | 0.10       | 0.20      | —       |

Note: jhunjhunwala, lynch, soros, munger do not use options; their weights sum to 1.0 over
the four categories they use.

## Rule-Based Fallback (no LLM)

When `llm_provider=None`, `run_persona_analysis()` uses a deterministic scoring approach:

1. Fetch data via registry tools (or use empty defaults if registry is also None)
2. Score each dimension (fundamentals, macro, technicals, sentiment, options) 0–100
3. Weighted sum → overall score
4. Map score to verdict: ≥80 STRONG_BUY, ≥65 BUY, ≥40 HOLD, ≥25 SELL, <25 STRONG_SELL
5. Confidence = score (capped 0-100)

## CLI Usage

```
persona list                    — list all 5 personas
persona buffett RELIANCE        — single persona on NSE:RELIANCE
persona buffett NSE:RELIANCE    — explicit exchange
debate RELIANCE                 — all 5 personas + consensus
```

## Terminal Output

Single persona (`persona buffett RELIANCE`):
```
━━━ Warren Buffett on NSE:RELIANCE ━━━━━━━━━━━━━━━━━
Signal     : HOLD  (58% confidence)
Checklist  :
  ✓ Strong competitive moat (Jio telecom + retail)
  ✗ ROE 8% — below 15% threshold
  ✗ FCF yield 2.1% — want > 5%
  ~ PE 28x: not cheap enough for uncertainty
Key Metrics:
  ROE    : 8% (threshold: >15%)
  D/E    : 0.4 (ok)
Reasoning  : [2-3 sentences in Buffett's voice]
```

Debate (`debate RELIANCE`):
```
━━━ Investor Debate: NSE:RELIANCE ━━━━━━━━━━━━━━━━━
┌──────────────────┬────────────┬────────────┬──────────────────────┐
│ Persona          │ Signal     │ Confidence │ Key Factor           │
├──────────────────┼────────────┼────────────┼──────────────────────┤
│ Buffett          │ HOLD       │ 58%        │ ROE below threshold  │
│ Jhunjhunwala     │ BUY        │ 75%        │ India growth story   │
│ Lynch            │ BUY        │ 68%        │ PEG < 1.2, clear biz │
│ Soros            │ HOLD       │ 52%        │ FII flows mixed      │
│ Munger           │ HOLD       │ 61%        │ Complexity concerns  │
└──────────────────┴────────────┴────────────┴──────────────────────┘
Consensus  : HOLD (3/5) — BUY camp: Jhunjhunwala, Lynch
```

## Testing Requirements

All tests in `tests/test_personas.py`, no LLM required:

- All 5 personas defined in PERSONAS dict
- Each has non-empty checklist (≥5 items), weights summing to 1.0, non-empty system_prompt
- `get_persona("buffett")` returns InvestorPersona with correct id
- `get_persona("invalid")` raises ValueError
- `list_personas()` returns exactly 5 items
- `PersonaSignal` validates correctly (verdict enum, confidence 0-100)
- Deterministic fallback (no LLM, no registry) returns valid PersonaSignal
- `parse_persona_response` handles valid, partial, and empty text
