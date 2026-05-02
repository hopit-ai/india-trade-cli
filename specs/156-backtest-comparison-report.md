# Spec: Backtest Comparison HTML Reports (#156)

## Problem
The backtester runs one strategy at a time and outputs text. No side-by-side comparison or shareable report.

## Solution

### engine/backtest_report.py — new module

`generate_html_report(results: list[BacktestResult], output_path: str | None = None) -> str`

- Accepts one or more `BacktestResult` objects from `engine/backtest.py`
- Generates a self-contained HTML file (no external server dependency)
- Embeds Chart.js from CDN for equity curve overlays
- Returns the absolute path to the saved file
- Default output: `~/Desktop/backtest_{symbol}_{date}.html`

### Report sections
1. **Strategy ranking table** — columns: Strategy, Return%, CAGR, Sharpe, Max DD, Win Rate, Profit Factor, Trades
2. **Equity curve chart** — all strategies overlaid on one chart (Chart.js line chart)
3. **Benchmark row** — Buy & Hold return shown in every table and chart
4. **Individual strategy detail** — expandable section per strategy with full stats

### CLI integration
`backtest RELIANCE rsi macd --compare --html`

The `--compare` flag runs all specified strategies; `--html` generates the report.

### Web endpoint
`POST /skills/backtest_report` — accepts `{symbol, strategies, period}`, returns HTML URL or inline HTML.

## Files
- `engine/backtest_report.py` — HTML generation
- `app/repl.py` — wire `--compare --html` to new module
- `web/skills.py` — `POST /skills/backtest_report` endpoint

## Acceptance Criteria
- `generate_html_report([result1, result2])` produces a valid HTML file
- HTML contains "Strategy", each strategy name, and equity curve data
- Works with a single strategy (no comparison needed)
- File is saved to Desktop with timestamped filename
