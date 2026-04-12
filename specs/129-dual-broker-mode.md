# Spec: Dual-Broker Mode (#129)

## Problem
App supports one active broker at a time. Optimal setup needs Fyers (data) +
Zerodha (execution) simultaneously with role-based routing.

## Goal
Add role-based broker routing so market data flows through the DATA broker
and orders flow through the EXECUTION broker. Auto-assign roles when both
Fyers and Zerodha are connected.

---

## Role Model

| Role | Purpose | Default broker |
|------|---------|----------------|
| `data` | Quotes, options chain, historical, GEX, IV | Fyers |
| `execution` | Orders, holdings, positions, funds | Zerodha |
| `both` | Everything (single-broker mode) | Any |

---

## Backend Changes

### `brokers/session.py` — Role registry

**New state:**
```python
_broker_roles: dict[str, str] = {}  # key -> "data" | "execution" | "both"
```

**New functions:**
```python
def set_broker_role(key: str, role: str) -> None
    # role must be "data", "execution", or "both"
    # Validates key exists in _brokers

def get_broker_role(key: str) -> str
    # Returns role for broker, defaults to "both"

def get_data_broker() -> BrokerAPI
    # 1. Find broker with role="data"
    # 2. Fallback: broker with role="both"
    # 3. Fallback: primary broker (get_broker())

def get_execution_broker() -> BrokerAPI
    # Same logic but for role="execution"
```

**Modified `register_broker()`:**
- Accept optional `role` param
- Auto-assign: fyers → "data", zerodha → "execution" (when both present)

**Modified `unregister_broker()`:**
- Remove from `_broker_roles` too

### `market/quotes.py` — Data routing

Line ~86: `get_broker()` → `get_data_broker()`

Import change: `from brokers.session import get_data_broker`

### `market/options.py` — Data routing

Same change: `get_broker()` → `get_data_broker()` for options chain fetching.

### `engine/trade_executor.py` — Execution routing

If it calls `get_broker()` internally for placing orders, change to `get_execution_broker()`.
If it receives broker as a parameter, no change needed — caller passes the right one.

### `web/api.py` — API endpoints

**Modified `GET /api/status`:**
```json
{
  "fyers": { "configured": true, "authenticated": true, "role": "data" },
  "zerodha": { "configured": true, "authenticated": true, "role": "execution" }
}
```

**New `POST /api/broker/role`:**
```json
// Request
{ "broker": "fyers", "role": "data" }
// Response
{ "status": "ok" }
```

**Modified `_auto_restore_brokers()`:**
After restoring all brokers, auto-assign roles:
- If fyers + zerodha both authenticated → fyers=data, zerodha=execution
- If only one broker → role=both

---

## Frontend Changes

### `BrokerPanel.jsx`
- Show role badge (DATA / EXECUTION / BOTH) next to each authenticated broker
- Read role from `/api/status` response (already polled every 8s)

### `Sidebar/index.jsx`
- Broker status section shows all connected brokers with roles
- e.g. "🟢 Fyers (data) · 🟢 Zerodha (execution)"

---

## Edge Cases

1. **Single broker**: role = "both" — all routing goes through primary (no change)
2. **Data broker disconnected**: `get_data_broker()` falls back to primary
3. **Role changed at runtime**: `POST /api/broker/role` updates immediately
4. **Three brokers**: only two roles exist, third gets "both" or unassigned
