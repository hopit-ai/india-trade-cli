# Spec: Interactive Strategy Builder (#44)

## Problem
Users have to write Python code or know strategy names to create custom strategies.
No guided flow for describing a strategy in plain English and getting it built.

## Solution

### engine/strategy_builder.py — add StrategyBuilderSession

A stateful session that:
1. Collects requirements via structured questions (entry, exit, risk, timing)
2. Builds a `StrategySpec` from answers
3. Generates the corresponding backtest Strategy subclass
4. Runs backtest and returns results
5. Optionally saves to StrategyStore

```python
session = StrategyBuilderSession(llm_provider)
questions = session.start("Buy NIFTY when RSI drops below 30 and price above 50 EMA")
# → [Q1, Q2, Q3, ...]
session.answer("Q1", "14")
session.answer("Q2", "Daily")
spec = session.finalize()  # → StrategySpec
result = session.build_and_backtest("NIFTY", "1y")
```

### StrategySpec dataclass
```python
@dataclass
class StrategySpec:
    name: str
    description: str
    entry_conditions: list[str]
    exit_conditions: list[str]
    stop_loss_pct: float
    target_pct: float
    max_hold_days: int
    position_size_pct: float
    generated_code: str
```

### POST /skills/strategy_builder
- Start a session: `{"action": "start", "description": "..."}`  
- Answer a question: `{"action": "answer", "session_id": "...", "answer": "..."}`
- Finalize: `{"action": "finalize", "session_id": "..."}`

## CLI
```
> strategy new
Description: Buy NIFTY when RSI drops below 30 and price above 50 EMA
...
```

## Acceptance Criteria
- `StrategyBuilderSession` can be created with or without LLM provider
- `session.start(description)` returns a list of clarifying questions
- `session.finalize()` returns a `StrategySpec` with populated fields
- Without LLM, uses rule-based question extraction
