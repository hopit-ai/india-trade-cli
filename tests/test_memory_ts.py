"""
Tests for memory analysis_snapshot field (#122).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def temp_memory(tmp_path, monkeypatch):
    """Each test gets an isolated memory file."""
    monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "trade_memory.json")
    import engine.memory as mem_mod

    mem_mod.trade_memory = mem_mod.TradeMemory()
    yield
    mem_mod.trade_memory = mem_mod.TradeMemory()


class TestAnalysisSnapshot:
    def test_store_from_analysis_creates_snapshot(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: BUY\nCONFIDENCE: 75%\nStrategy: Delivery Buy"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="INFY",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
            price=1800.0,
        )
        assert isinstance(record.analysis_snapshot, dict)
        assert len(record.analysis_snapshot) > 0

    def test_snapshot_has_verdict_and_confidence(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm2.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: BUY\nCONFIDENCE: 75%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="TCS",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        snap = record.analysis_snapshot
        assert snap.get("verdict") == "BUY"
        assert snap.get("confidence") == 75

    def test_snapshot_has_price_when_provided(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm3.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: SELL\nCONFIDENCE: 65%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="RELIANCE",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
            price=2950.0,
        )
        assert record.analysis_snapshot.get("price") == 2950.0

    def test_snapshot_price_absent_when_not_provided(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm4.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: HOLD\nCONFIDENCE: 50%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="WIPRO",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        assert "price" not in record.analysis_snapshot

    def test_snapshot_includes_vix(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm5.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        class FakeReport:
            analyst = "Risk Manager"
            score = 50
            data = {"vix": 18.5}

        synthesis = "VERDICT: BUY\nCONFIDENCE: 70%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="HDFC",
            exchange="NSE",
            analyst_reports=[FakeReport()],
            debate=None,
            synthesis=synthesis,
        )
        assert record.analysis_snapshot.get("vix") == 18.5

    def test_snapshot_has_timestamp(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod
        from datetime import datetime

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm6.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: BUY\nCONFIDENCE: 72%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="BAJFINANCE",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        ts = record.analysis_snapshot.get("timestamp")
        assert ts is not None
        # Should parse as ISO datetime
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_direct_store_empty_snapshot_by_default(self):
        from engine.memory import trade_memory

        record = trade_memory.store(symbol="NIFTY", verdict="BUY", confidence=70)
        assert isinstance(record.analysis_snapshot, dict)
        assert record.analysis_snapshot == {}

    def test_direct_store_with_snapshot(self):
        from engine.memory import trade_memory

        snap = {"verdict": "BUY", "confidence": 70, "custom_field": "value"}
        record = trade_memory.store(
            symbol="NIFTY", verdict="BUY", confidence=70, analysis_snapshot=snap
        )
        assert record.analysis_snapshot == snap


class TestContextForSymbolIncludesSnapshot:
    def test_context_includes_price(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "ctx.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: BUY\nCONFIDENCE: 75%"
        mem_mod.trade_memory.store_from_analysis(
            symbol="INFY",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
            price=1800.0,
        )

        context = mem_mod.trade_memory.get_context_for_symbol("INFY")
        assert "1800" in context

    def test_context_includes_analyst_scores_when_present(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "ctx2.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        class FakeReport:
            analyst = "Technical"
            score = 70
            data = {}

        synthesis = "VERDICT: BUY\nCONFIDENCE: 72%"
        mem_mod.trade_memory.store_from_analysis(
            symbol="TCS",
            exchange="NSE",
            analyst_reports=[FakeReport()],
            debate=None,
            synthesis=synthesis,
        )

        context = mem_mod.trade_memory.get_context_for_symbol("TCS")
        assert "Technical" in context
        assert "70" in context
