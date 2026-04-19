# Spec: Dual LLM Routing (#91)

## Problem
All 10 LLM calls in the multi-agent pipeline use the same model.
Extraction/classification calls don't need the same intelligence as debate/synthesis.

## Design

### Deep model (reasoning)
- Bull/Bear debate (5 calls)
- Risk debate (3 calls)
- Fund Manager synthesis (1 call)

### Fast model (extraction)
- News sentiment classification (`NewsMacroAnalyst`)
- Future: signal cleanup, output parsing

## Config via env vars
```bash
# Deep model (defaults to current AI_PROVIDER + AI_MODEL)
AI_DEEP_PROVIDER=anthropic         # optional — defaults to AI_PROVIDER
AI_DEEP_MODEL=claude-opus-4-5      # optional — defaults to AI_MODEL

# Fast model (defaults to deep model if not set — zero breaking change)
AI_FAST_PROVIDER=anthropic         # optional
AI_FAST_MODEL=claude-haiku-3-5    # optional; or gemini-flash

# Cross-provider example:
AI_DEEP_PROVIDER=anthropic
AI_DEEP_MODEL=claude-opus-4-5
AI_FAST_PROVIDER=gemini
AI_FAST_MODEL=gemini-2.0-flash
```

## New functions in `agent/core.py`
```python
def get_deep_provider(registry=None) -> LLMProvider:
    """Build the deep reasoning provider from AI_DEEP_* env vars (falls back to AI_*)."""

def get_fast_provider(registry=None) -> LLMProvider:
    """Build the fast extraction provider from AI_FAST_* env vars (falls back to deep)."""
```

## Changes to `MultiAgentAnalyzer`
```python
class MultiAgentAnalyzer:
    def __init__(self, registry, llm_provider, fast_llm_provider=None, ...):
        self.llm = llm_provider           # deep — debate + synthesis
        self.fast_llm = fast_llm_provider or llm_provider  # fast — extraction

    # Use fast_llm for news analyst:
    news_analyst.set_llm(self.fast_llm)
```

## Zero breaking change guarantee
- `fast_llm_provider=None` → falls back to `llm_provider`
- Old callers pass `MultiAgentAnalyzer(registry, provider)` → unchanged behavior
- If `AI_FAST_MODEL` not set → fast = deep (same as before)

## Files
- `agent/core.py` — `get_deep_provider()`, `get_fast_provider()`
- `agent/multi_agent.py` — `fast_llm_provider` param
- `web/skills.py` — build both providers when creating `MultiAgentAnalyzer`

## Acceptance Criteria
- `get_fast_provider()` returns deep provider when `AI_FAST_*` not set
- `get_fast_provider()` returns a different model when `AI_FAST_MODEL` set
- `MultiAgentAnalyzer` with `fast_llm_provider=None` behaves identically to current
- `MultiAgentAnalyzer` with different `fast_llm_provider` routes news analyst to fast
