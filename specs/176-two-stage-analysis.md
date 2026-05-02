# Spec: Two-Stage Analysis Pipeline (#176)

## Problem

`analyze RELIANCE` today makes up to 8 LLM calls with ~20,000 input tokens:

- 5 debate calls (bull, bear, bull rebuttal, bear rebuttal, facilitator)
- 1 synthesis call
- 2 optional (NewsMacro + Sentiment LLM mode)

Every debate and synthesis call receives the full verbose `summary_text()` from all 7 analysts
(~1,000 tokens per prompt × 5 prompts = ~5,000 extra tokens just for analyst context repetition).

Additionally, when all 7 analysts agree — e.g., all BULLISH — the debate phase still runs its 5
LLM calls, arguing for and against a direction the evidence doesn't support.

## Architecture

### Stage 1 — Deterministic (already exists, now made explicit)

The 7 analyst agents already run in Python with no LLM involvement (TechnicalAnalyst,
FundamentalAnalyst, OptionsAnalyst, SentimentAnalyst keyword-mode, SectorRotationAnalyst,
RiskAnalyst). Stage 1 makes this contract explicit via `AnalysisContext`.

```
run_analysis_pipeline(symbol, exchange, registry)
  → runs 7 analysts in parallel
  → computes AnalystScorecard
  → produces compact_signals string (~200 tokens)
  → sets should_skip_debate flag
  → returns AnalysisContext
```

### Stage 2 — LLM synthesis (unchanged API, smaller input)

Every LLM call now receives `compact_signals` instead of 7× `summary_text()`.

```
Analyst context input: ~1,000 tokens → ~200 tokens (80% reduction per call)
Total token savings across 5 debate calls: ~4,000 tokens
```

### Fast-path — skip debate when analysts agree

When `scorecard.agreement >= 80` AND `abs(scorecard.weighted_total) >= 25`:
- Skip all 5 debate LLM calls
- Run 1 compact synthesis call with a simplified prompt
- Saves ~5 LLM calls per analysis

## New Dataclass: `AnalysisContext`

```python
@dataclass
class AnalysisContext:
    symbol: str
    exchange: str
    reports: list[AnalystReport]
    scorecard: AnalystScorecard
    compact_signals: str       # pre-formatted table for LLM prompts
    should_skip_debate: bool   # True when agreement threshold met
    ltp: float = 0.0           # last traded price from technical report
```

## Compact Signal Format

Replaces verbose `r.summary_text()` in debate and synthesis prompts:

```
SYMBOL: RELIANCE (NSE) | Price: ₹2,850.40

PRE-COMPUTED SIGNALS — do not recompute, reference only:
┌─────────────────┬──────────┬───────┬────────────┬──────────────────────────────────┐
│ Analyst         │ Verdict  │ Score │ Confidence │ Key Metrics                      │
├─────────────────┼──────────┼───────┼────────────┼──────────────────────────────────┤
│ Technical       │ BEARISH  │  -35  │    65%     │ RSI:45 MACD:bear below EMA50     │
│ Fundamental     │ BULLISH  │  +55  │    70%     │ PE:28.5 ROE:18% D/E:0.3          │
│ Options         │ NEUTRAL  │   +5  │    40%     │ PCR:0.92 IVR:68 MaxPain:2500     │
│ News & Macro    │ BEARISH  │  -20  │    50%     │ FII:net-sell 3 bearish headlines  │
│ Sentiment       │ NEUTRAL  │    0  │    30%     │ keyword-based                    │
│ Sector Rotation │ BULLISH  │  +30  │    60%     │ IT sector outperforming          │
│ Risk Manager    │ NEUTRAL  │  -10  │    55%     │ VIX:14.2 cap:₹200k              │
└─────────────────┴──────────┴───────┴────────────┴──────────────────────────────────┘
Scorecard: NEUTRAL (weighted: -5.0, agreement: 42%)
Conflicts: Technical BEARISH vs Fundamental BULLISH
```

## Fast-Path Output

When `should_skip_debate=True`, produce a `DebateResult` from the scorecard without LLM:

```
DebateResult(
  bull_argument  = "Scorecard: {verdict} (agreement: {pct}%). Fast-path: analysts agree.",
  bear_argument  = "",
  winner         = derived from scorecard direction,
  rounds         = 0,
  fast_path      = True,
)
```

## Files

| File | Change |
|------|--------|
| `analysis/pipeline.py` | NEW — `AnalysisContext`, `build_compact_signals()`, `run_analysis_pipeline()` |
| `agent/multi_agent.py` | Use `AnalysisContext`; compact signals in debate prompts; fast-path logic |
| `tests/test_pipeline.py` | NEW — tests for Stage 1 and fast-path |

## Acceptance Criteria

- [ ] `AnalysisContext` produced by `run_analysis_pipeline()` contains scorecard, compact_signals, should_skip_debate
- [ ] `compact_signals` format fits in ≤ 300 tokens regardless of analyst count
- [ ] All debate and synthesis prompts receive `compact_signals` instead of `summary_text()`
- [ ] When agreement ≥ 80% AND weighted_total abs ≥ 25: debate skipped, terminal shows "[fast-path]"
- [ ] When agreement < 80%: full debate runs as before
- [ ] Output format unchanged from user perspective
- [ ] `analysis/pipeline.py` has no LLM imports — Stage 1 is pure Python

## Token Budget (Target)

| Call | Before | After |
|------|--------|-------|
| Each debate prompt (×5) | ~2,000 input tokens | ~400 input tokens |
| Synthesis prompt | ~5,000 input tokens | ~1,500 input tokens |
| Fast-path (high agreement) | 5+1 LLM calls | 1 LLM call |
| **Total (normal path)** | **~18,000 tokens** | **~6,000 tokens** |
| **Total (fast-path)** | **~18,000 tokens** | **~2,000 tokens** |
