# Spec: Hard Risk Limits (#154)

## Problem
Risk Manager analyst provides recommendations but LLM can override them in synthesis.
No programmatic guardrails prevent catastrophic losses.

## Proposal
Non-overridable risk limits enforced in code before every order placement.

## Limits

| Limit | Default | Env Var |
|-------|---------|---------|
| Daily loss cap | -₹20,000 | `MAX_DAILY_LOSS` |
| Max trades per day | 20 | `MAX_DAILY_TRADES` |
| Max trades per symbol per day | 5 | `MAX_TRADES_PER_SYMBOL` |
| Max position size | 20% of capital | `MAX_POSITION_PCT` (already in #157) |
| No pyramiding | Cannot add to losing position | Always on |
| Auto square-off | 15:15 IST | `AUTO_SQUAREOFF_TIME` |

## Architecture

### New file: `engine/risk_limits.py`
```python
class RiskLimits:
    def check(self, symbol, action, quantity, price, broker) -> None:
        """Raises RiskLimitError if any limit is breached."""
    def record_trade(self, symbol, action, quantity, price, pnl=0.0) -> None:
        """Record a completed trade for daily tracking."""
    def get_status(self) -> dict:
        """Return current risk usage: daily_loss, trades_today, etc."""
```

### Storage
- SQLite at `~/.trading_platform/risk_limits.db`
- Daily P&L and trade counts persist across restarts
- Auto-reset at midnight / market open

### Integration
- `engine/trade_executor.py` — call `risk_limits.check()` before `broker.place_order()`
- `web/api.py` — `GET /api/risk/status` endpoint

### Pyramiding check
- Fetch current positions from broker
- If trade is BUY for a symbol already held at a HIGHER average price → block

### Error format
```
RiskLimitError: Order blocked — daily loss cap reached (-₹18,500 of -₹20,000 limit).
  Today's trades: 12/20
  P&L today: -₹18,500
  Remaining room: -₹1,500
```

## Files
- `engine/risk_limits.py` — new: RiskLimits class + RiskLimitError
- `engine/trade_executor.py` — call check() before place_order
- `web/api.py` — GET /api/risk/status
- `tests/test_risk_limits.py` — unit tests

## Acceptance Criteria
- Placing an order when daily_loss < -MAX_DAILY_LOSS → RiskLimitError raised
- Placing 21st trade when MAX_DAILY_TRADES=20 → RiskLimitError raised  
- Placing 6th trade on same symbol when MAX_TRADES_PER_SYMBOL=5 → RiskLimitError raised
- Pyramiding into a losing equity position → RiskLimitError raised
- Limits cannot be bypassed by any code path (no skip parameter)
- All limits configurable via env vars
- Status readable at any time via get_status()
