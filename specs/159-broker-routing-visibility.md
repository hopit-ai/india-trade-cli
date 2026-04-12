# Spec: Broker Routing Visibility + CLI Commands (#159)

## Problem
Dual-broker mode works but users can't see or control which broker
handles data vs execution.

---

## CLI Changes

### Enhanced `brokers` command (`brokers/session.py` → `list_connected_brokers()`)

Current output: just lists broker names.
New output:
```
CONNECTED BROKERS
  🟢 Fyers          DATA        live quotes, options chain, GEX, IV
  🟢 Zerodha        EXECUTION   orders, holdings, positions, funds

  Data broker:      Fyers
  Execution broker: Zerodha
```

If no brokers connected: `No brokers connected. Run 'login' to connect.`

### New `data-broker <name>` command (`app/repl.py`)

```python
elif command == "data-broker":
    name = args[0] if args else None
    # 1. If broker not connected, trigger login
    # 2. Set role via set_broker_role(name, "data")
    # 3. Print confirmation
```

### New `exec-broker <name>` command (`app/repl.py`)

Same pattern, sets role to "execution".

### Auto-login flow

```python
def _ensure_broker_connected(key: str) -> bool:
    """If broker not in _brokers, trigger login. Returns True if connected."""
    all_brokers = get_all_brokers()
    if key not in all_brokers:
        console.print(f"[dim]{key} not connected — starting login…[/dim]")
        login(key)
    return key in get_all_brokers()
```

---

## Frontend Changes

### Input bar routing indicator (`InputBar.jsx`)

Below the input field, add a compact line showing current routing:
```
Data: Fyers · Exec: Zerodha
```

Read from `brokerStatuses` in chatStore — filter authenticated brokers
and show their roles.

Only shown when 2+ brokers are connected (skip for single broker).

---

## Backend Changes

None — `set_broker_role()`, `get_broker_role()`, `get_data_broker()`,
`get_execution_broker()` already exist from #129.

---

## Files Modified

| File | Change |
|------|--------|
| `brokers/session.py` | Enhance `list_connected_brokers()` to show roles |
| `app/repl.py` | Add `data-broker` and `exec-broker` commands |
| `macos-app/.../Input/InputBar.jsx` | Add routing indicator |

## Tests

| Test | What |
|------|------|
| `test_list_brokers_shows_roles` | Verify role labels in output |
| `test_data_broker_command_sets_role` | Verify set_broker_role called |
| `test_exec_broker_command_sets_role` | Same for execution |
