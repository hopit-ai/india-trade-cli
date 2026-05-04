# Spec: Execution Broker Routing (#178)

## Problem

When Fyers (data) + Zerodha (execution) are both connected, the CLI still
routes all operations through the **primary broker** (whichever was connected
first). This means:

- `buy / sell / cancel` place orders via the wrong broker
- `holdings / positions / funds / portfolio` read from the wrong broker
- Alert LTP checks ignore the configured data broker

## Solution

Use `get_data_broker()` and `get_execution_broker()` from `brokers/session.py`
(already exist from #129) at the call sites that were overlooked.

## Routing rules

| Operation | Broker |
|-----------|--------|
| Market quotes, LTP, options chains | `get_data_broker()` |
| Holdings, positions, funds, orders | `get_execution_broker()` |
| Order placement (buy / sell / cancel) | `get_execution_broker()` |
| Account profile | primary (unchanged) |

## Changes

### `app/repl.py`
- `buy` / `sell` commands: resolve broker via `get_execution_broker()` instead
  of the `broker` local variable
- `cancel` command: same

### `engine/portfolio.py`
- `get_portfolio_summary()`, `get_position_greeks()`, `risk_meter()`:
  `get_broker()` → `get_execution_broker()`

### `engine/risk_metrics.py`
- `_get_holdings()`: `get_broker()` → `get_execution_broker()`

### `engine/simulator.py`
- `_load_portfolio()`: `get_broker()` → `get_execution_broker()`

### `engine/alerts.py`
- `_check_conditional_alert()` LTP path: `get_broker()` → `get_data_broker()`
  (already falls back to `market.quotes.get_ltp` which uses `get_data_broker()`)

## Fallback behaviour (single broker)

`get_execution_broker()` and `get_data_broker()` already fall back to the
primary broker when no role is assigned, so single-broker users see no change.
