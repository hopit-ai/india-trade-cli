# Spec: FTS5 Full-text Search across Past Analyses (#183)

## Problem
Trade memory grows to hundreds of records but there's no way to search them
beyond simple symbol/verdict filters. Traders want to ask: "Show me all BUY
analyses where I mentioned iron condor" or "Find analyses with VIX > 20".

## Solution
`engine/search.py` — `AnalysisSearch` class backed by SQLite FTS5.

- `index_records(records)` — upserts TradeRecord objects into the FTS index
- `index_from_memory()` — convenience: loads from the trade_memory singleton
- `search(query, limit=20) -> list[SearchResult]` — FTS5 BM25-ranked search
  - Supports plain terms, quoted phrases, column filters (`verdict:BUY`),
    and prefix matching (`RELIAN*`)
  - Falls back to LIKE scan on malformed queries

Database: `~/.trading_platform/analysis_search.db`

### `SearchResult` fields
`record_id`, `symbol`, `timestamp`, `verdict`, `confidence`, `strategy`, `snippet`

### REPL command
`search <query>` — indexes memory on demand, then displays a Rich table.

## Tests
`tests/test_search.py`
