# Spec: Pine Script Export for Strategies (#185)

## Problem
Traders who use TradingView want to visualise the same strategy logic they built
in india-trade-cli without rewriting it. A one-click Pine Script export removes
that friction.

## Solution
New module `engine/export/pinescript.py` with two public functions:

- `strategy_to_pinescript(name, python_code, metadata) -> str`
  — detects common indicator patterns (MACD, RSI, Bollinger, EMA) and emits
    matching Pine Script v5 logic. Falls back to generic SMA-crossover template.

- `export_backtest_result_to_pinescript(result) -> str`
  — generates Pine Script annotated with backtest metrics (return, Sharpe, win
    rate, drawdown) as a comment block.

New subcommand `strategy export <name> --pine`:
- Loads strategy code and metadata from `strategy_store`
- Calls `strategy_to_pinescript()`
- Writes to `<name>.pine` in the current directory
- Prints a success message with the file path

## Tests
`tests/test_pinescript_export.py`
