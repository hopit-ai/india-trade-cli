# Spec: Vectorized Backtesting Mode (#158)

## Problem
Event-driven backtesting takes 10-30s per run. Iterating on signal ideas requires instant feedback.

## Solution

### engine/backtest_vectorized.py — new module

`run_vectorized_backtest(symbol, strategy_name, period, exchange) -> BacktestResult`

- Uses pandas vectorized operations — no bar-by-bar loop
- Computes signals for the full series in one pass
- Calculates equity curve, Sharpe, max drawdown, win rate as array ops
- Returns the same `BacktestResult` dataclass as event-driven engine
- Target: <1 second for 1-year daily data

### Strategy signal implementations (vectorized)
- **RSI**: buy when RSI crosses above 30, sell when crosses below 70
- **MACD**: buy when MACD line crosses above signal line, sell on reverse
- **Bollinger**: buy when price crosses above lower band, sell on upper
- **MA Cross**: buy when fast MA crosses above slow MA, sell on reverse
- **Momentum**: buy top decile 1-month return, hold 1 month

### Metrics computed
- Total return, CAGR, Sharpe ratio, Sortino ratio, max drawdown
- Win rate, profit factor, total trades
- Buy-and-hold benchmark

### CLI
```
backtest RELIANCE rsi --fast          # vectorized
backtest RELIANCE rsi macd --compare --fast  # compare, vectorized
```

### API
`POST /skills/backtest` with `{"fast": true}` → uses vectorized engine

## Files
- `engine/backtest_vectorized.py` — vectorized engine
- `app/repl.py` — `--fast` flag routes to vectorized
- `web/skills.py` — `fast: bool = False` param on backtest endpoint

## Acceptance Criteria
- `run_vectorized_backtest("INFY", "rsi", "1y")` completes without error when market data available
- Returns `BacktestResult` with same fields as event-driven engine
- Unit-testable without live market data (accepts a pre-built DataFrame)
- `--fast` flag in CLI routes to vectorized engine
