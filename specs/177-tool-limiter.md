# Spec: Soft tool limiting + loop detection (#177)

## Problem
LLM agents can enter runaway tool call loops, calling the same tool repeatedly
or alternating between two tools. This wastes tokens and time.

## Solution
`engine/tool_limiter.py` — ToolLimiter class that:
- Tracks tool calls per session
- Warns when same tool exceeds soft_limit_per_tool (default: 5)
- Detects A-B-A-B-A-B alternating loops (6 consecutive alternating calls)
- Warns when total calls exceed hard_limit_total (default: 30)
- Never raises — only returns warning strings

Wired into `agent/tools.py` ToolRegistry.execute():
- Called before executing the tool function
- Warning appended to tool result as `_tool_warning` key

## Interface
```python
class ToolLimiter:
    def __init__(self, soft_limit_per_tool=5, hard_limit_total=30)
    def check_and_record(tool_name: str) -> str | None
    def get_summary() -> dict
    def reset() -> None
```

## Tests
`tests/test_tool_limiter.py`
