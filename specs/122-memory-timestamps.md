# Spec: Memory Timestamps + Analysis Snapshot (#122) + Stats Fix (#123)

## Issues

### #122 — Missing timestamp + analysis snapshot
- `timestamp` field exists but may not be populated in all records
- No `price_at_analysis` stored (can't correlate to market events)
- Full synthesis text not stored — just the parsed verdict/confidence
- `_load()` fails silently if JSON has unknown keys or missing fields

### #123 — Misleading stats
- Win Rate shows 100% when only 1–2 outcomes tracked out of 20 analyses
- All verdicts show HOLD — `_parse_synthesis()` fails to extract verdict when LLM uses markdown formatting (e.g. `**VERDICT: BUY**`)
- Avg confidence 50% — same parsing failure, defaults to 50

## Fixes

### #122 Additions to `TradeRecord`
```python
price_at_analysis: Optional[float] = None   # LTP at time of analysis
synthesis_text: str = ""                    # full synthesis output stored
```

### #122 Fix `_load()` backward compatibility
```python
def _load(self):
    data = json.loads(...)
    self._records = [TradeRecord(**{k: v for k, v in d.items() if k in TradeRecord.__dataclass_fields__}) for d in data]
```

### #122 Pass price to `store_from_analysis()`
```python
trade_memory.store_from_analysis(symbol, exchange, analyst_reports, debate, synthesis, price=spot_price)
```

### #123 Fix `_parse_synthesis()` — use regex
```python
import re
# Match: VERDICT: BUY, **VERDICT: BUY**, Verdict: Strong Buy (case insensitive)
verdict_match = re.search(r'verdict[:\s]+([^\n\r,\.]+)', text, re.IGNORECASE)
```

### #123 Fix `get_stats()` — minimum sample warning
```python
"win_rate": win_rate if len(with_outcome) >= 5 else None,
"win_rate_label": f"{len(wins)}/{len(with_outcome)} tracked" if with_outcome else "No outcomes",
"win_rate_insufficient": len(with_outcome) < 5,
```

## Acceptance Criteria
- New records always have non-null `timestamp` and `price_at_analysis`
- `synthesis_text` stores full LLM output
- Old JSON records load without crashing (backward compat)
- `_parse_synthesis("**VERDICT: BUY**\nCONFIDENCE: 72%")` → ("BUY", 72, "")
- `get_stats()["win_rate"]` is `None` when fewer than 5 outcomes tracked
- `get_stats()["win_rate_label"]` shows fraction like "1/2 tracked"
