# Spec: Data Source Fallback Chains (#184)

## Problem

If the data broker (Fyers) token expires or returns nothing, several core
features fail hard:

- Options chain → `get_data_broker().get_options_chain()` raises, entire
  options analysis aborts
- Holdings / positions → no fallback, portfolio view dies
- No visibility into which data source is currently active

Quotes and OHLCV history already have yfinance fallbacks. This spec closes
the remaining gaps and adds source-visibility across the board.

## Current state

| Data type       | Tier 1        | Tier 2    | Tier 3 |
|----------------|---------------|-----------|--------|
| Quotes          | Broker REST   | yfinance  | —      |
| OHLCV history   | Broker REST   | yfinance  | —      |
| Options chain   | Broker REST   | **none**  | —      |
| Holdings        | Broker REST   | **none**  | —      |
| Positions       | Broker REST   | **none**  | —      |

## Proposal

### Tier additions

| Data type       | Tier 1      | Tier 2    | Tier 3          |
|----------------|-------------|-----------|-----------------|
| Quotes          | Broker REST | yfinance  | NSE scraper     |
| OHLCV history   | Broker REST | yfinance  | local disk cache|
| Options chain   | Broker REST | NSE scraper | —             |
| Holdings        | Broker REST | disk cache  | —             |
| Positions       | Broker REST | disk cache  | —             |

### Source visibility

Every public data function returns data from the best available source and
records which source was used in a module-level registry:

```python
# market/source_tracker.py
get_last_source(data_type: str) -> str
# returns: "broker", "yfinance", "nse_scraper", "disk_cache", "none"
```

A warning is printed to console whenever the app falls back:

```
⚠ Options chain: Fyers failed (token expired) — using NSE scraper (delayed)
⚠ Holdings: broker unavailable — using cached data from 14 min ago
```

---

## Architecture

### New file: `market/nse_scraper.py`

NSE public API — no auth required, free, available during market hours.

```
GET https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY
GET https://www.nseindia.com/api/option-chain-equities?symbol=RELIANCE
```

Requires a browser-like session (cookies from homepage). Returns
`list[OptionsContract]` in the same schema as broker-sourced chains.

```python
def nse_get_options_chain(underlying: str, expiry: str | None = None) -> list[OptionsContract]
def nse_available() -> bool   # checks network + NSE reachability
```

Index underlyings (NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY) → indices endpoint.
Stock underlyings → equities endpoint.

### New file: `market/source_tracker.py`

Lightweight registry for tracking and printing which source served each request.

```python
_last_source: dict[str, str] = {}   # data_type → source name

def record_source(data_type: str, source: str) -> None
def get_last_source(data_type: str) -> str
def warn_fallback(data_type: str, reason: str, source: str) -> None
```

`warn_fallback` prints to console with `[yellow]⚠[/yellow]` styling via Rich.

### Modified: `market/options.py`

`get_options_chain()` becomes a two-tier function:

```python
def get_options_chain(underlying, expiry=None):
    # Tier 1: broker
    try:
        chain = get_data_broker().get_options_chain(underlying, expiry)
        record_source("options", "broker")
        return chain
    except Exception as e:
        warn_fallback("options", str(e), "nse_scraper")

    # Tier 2: NSE scraper
    return nse_get_options_chain(underlying, expiry)
```

### Modified: `engine/portfolio.py`

`get_holdings()` and `get_positions()` gain disk cache:

```python
CACHE_DIR = Path.home() / ".trading_platform" / "cache"

def _cache_path(kind: str) -> Path:
    return CACHE_DIR / f"{kind}.json"

def _save_cache(kind: str, data: list) -> None: ...
def _load_cache(kind: str) -> tuple[list, datetime | None]: ...
    # returns (data, cached_at) — cached_at is None if no cache
```

On successful broker fetch → save to cache.
On broker failure → load cache, print staleness warning.

### Modified: `market/history.py`

Already has broker → yfinance chain. Add tier 3: local OHLCV cache.

On successful yfinance fetch of daily data → save last N rows to
`~/.trading_platform/cache/ohlcv_{symbol}.json`.
On all upstream failure → load from disk cache.

---

## Acceptance Criteria

- [ ] `market/nse_scraper.py` fetches options chain from NSE public API
- [ ] `nse_available()` returns False gracefully when network is unreachable
- [ ] `market/options.py` falls back to NSE scraper when broker raises
- [ ] `engine/portfolio.py` saves holdings/positions to disk on success
- [ ] `engine/portfolio.py` loads cached holdings/positions with staleness warning
- [ ] `market/source_tracker.py` records which source served each request
- [ ] Warning printed on console whenever a fallback is used
- [ ] All fallbacks are silent (no crash) when both primary and fallback fail
- [ ] Full test coverage — each fallback tier tested in isolation

## Files

| File | Change |
|------|--------|
| `market/nse_scraper.py` | New — NSE options chain + quote scraper |
| `market/source_tracker.py` | New — source registry + fallback warnings |
| `market/options.py` | Add NSE scraper fallback in `get_options_chain` |
| `engine/portfolio.py` | Add disk cache for holdings/positions |
| `market/history.py` | Add disk cache tier 3 for daily OHLCV |
| `tests/test_data_fallback.py` | New — full fallback chain tests |
