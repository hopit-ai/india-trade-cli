# Spec: Percentage-Based Position Sizing (#157)

## Problem
Buy/sell commands accept only fixed quantities. No way to say "put 5% of capital into this."

## Proposal
Extend the `buy`/`sell` CLI commands to accept a percentage:

```
buy INFY 5%          → buy (5% of capital / ltp) shares at market
buy INFY 5% 1300     → limit order at ₹1300, quantity = int(capital * 0.05 / 1300)
sell RELIANCE 10%    → sell 10% of capital worth of RELIANCE at market
```

## Core utility function
Add `size_by_pct(symbol, pct, capital, limit_price=None)` to `engine/trade_executor.py`:

```python
def size_by_pct(symbol: str, pct: float, capital: float, limit_price: float | None = None) -> int:
    """
    Compute share quantity from a percentage of capital.

    Args:
        symbol: Stock symbol (used to fetch LTP if no limit_price)
        pct: Percentage of capital (0.0–100.0)
        capital: Total capital in INR (from TRADING_CAPITAL env var or explicit)
        limit_price: If provided, use this as price; else fetch live LTP

    Returns:
        Integer quantity (at least 1 if pct > 0 and capital > 0)
    """
```

## Config
- `TRADING_CAPITAL` env var (INR). Default: 100_000 (₹1 lakh)
- `MAX_POSITION_PCT` env var — cap per-position percentage. Default: 20%
  (Prevents accidentally sizing 100% of capital into one trade)

## CLI syntax rules
- Percentage is detected by trailing `%` on the second argument
- `buy INFY 5%` → market order, quantity = `int(capital * 0.05 / ltp)`
- `buy INFY 5% 1300` → limit at ₹1300, quantity = `int(capital * 0.05 / 1300)`
- Fractional share workaround: minimum quantity is 1; warns if capital too low
- If quantity is 0: print error "Position size too small for ₹X at ₹Y/share"

## Files Changed
- `engine/trade_executor.py` — add `size_by_pct()` function, `get_trading_capital()`
- `app/repl.py` — parse `%` in buy/sell arg[1], call `size_by_pct()` before order
- Help text updated to show percentage syntax

## Tests
- `size_by_pct("INFY", 5.0, 100_000, 1400)` → 3 (floor of 100k * 5% / 1400 = 3.57)
- `size_by_pct("INFY", 5.0, 100_000, 100_000)` → 0 → raises ValueError
- Percentage > MAX_POSITION_PCT → raises ValueError with clear message
- Parse logic: `"5%"` → detected as pct=5.0
- `"500"` → treated as fixed quantity=500 (no change to existing behaviour)
