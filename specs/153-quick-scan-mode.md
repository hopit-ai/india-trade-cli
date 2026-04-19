# Spec: Quick Scan Mode (#153)

## Problem
Full multi-agent analysis takes 30–90s (8 LLM calls). Users want a fast directional read.

## Proposal
`quick INFY` → single-agent analysis in 3–5 seconds.

```
> quick INFY
  INFY: BUY (72%) — PE 18x below sector avg, RSI 54 neutral, OI support at 1280
  Entry: ₹1,410  SL: ₹1,370  Target: ₹1,480
  ⏱ 3.2s | 1 LLM call
```

## Architecture

### New file: `agent/quick_scan.py`
```python
class QuickScanner:
    def scan(symbol, exchange="NSE", provider=None) -> QuickScanResult:
        # 1. Gather data: technical + fundamental (pure Python, no LLM)
        # 2. Single LLM call with concise structured prompt
        # 3. Parse response: verdict, confidence, reasons, entry/sl/target
```

### Data gathering (pure Python — existing analyst tool functions):
- `registry.execute("technical_analyse", {symbol, exchange})`
- `registry.execute("fundamental_data", {symbol})` 
- `market.quotes.get_ltp(symbol)` for current price

### Single LLM call:
Prompt feeds RSI, MACD, PE, volume, price — asks for:
```
VERDICT: BUY/SELL/HOLD
CONFIDENCE: 0-100
REASON: (3-5 bullet points)  
ENTRY: price
SL: price
TARGET: price
```

### CLI:
- `quick SYMBOL` — already has `quick` in COMMANDS list? Add as new command
- `quick INFY RELIANCE TCS` — multi-symbol (parallel)

### Endpoint: `POST /skills/quick_analyze`
```json
{"symbol": "INFY", "exchange": "NSE"}
→ {"verdict", "confidence", "reasons", "entry", "sl", "target", "ltp", "elapsed_ms"}
```

## Result schema
```python
@dataclass
class QuickScanResult:
    symbol: str
    verdict: str          # BUY / SELL / HOLD
    confidence: int       # 0-100
    reasons: list[str]    # 3-5 bullet points
    entry: float | None
    sl: float | None
    target: float | None
    ltp: float            # price at scan time
    elapsed_ms: int
    error: str | None = None
```

## Comparison
| Mode | LLM calls | Time | Depth |
|------|-----------|------|-------|
| quick | 1 | 3-5s | Signal |
| analyze | 8 | 30-90s | Full |
| deep-analyze | 11 | 3-8min | Institutional |

## Files
- `agent/quick_scan.py` — new
- `web/skills.py` — new `POST /skills/quick_analyze`
- `app/repl.py` — `quick SYMBOL` command
