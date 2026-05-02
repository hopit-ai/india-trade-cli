# Spec: Strategy Marketplace (#161)

## Problem
Users can build strategies but can't share or import them.
No way to distribute a strategy with its verified backtest results.

## Solution

### Strategy export format (JSON package)

A strategy "package" is a JSON file containing:
```json
{
  "version": "1.0",
  "name": "rsi_ema_filter",
  "description": "Buy when RSI < 30 and price above 50 EMA",
  "author": "...",
  "created_at": "2026-04-11",
  "code": "class RsiEmaStrategy(Strategy):\n ...",
  "backtest": {
    "symbol": "NIFTY",
    "period": "1y",
    "total_return": 18.5,
    "sharpe": 1.4,
    "max_drawdown": -8.2,
    "win_rate": 64.0
  },
  "tags": ["nifty", "rsi", "swing-trade"],
  "license": "MIT"
}
```

### StrategyStore additions
- `export(name, output_path)` → writes JSON package
- `import_strategy(source)` → loads from local path or URL
- `verify_strategy(package)` → re-runs backtest, checks metrics match

### CLI commands
- `strategy export <name>` → saves JSON package
- `strategy import <path|url>` → imports and optionally verifies
- `strategy list` → shows installed strategies with marketplace metadata

### POST /skills/strategy/export and /skills/strategy/import
Simple endpoints wrapping the above.

## Acceptance Criteria
- Export produces valid JSON with required fields
- Import from local file works
- Import from URL works (HTTP GET)
- Verification re-runs backtest and flags discrepancies
