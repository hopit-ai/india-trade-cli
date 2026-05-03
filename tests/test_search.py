"""
Tests for FTS5 full-text search across past analyses (#183).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def search_db(tmp_path):
    """AnalysisSearch backed by a temp database."""
    from engine.search import AnalysisSearch

    return AnalysisSearch(db_path=tmp_path / "test_search.db")


def _make_record(record_id, symbol, verdict, strategy="", synthesis_text=""):
    """Create a minimal TradeRecord-like stub."""

    class FakeRecord:
        pass

    r = FakeRecord()
    r.id = record_id
    r.symbol = symbol
    r.timestamp = "2026-04-01T10:00:00"
    r.verdict = verdict
    r.confidence = 70
    r.strategy = strategy
    r.synthesis_text = synthesis_text
    r.bull_summary = ""
    r.bear_summary = ""
    r.lesson = ""
    return r


class TestAnalysisSearchIndexing:
    def test_index_records_returns_count(self, search_db):
        records = [
            _make_record("abc1", "INFY", "BUY"),
            _make_record("abc2", "TCS", "SELL"),
        ]
        count = search_db.index_records(records)
        assert count == 2

    def test_count_after_indexing(self, search_db):
        records = [
            _make_record("r1", "INFY", "BUY"),
            _make_record("r2", "RELIANCE", "HOLD"),
            _make_record("r3", "TCS", "SELL"),
        ]
        search_db.index_records(records)
        assert search_db.count() == 3

    def test_upsert_does_not_duplicate(self, search_db):
        r = _make_record("dup1", "HDFC", "BUY")
        search_db.index_records([r])
        search_db.index_records([r])  # index same record again
        assert search_db.count() == 1

    def test_empty_list_indexes_zero(self, search_db):
        count = search_db.index_records([])
        assert count == 0

    def test_records_without_id_skipped(self, search_db):
        r = _make_record("", "WIPRO", "BUY")
        count = search_db.index_records([r])
        assert count == 0


class TestAnalysisSearchQuery:
    def test_search_by_symbol(self, search_db):
        records = [
            _make_record("s1", "INFY", "BUY", synthesis_text="Strong uptrend in INFY"),
            _make_record("s2", "TCS", "SELL", synthesis_text="TCS bearish momentum"),
        ]
        search_db.index_records(records)
        results = search_db.search("INFY")
        assert len(results) >= 1
        assert any(r.symbol == "INFY" for r in results)

    def test_search_by_verdict(self, search_db):
        records = [
            _make_record("v1", "RELIANCE", "STRONG_BUY", synthesis_text="Strong bullish"),
            _make_record("v2", "WIPRO", "SELL", synthesis_text="Bearish setup"),
        ]
        search_db.index_records(records)
        results = search_db.search("STRONG_BUY")
        assert len(results) >= 1
        assert any(r.verdict == "STRONG_BUY" for r in results)

    def test_search_by_strategy_name(self, search_db):
        records = [
            _make_record(
                "st1", "NIFTY", "BUY", strategy="Iron Condor", synthesis_text="Condor spread setup"
            ),
            _make_record(
                "st2",
                "BANKNIFTY",
                "HOLD",
                strategy="Bull Call Spread",
                synthesis_text="Mild uptrend",
            ),
        ]
        search_db.index_records(records)
        results = search_db.search("Iron")
        assert len(results) >= 1
        assert any("Iron" in r.strategy for r in results)

    def test_search_synthesis_text(self, search_db):
        records = [
            _make_record(
                "tx1", "INFY", "BUY", synthesis_text="MACD crossover bullish signal confirmed"
            ),
            _make_record("tx2", "TCS", "HOLD", synthesis_text="RSI neutral zone no signal"),
        ]
        search_db.index_records(records)
        results = search_db.search("MACD crossover")
        assert len(results) >= 1

    def test_search_returns_empty_for_no_match(self, search_db):
        records = [_make_record("nm1", "INFY", "BUY", synthesis_text="Normal analysis")]
        search_db.index_records(records)
        results = search_db.search("xyzzy_nonexistent_term_12345")
        assert results == []

    def test_search_result_has_snippet(self, search_db):
        records = [
            _make_record(
                "sn1",
                "HDFC",
                "BUY",
                synthesis_text="HDFC shows strong momentum with RSI above 60 and MACD positive",
            )
        ]
        search_db.index_records(records)
        results = search_db.search("HDFC")
        assert len(results) >= 1
        assert isinstance(results[0].snippet, str)

    def test_search_result_fields_populated(self, search_db):
        records = [_make_record("fld1", "BAJFINANCE", "BUY", strategy="Delivery Buy")]
        search_db.index_records(records)
        results = search_db.search("BAJFINANCE")
        assert len(results) == 1
        r = results[0]
        assert r.record_id == "fld1"
        assert r.symbol == "BAJFINANCE"
        assert r.verdict == "BUY"
        assert r.strategy == "Delivery Buy"

    def test_search_with_limit(self, search_db):
        records = [
            _make_record(f"lim{i}", "NIFTY", "BUY", synthesis_text="bullish setup")
            for i in range(10)
        ]
        search_db.index_records(records)
        results = search_db.search("bullish", limit=3)
        assert len(results) <= 3

    def test_malformed_query_falls_back_gracefully(self, search_db):
        records = [_make_record("mf1", "INFY", "BUY", synthesis_text="BUY signal")]
        search_db.index_records(records)
        # FTS5 special chars that might fail — should not raise
        try:
            search_db.search("BUY OR")
        except Exception:
            pytest.fail("search() raised an exception on malformed query")


class TestAnalysisSearchClear:
    def test_clear_removes_all_records(self, search_db):
        records = [
            _make_record("cl1", "INFY", "BUY"),
            _make_record("cl2", "TCS", "SELL"),
        ]
        search_db.index_records(records)
        search_db.clear()
        assert search_db.count() == 0

    def test_search_after_clear_returns_empty(self, search_db):
        records = [_make_record("cl3", "WIPRO", "HOLD", synthesis_text="Hold for now")]
        search_db.index_records(records)
        search_db.clear()
        results = search_db.search("WIPRO")
        assert results == []


class TestPrintSearchResults:
    def test_prints_without_error(self, capsys):
        from engine.search import SearchResult, print_search_results

        results = [
            SearchResult(
                record_id="abc1",
                symbol="INFY",
                timestamp="2026-04-01",
                verdict="BUY",
                confidence=72,
                strategy="Delivery Buy",
                snippet="...strong MACD signal...",
            )
        ]
        # Should not raise
        print_search_results(results, "INFY")

    def test_prints_no_results_message(self, capsys):
        from engine.search import print_search_results

        print_search_results([], "xyz")
        # No exception raised = pass
