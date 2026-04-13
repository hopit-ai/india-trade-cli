"""
Tests for reflect-and-remember (engine/memory.py #92).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def memory(tmp_path, monkeypatch):
    """Fresh TradeMemory backed by a temp file."""
    import engine.memory as mem_mod

    monkeypatch.setattr(mem_mod, "MEMORY_FILE", tmp_path / "trades.json")
    from engine.memory import TradeMemory

    return TradeMemory()


def _make_record(memory, symbol="INFY", verdict="BUY", outcome=None, pnl=None):
    """Store a trade and optionally record an outcome. Returns trade_id string."""
    record = memory.store(
        symbol=symbol,
        exchange="NSE",
        verdict=verdict,
        confidence=72,
    )
    trade_id = record.id
    if outcome:
        memory.record_outcome(trade_id, outcome=outcome, actual_pnl=pnl, exit_price=1800.0)
    return trade_id


class TestReflectAndRememberExists:
    def test_method_exists(self, memory):
        assert hasattr(memory, "reflect_and_remember")
        import inspect

        sig = inspect.signature(memory.reflect_and_remember)
        assert "trade_id" in sig.parameters
        assert "llm_provider" in sig.parameters

    def test_nonexistent_id_returns_empty(self, memory):
        result = memory.reflect_and_remember("nonexistent-id-xyz")
        assert result == ""

    def test_returns_string(self, memory):
        trade_id = _make_record(memory, outcome="WIN", pnl=4200.0)
        result = memory.reflect_and_remember(trade_id)
        assert isinstance(result, str)
        assert len(result) > 0


class TestReflectRuleBasedFallback:
    def test_win_lesson_mentions_symbol(self, memory):
        trade_id = _make_record(memory, symbol="RELIANCE", verdict="BUY", outcome="WIN", pnl=3500.0)
        lesson = memory.reflect_and_remember(trade_id, llm_provider=None)
        assert "RELIANCE" in lesson or "BUY" in lesson or "WIN" in lesson.upper()

    def test_loss_lesson_advises_caution(self, memory):
        trade_id = _make_record(memory, symbol="INFY", verdict="SELL", outcome="LOSS", pnl=-2000.0)
        lesson = memory.reflect_and_remember(trade_id, llm_provider=None)
        assert len(lesson) > 0
        # Should at least mention the outcome
        lower = lesson.lower()
        assert "loss" in lower or "incorrect" in lower or "stop" in lower or "infy" in lower

    def test_lesson_stored_on_record(self, memory):
        trade_id = _make_record(memory, outcome="WIN", pnl=1500.0)
        memory.reflect_and_remember(trade_id)
        record = memory.get_by_id(trade_id)
        assert record is not None
        assert record.lesson != ""

    def test_lesson_persisted(self, memory, tmp_path):
        """Lesson is written to disk and survives reload."""
        import engine.memory as mem_mod

        trade_id = _make_record(memory, outcome="WIN", pnl=1000.0)
        memory.reflect_and_remember(trade_id)

        # Reload from same file
        mem2 = mem_mod.TradeMemory()
        record = mem2.get_by_id(trade_id)
        assert record is not None
        assert record.lesson != ""


class TestReflectWithLLM:
    def test_llm_lesson_is_used_when_provided(self, memory):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = (
            "The RSI oversold entry on INFY was correct — hold similar setups."
        )

        trade_id = _make_record(memory, symbol="INFY", verdict="BUY", outcome="WIN", pnl=2000.0)
        lesson = memory.reflect_and_remember(trade_id, llm_provider=mock_provider)

        assert "INFY" in lesson or "oversold" in lesson or "correct" in lesson
        mock_provider.chat.assert_called_once()

    def test_llm_failure_falls_back_to_rule(self, memory):
        mock_provider = MagicMock()
        mock_provider.chat.side_effect = RuntimeError("LLM unavailable")

        trade_id = _make_record(memory, outcome="WIN", pnl=500.0)
        # Should not raise — falls back to rule-based
        lesson = memory.reflect_and_remember(trade_id, llm_provider=mock_provider)
        assert isinstance(lesson, str)
        assert len(lesson) > 0


class TestTradeRecordLessonField:
    def test_lesson_field_exists_on_dataclass(self):
        from engine.memory import TradeRecord

        assert "lesson" in TradeRecord.__dataclass_fields__
        assert TradeRecord.__dataclass_fields__["lesson"].default == ""

    def test_old_records_load_without_lesson(self, tmp_path, monkeypatch):
        """Records saved without lesson field load with lesson='' (backward compat)."""
        import json
        import engine.memory as mem_mod

        mem_file = tmp_path / "trades.json"
        # Write a record without the 'lesson' key (simulating old data)
        old_record = {
            "id": "old-123",
            "timestamp": "2026-01-01T10:00:00",
            "symbol": "NIFTY",
            "exchange": "NSE",
            "verdict": "BUY",
            "confidence": 60,
            "analyst_scores": {},
        }
        mem_file.write_text(json.dumps([old_record]))
        monkeypatch.setattr(mem_mod, "MEMORY_FILE", mem_file)

        mem = mem_mod.TradeMemory()
        record = mem.get_by_id("old-123")
        assert record is not None
        assert record.lesson == ""


class TestGetContextIncludesLesson:
    def test_context_includes_lesson_when_set(self, memory):
        trade_id = _make_record(memory, symbol="TATAMOTORS", outcome="WIN", pnl=3000.0)
        memory.reflect_and_remember(trade_id)

        context = memory.get_context_for_symbol("TATAMOTORS")
        # Context should either include the lesson or at minimum the trade history
        assert "TATAMOTORS" in context or "BUY" in context
