"""
engine/search.py
────────────────
FTS5 full-text search across past analyses stored in trade memory (#183).

Uses SQLite's built-in FTS5 extension to index synthesis text, strategy names,
symbols, and verdict information. Enables fast free-text queries like:

    search "bullish MACD RELIANCE"
    search verdict:BUY
    search "iron condor"

The index is stored alongside the trade memory file in:
    ~/.trading_platform/analysis_search.db

Data is synced from trade_memory on demand (lazy, no background threads).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SEARCH_DB = Path.home() / ".trading_platform" / "analysis_search.db"


@dataclass
class SearchResult:
    """A single search hit."""

    record_id: str
    symbol: str
    timestamp: str
    verdict: str
    confidence: int
    strategy: str
    snippet: str  # matched text excerpt


class AnalysisSearch:
    """
    SQLite FTS5 search index for past analysis records.

    Lazily initialised — database and table are created on first use.
    Call `index_records(records)` to populate (or refresh) the index.
    Call `search(query)` to find matching analyses.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or SEARCH_DB
        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection ────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Create FTS5 virtual table and metadata table if they don't exist."""
        conn = self._conn
        assert conn is not None

        # Metadata table stores structured fields (for display)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                record_id  TEXT PRIMARY KEY,
                symbol     TEXT NOT NULL,
                timestamp  TEXT NOT NULL,
                verdict    TEXT NOT NULL,
                confidence INTEGER NOT NULL DEFAULT 0,
                strategy   TEXT NOT NULL DEFAULT '',
                full_text  TEXT NOT NULL DEFAULT ''
            )
        """)

        # FTS5 virtual table — content=analyses
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS analyses_fts
            USING fts5(
                record_id UNINDEXED,
                symbol,
                verdict,
                strategy,
                full_text,
                content='analyses',
                content_rowid='rowid'
            )
        """)

        # Keep FTS in sync via triggers
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS analyses_ai
            AFTER INSERT ON analyses BEGIN
                INSERT INTO analyses_fts(rowid, record_id, symbol, verdict, strategy, full_text)
                VALUES (new.rowid, new.record_id, new.symbol, new.verdict, new.strategy, new.full_text);
            END;

            CREATE TRIGGER IF NOT EXISTS analyses_ad
            AFTER DELETE ON analyses BEGIN
                INSERT INTO analyses_fts(analyses_fts, rowid, record_id, symbol, verdict, strategy, full_text)
                VALUES ('delete', old.rowid, old.record_id, old.symbol, old.verdict, old.strategy, old.full_text);
            END;

            CREATE TRIGGER IF NOT EXISTS analyses_au
            AFTER UPDATE ON analyses BEGIN
                INSERT INTO analyses_fts(analyses_fts, rowid, record_id, symbol, verdict, strategy, full_text)
                VALUES ('delete', old.rowid, old.record_id, old.symbol, old.verdict, old.strategy, old.full_text);
                INSERT INTO analyses_fts(rowid, record_id, symbol, verdict, strategy, full_text)
                VALUES (new.rowid, new.record_id, new.symbol, new.verdict, new.strategy, new.full_text);
            END;
        """)
        conn.commit()

    # ── Indexing ──────────────────────────────────────────────

    def index_records(self, records: list) -> int:
        """
        Index (or re-index) a list of TradeRecord objects.

        Existing records with the same ID are replaced (upsert).
        Returns the count of records indexed.
        """
        conn = self._get_conn()
        count = 0
        for r in records:
            record_id = getattr(r, "id", "")
            if not record_id:
                continue

            symbol = getattr(r, "symbol", "")
            timestamp = getattr(r, "timestamp", "")
            verdict = getattr(r, "verdict", "")
            confidence = getattr(r, "confidence", 0)
            strategy = getattr(r, "strategy", "")
            synthesis = getattr(r, "synthesis_text", "")
            bull = getattr(r, "bull_summary", "")
            bear = getattr(r, "bear_summary", "")
            lesson = getattr(r, "lesson", "")

            # Build searchable full_text blob
            full_text = " ".join(
                filter(None, [symbol, verdict, strategy, synthesis, bull, bear, lesson])
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO analyses
                (record_id, symbol, timestamp, verdict, confidence, strategy, full_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, symbol, timestamp, verdict, confidence, strategy, full_text),
            )
            count += 1

        conn.commit()
        return count

    def index_from_memory(self) -> int:
        """Convenience: load from the singleton trade_memory and index all records."""
        from engine.memory import trade_memory

        return self.index_records(trade_memory._records)

    # ── Search ────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """
        Full-text search across all indexed analyses.

        Supports standard FTS5 query syntax:
          - plain terms:       "bullish MACD"
          - quoted phrases:    '"iron condor"'
          - column filters:    "verdict:BUY"
          - prefix matching:   "RELIAN*"

        Returns a list of SearchResult sorted by relevance (BM25).
        """
        conn = self._get_conn()

        # Auto-build a snippet if the synthesis is long
        try:
            rows = conn.execute(
                """
                SELECT
                    a.record_id,
                    a.symbol,
                    a.timestamp,
                    a.verdict,
                    a.confidence,
                    a.strategy,
                    snippet(analyses_fts, 4, '[', ']', '...', 15) AS snip
                FROM analyses_fts
                JOIN analyses a ON a.rowid = analyses_fts.rowid
                WHERE analyses_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 query syntax error — fall back to LIKE scan
            like_q = f"%{query}%"
            rows = conn.execute(
                """
                SELECT record_id, symbol, timestamp, verdict, confidence, strategy,
                       substr(full_text, 1, 100) AS snip
                FROM analyses
                WHERE full_text LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (like_q, limit),
            ).fetchall()

        return [
            SearchResult(
                record_id=row["record_id"],
                symbol=row["symbol"],
                timestamp=row["timestamp"][:10],
                verdict=row["verdict"],
                confidence=row["confidence"],
                strategy=row["strategy"],
                snippet=row["snip"],
            )
            for row in rows
        ]

    def count(self) -> int:
        """Return the number of indexed records."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def clear(self) -> None:
        """Remove all indexed records."""
        conn = self._get_conn()
        conn.execute("DELETE FROM analyses")
        conn.commit()


# ── Rich printer ──────────────────────────────────────────────


def print_search_results(results: list[SearchResult], query: str) -> None:
    """Display search results as a Rich table."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not results:
        console.print(f"[dim]No results for: {query!r}[/dim]")
        return

    table = Table(
        title=f"Search: {query!r}  ({len(results)} results)",
        show_lines=False,
    )
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Date", style="dim", width=12)
    table.add_column("Symbol", style="bold", width=12)
    table.add_column("Verdict", width=12)
    table.add_column("Conf", justify="right", width=6)
    table.add_column("Strategy", width=20)
    table.add_column("Excerpt", width=40)

    for r in results:
        v_style = {
            "STRONG_BUY": "bold green",
            "BUY": "green",
            "HOLD": "yellow",
            "SELL": "red",
            "STRONG_SELL": "bold red",
        }.get(r.verdict, "white")

        table.add_row(
            r.record_id,
            r.timestamp,
            r.symbol,
            f"[{v_style}]{r.verdict}[/{v_style}]",
            f"{r.confidence}%",
            r.strategy[:20] if r.strategy else "-",
            r.snippet[:40] if r.snippet else "-",
        )

    console.print(table)


# ── Singleton ─────────────────────────────────────────────────

analysis_search = AnalysisSearch()
