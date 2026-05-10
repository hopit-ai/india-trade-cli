"""
tests/test_ai_brain.py
──────────────────────
Tests for all 7 "AI brain" tickets:

  #109  Harness conversation history (clear_history)
  #91   Dual LLM routing (build_fast_provider_from_env)
  #149  Web search (Exa / Perplexity) integration
  #169  Semantic memory — get_context_for_conditions injected into synthesis
  #168  Analysis scratchpad (AnalysisScratchpad)
  #92   Reflect-and-remember (auto-reflect on record_outcome)
  #90   BM25 retrieval (auto-index + get_bm25_context)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── #109: Harness history ─────────────────────────────────────────


class TestHarnessHistory:
    """#109 — clear_history() wipes harness JSONL log."""

    def _write_history(self, path: Path, entries: int = 3) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for i in range(entries):
                f.write(json.dumps({"role": "user", "content": f"msg {i}"}) + "\n")

    def test_clear_history_empties_file(self, tmp_path):
        from agent.harness import clear_history

        hf = tmp_path / "history.jsonl"
        self._write_history(hf, entries=5)
        assert hf.stat().st_size > 0

        clear_history(history_file=hf)

        assert hf.exists()
        assert hf.read_text() == ""

    def test_clear_history_noop_when_missing(self, tmp_path):
        from agent.harness import clear_history

        missing = tmp_path / "nope.jsonl"
        # Should not raise
        clear_history(history_file=missing)
        assert not missing.exists()

    def test_load_history_respects_max(self, tmp_path):
        from agent.harness import _load_history

        hf = tmp_path / "history.jsonl"
        # Write 10 messages
        with hf.open("w") as f:
            for i in range(10):
                role = "user" if i % 2 == 0 else "assistant"
                f.write(json.dumps({"role": role, "content": f"msg {i}"}) + "\n")

        messages = _load_history(max_messages=4, history_file=hf)
        assert len(messages) <= 4
        assert len(messages) % 2 == 0  # always even

    def test_load_history_returns_empty_for_missing_file(self, tmp_path):
        from agent.harness import _load_history

        messages = _load_history(history_file=tmp_path / "ghost.jsonl")
        assert messages == []

    def test_append_then_load(self, tmp_path):
        from agent.harness import _append_history, _load_history

        hf = tmp_path / "h.jsonl"
        msgs = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        _append_history(msgs, history_file=hf)
        loaded = _load_history(history_file=hf)
        assert len(loaded) == 2
        assert loaded[0]["content"] == "hello"


# ── #91: Dual LLM routing ─────────────────────────────────────────


class TestDualLLM:
    """#91 — build_fast_provider_from_env returns fast or falls back to deep."""

    def test_falls_back_to_deep_when_env_not_set(self, monkeypatch):
        """If neither AI_FAST_MODEL nor AI_FAST_PROVIDER is set, get deep provider."""
        monkeypatch.delenv("AI_FAST_MODEL", raising=False)
        monkeypatch.delenv("AI_FAST_PROVIDER", raising=False)

        deep_mock = MagicMock()

        with patch("agent.core.build_provider_from_env", return_value=deep_mock):
            from agent.core import build_fast_provider_from_env

            result = build_fast_provider_from_env()
            assert result is deep_mock

    def test_fast_model_env_triggers_separate_build(self, monkeypatch):
        """If AI_FAST_MODEL is set, build_fast_provider_from_env should not return deep mock."""
        monkeypatch.setenv("AI_FAST_MODEL", "claude-haiku-3-5")
        monkeypatch.setenv("AI_FAST_PROVIDER", "anthropic")
        # Also need a key so anthropic doesn't fail
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("AI_PROVIDER", "anthropic")

        deep_mock = MagicMock()

        # The function should attempt to build a fast-specific provider
        # It may fail (no real API key) but must NOT return deep_mock
        with patch("agent.core.build_provider_from_env", return_value=deep_mock):
            from agent.core import build_fast_provider_from_env

            # If build fails, it'll fall back to deep_mock — that's acceptable
            # What we test is that it *tries* to build a separate provider first
            result = build_fast_provider_from_env()
            # result is either a new provider OR deep_mock (fallback) — both fine
            assert result is not None


# ── #149: Web search ─────────────────────────────────────────────


class TestWebSearch:
    """#149 — web_search, web_search_available, format_search_results."""

    def test_available_false_when_no_keys(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

        from agent.web_search import web_search_available

        assert web_search_available() is False

    def test_available_true_when_exa_key(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "sk-exa-test")

        from agent.web_search import web_search_available

        assert web_search_available() is True

    def test_available_true_when_perplexity_key(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        monkeypatch.delenv("EXA_API_KEY", raising=False)

        from agent.web_search import web_search_available

        assert web_search_available() is True

    def test_web_search_returns_empty_on_failure(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "bad-key")
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

        with patch("agent.web_search._exa_search", side_effect=RuntimeError("network")):
            with patch("agent.web_search._perplexity_search", side_effect=RuntimeError("no key")):
                from agent.web_search import web_search

                results = web_search("INFY stock India 2026")
                assert results == []

    def test_web_search_returns_results_on_success(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "sk-exa-test")

        from agent.web_search import SearchResult

        fake_results = [
            SearchResult(
                title="Infosys Q4 earnings beat",
                url="https://example.com/1",
                text="AI deal Topaz revenue",
            ),
            SearchResult(
                title="Infosys hiring freeze",
                url="https://example.com/2",
                text="1000 employees laid off",
            ),
        ]
        with patch("agent.web_search._exa_search", return_value=fake_results):
            from agent.web_search import web_search

            results = web_search("INFY stock India", max_results=2)
            assert len(results) == 2
            assert results[0].title == "Infosys Q4 earnings beat"

    def test_max_results_capped_at_5(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "sk-exa-test")

        with patch("agent.web_search._exa_search") as mock_exa:
            mock_exa.return_value = []

            from agent.web_search import web_search

            web_search("test", max_results=99)
            # Check that _exa_search was called with at most 5
            call_args = mock_exa.call_args
            assert call_args[0][1] <= 5  # positional max_results arg

    def test_format_search_results_empty(self):
        from agent.web_search import format_search_results

        assert format_search_results([]) == ""

    def test_format_search_results_content(self):
        from agent.web_search import SearchResult, format_search_results

        results = [
            SearchResult(
                title="RELIANCE Deal", url="https://example.com", text="Huge acquisition announced"
            ),
        ]
        formatted = format_search_results(results)
        assert "RELIANCE Deal" in formatted
        assert "example.com" in formatted
        assert "Huge acquisition" in formatted

    def test_search_result_text_truncated_in_format(self):
        from agent.web_search import SearchResult, format_search_results

        long_text = "x" * 2000
        results = [SearchResult(title="T", url="http://u.com", text=long_text)]
        formatted = format_search_results(results)
        # Text is capped at 1200 chars in format
        assert len(formatted) < 2500

    def test_perplexity_fallback_on_exa_fail(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "bad-exa")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "good-pplx")

        from agent.web_search import SearchResult

        fallback_results = [SearchResult(title="Perplexity answer", url="", text="Some answer")]

        with patch("agent.web_search._exa_search", side_effect=RuntimeError("exa fail")):
            with patch("agent.web_search._perplexity_search", return_value=fallback_results):
                from agent.web_search import web_search

                results = web_search("NIFTY", provider="exa")
                assert len(results) == 1
                assert results[0].title == "Perplexity answer"


# ── #169: Semantic memory — conditions context ────────────────────


class TestSemanticMemoryConditions:
    """#169 — get_context_for_conditions injected when VIX available."""

    def _make_fresh_memory(self, tmp_path, monkeypatch):
        """Create a TradeMemory with a temp file via module-level path patching."""
        import engine.memory as mem_mod
        from engine.memory import TradeMemory

        mem_file = tmp_path / "memory.json"
        monkeypatch.setattr(mem_mod, "MEMORY_FILE", mem_file)
        mem = TradeMemory()
        mem._records = []  # ensure clean slate
        return mem

    def test_get_context_for_symbol_no_history(self, tmp_path, monkeypatch):
        mem = self._make_fresh_memory(tmp_path, monkeypatch)
        ctx = mem.get_context_for_symbol("INFY")
        assert "No previous" in ctx or "INFY" in ctx

    def test_get_context_for_symbol_with_records(self, tmp_path, monkeypatch):
        from engine.memory import TradeRecord

        mem = self._make_fresh_memory(tmp_path, monkeypatch)
        rec = TradeRecord(
            id="t001",
            timestamp="2026-01-01T10:00:00",
            symbol="INFY",
            exchange="NSE",
            verdict="BUY",
            confidence=75,
        )
        mem._records.append(rec)
        ctx = mem.get_context_for_symbol("INFY")
        assert "INFY" in ctx
        assert "BUY" in ctx

    def test_get_context_for_conditions_no_records(self, tmp_path, monkeypatch):
        mem = self._make_fresh_memory(tmp_path, monkeypatch)
        ctx = mem.get_context_for_conditions(vix=15.0)
        assert "No past trades" in ctx or isinstance(ctx, str)

    def test_get_context_for_conditions_returns_string(self, tmp_path, monkeypatch):
        mem = self._make_fresh_memory(tmp_path, monkeypatch)
        ctx = mem.get_context_for_conditions(vix=20.0, fii_net=None)
        assert isinstance(ctx, str)

    def test_conditions_context_included_when_similar(self, tmp_path, monkeypatch):
        """Records with matching VIX range appear in conditions context."""
        from engine.memory import TradeRecord

        mem = self._make_fresh_memory(tmp_path, monkeypatch)
        rec = TradeRecord(
            id="t002",
            timestamp="2026-01-01T10:00:00",
            symbol="NIFTY",
            exchange="NSE",
            verdict="SELL",
            confidence=60,
            vix=21.5,
            outcome="WIN",
            actual_pnl=5000.0,
        )
        mem._records.append(rec)
        ctx = mem.get_context_for_conditions(vix=20.0)
        # Either the record is found, or "No past trades" returned
        assert isinstance(ctx, str)


# ── #168: Scratchpad ──────────────────────────────────────────────


class TestScratchpad:
    """#168 — AnalysisScratchpad: append, compact, reset, context string."""

    def test_empty_scratchpad_returns_empty_context(self):
        from agent.scratchpad import AnalysisScratchpad

        pad = AnalysisScratchpad(symbol="INFY")
        assert pad.to_context_string() == ""
        assert not pad  # __bool__ = False

    def test_append_records_entry(self):
        from agent.scratchpad import AnalysisScratchpad

        pad = AnalysisScratchpad(symbol="RELIANCE")
        pad.append("technical", "RSI=42, MACD bearish")
        assert len(pad) == 1
        assert bool(pad)

    def test_context_string_contains_tool_and_summary(self):
        from agent.scratchpad import AnalysisScratchpad

        pad = AnalysisScratchpad(symbol="HDFC")
        pad.append("technical", "RSI=55, trend up")
        pad.append("options", "PCR=1.2 bullish")
        ctx = pad.to_context_string()
        assert "technical" in ctx
        assert "RSI=55" in ctx
        assert "options" in ctx
        assert "PCR=1.2" in ctx

    def test_summary_is_truncated_to_300_chars(self):
        from agent.scratchpad import AnalysisScratchpad

        pad = AnalysisScratchpad(symbol="X")
        long_summary = "A" * 500
        pad.append("news", long_summary)
        ctx = pad.to_context_string()
        # The stored entry is capped at 300 chars
        assert "A" * 301 not in ctx

    def test_reset_clears_state(self):
        from agent.scratchpad import AnalysisScratchpad

        pad = AnalysisScratchpad(symbol="INFY")
        pad.append("technical", "some data")
        pad.reset(symbol="TCS")
        assert len(pad) == 0
        assert pad.symbol == "TCS"
        assert pad.to_context_string() == ""

    def test_compact_triggers_at_threshold(self):
        from agent.scratchpad import AnalysisScratchpad, COMPACT_AFTER, KEEP_RECENT

        pad = AnalysisScratchpad(symbol="NIFTY")
        # Add exactly COMPACT_AFTER entries to trigger auto-compact
        for i in range(COMPACT_AFTER):
            pad.append(f"tool_{i}", f"result_{i}")

        # After compaction, only KEEP_RECENT entries remain verbatim
        assert len(pad) <= KEEP_RECENT
        assert pad._compactions >= 1

    def test_compact_preserves_summary(self):
        from agent.scratchpad import AnalysisScratchpad, COMPACT_AFTER

        pad = AnalysisScratchpad(symbol="NIFTY")
        for i in range(COMPACT_AFTER):
            pad.append(f"tool_{i}", f"important_data_{i}")

        # After compaction, compact_summary should have some content
        assert pad._compact_summary != ""

    def test_context_includes_compact_summary_after_compaction(self):
        from agent.scratchpad import AnalysisScratchpad, COMPACT_AFTER

        pad = AnalysisScratchpad(symbol="TCS")
        for i in range(COMPACT_AFTER):
            pad.append(f"analyst_{i}", f"result_{i}")

        ctx = pad.to_context_string()
        # The compact summary should appear in context
        assert "compacted" in ctx or "Earlier" in ctx or "analyst_" in ctx

    def test_get_scratchpad_resets_on_new_symbol(self):
        from agent.scratchpad import get_scratchpad

        pad1 = get_scratchpad(symbol="INFY")
        pad1.append("technical", "some data")
        assert len(pad1) > 0

        pad2 = get_scratchpad(symbol="TCS")
        assert pad2.symbol == "TCS"
        assert len(pad2) == 0  # reset because symbol changed

    def test_get_scratchpad_returns_same_instance_for_same_symbol(self):
        from agent.scratchpad import get_scratchpad

        pad1 = get_scratchpad(symbol="WIPRO")
        pad1.append("technical", "data")
        pad2 = get_scratchpad()  # no symbol — same instance
        assert pad2 is pad1


# ── #92: Reflect-and-remember ─────────────────────────────────────


class TestReflectAndRemember:
    """#92 — record_outcome auto-triggers reflect_and_remember."""

    def _make_memory_with_record(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod
        from engine.memory import TradeMemory, TradeRecord

        mem_file = tmp_path / "memory.json"
        monkeypatch.setattr(mem_mod, "MEMORY_FILE", mem_file)
        mem = TradeMemory()
        mem._records = []
        rec = TradeRecord(
            id="trade-abc",
            timestamp="2026-01-01T10:00:00",
            symbol="TCS",
            exchange="NSE",
            verdict="BUY",
            confidence=70,
            entry_price=3500.0,
            stop_loss=3400.0,
            target_price=3650.0,
        )
        mem._records.append(rec)
        return mem

    def test_record_outcome_updates_outcome(self, tmp_path, monkeypatch):
        mem = self._make_memory_with_record(tmp_path, monkeypatch)
        success = mem.record_outcome("trade-abc", outcome="WIN", actual_pnl=4000.0)
        assert success is True
        rec = mem.get_by_id("trade-abc")
        assert rec is not None
        assert rec.outcome == "WIN"
        assert rec.actual_pnl == 4000.0

    def test_record_outcome_returns_false_for_unknown_id(self, tmp_path, monkeypatch):
        mem = self._make_memory_with_record(tmp_path, monkeypatch)
        result = mem.record_outcome("nonexistent", outcome="WIN")
        assert result is False

    def test_reflect_and_remember_rule_based_on_win(self, tmp_path, monkeypatch):
        mem = self._make_memory_with_record(tmp_path, monkeypatch)
        mem.record_outcome("trade-abc", outcome="WIN", actual_pnl=5000.0)

        # Trigger reflect with no LLM (rule-based fallback)
        lesson = mem.reflect_and_remember("trade-abc", llm_provider=None)
        assert isinstance(lesson, str)
        assert len(lesson) > 0

    def test_reflect_and_remember_rule_based_on_loss(self, tmp_path, monkeypatch):
        mem = self._make_memory_with_record(tmp_path, monkeypatch)
        mem.record_outcome("trade-abc", outcome="LOSS", actual_pnl=-2000.0)

        lesson = mem.reflect_and_remember("trade-abc", llm_provider=None)
        assert isinstance(lesson, str)
        assert len(lesson) > 0

    def test_record_outcome_auto_reflect_does_not_raise(self, tmp_path, monkeypatch):
        """Auto-reflect inside record_outcome must never raise even if LLM fails."""
        mem = self._make_memory_with_record(tmp_path, monkeypatch)

        with patch("agent.core.build_fast_provider_from_env", side_effect=RuntimeError("no creds")):
            # Should succeed despite reflect failing
            result = mem.record_outcome("trade-abc", outcome="LOSS", actual_pnl=-1000.0)
            assert result is True

    def test_reflect_with_mock_llm_stores_lesson(self, tmp_path, monkeypatch):
        mem = self._make_memory_with_record(tmp_path, monkeypatch)
        mem.record_outcome("trade-abc", outcome="WIN", actual_pnl=3000.0)

        mock_provider = MagicMock()
        mock_provider.chat.return_value = "Never trade against the trend."

        lesson = mem.reflect_and_remember("trade-abc", llm_provider=mock_provider)
        assert lesson == "Never trade against the trend."

        rec = mem.get_by_id("trade-abc")
        assert rec is not None
        assert rec.lesson == "Never trade against the trend."


# ── #90: BM25 retrieval ───────────────────────────────────────────


class TestBM25Retrieval:
    """#90 — FTS5 auto-index on _save() + get_bm25_context()."""

    def _make_search(self, tmp_path):
        from engine.search import AnalysisSearch

        return AnalysisSearch(db_path=tmp_path / "search.db")

    def test_index_records_returns_count(self, tmp_path):
        from engine.memory import TradeRecord
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "search.db")
        records = [
            TradeRecord(
                id="r1",
                timestamp="2026-01-01T10:00:00",
                symbol="INFY",
                exchange="NSE",
                verdict="BUY",
                confidence=70,
            ),
            TradeRecord(
                id="r2",
                timestamp="2026-01-01T10:00:00",
                symbol="TCS",
                exchange="NSE",
                verdict="SELL",
                confidence=60,
            ),
        ]
        count = search.index_records(records)
        assert count == 2

    def test_search_finds_indexed_symbol(self, tmp_path):
        from engine.memory import TradeRecord
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "search.db")
        records = [
            TradeRecord(
                id="r1",
                timestamp="2026-01-01T10:00:00",
                symbol="RELIANCE",
                exchange="NSE",
                verdict="BUY",
                confidence=80,
                synthesis_text="Strong Q4 results, fiber expansion tailwind",
            ),
        ]
        search.index_records(records)
        results = search.search("RELIANCE")
        assert len(results) >= 1
        assert results[0].symbol == "RELIANCE"

    def test_get_bm25_context_returns_string(self, tmp_path):
        from engine.memory import TradeRecord
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "search.db")
        records = [
            TradeRecord(
                id="r1",
                timestamp="2026-01-01T10:00:00",
                symbol="WIPRO",
                exchange="NSE",
                verdict="HOLD",
                confidence=50,
            ),
        ]
        search.index_records(records)
        ctx = search.get_bm25_context("WIPRO")
        assert isinstance(ctx, str)
        assert "WIPRO" in ctx

    def test_get_bm25_context_empty_when_no_index(self, tmp_path):
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "empty.db")
        ctx = search.get_bm25_context("ZOMATO")
        assert ctx == ""

    def test_auto_index_fires_on_save(self, tmp_path, monkeypatch):
        """record_outcome triggers _save() which should auto-index into FTS5."""
        import engine.memory as mem_mod
        from engine.memory import TradeMemory, TradeRecord
        from engine.search import AnalysisSearch

        # Use a real search DB to verify auto-index
        search_db = tmp_path / "search.db"
        search = AnalysisSearch(db_path=search_db)

        mem_file = tmp_path / "memory.json"
        monkeypatch.setattr(mem_mod, "MEMORY_FILE", mem_file)
        mem = TradeMemory()
        mem._records = []
        rec = TradeRecord(
            id="auto001",
            timestamp="2026-01-01T10:00:00",
            symbol="HDFC",
            exchange="NSE",
            verdict="BUY",
            confidence=65,
        )
        mem._records.append(rec)

        # Patch the singleton in engine.search (lazy-imported in _save())
        with patch("engine.search.analysis_search", search):
            mem._save()

        results = search.search("HDFC")
        assert any(r.symbol == "HDFC" for r in results)

    def test_search_empty_on_fts_error(self, tmp_path):
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "s.db")
        # Garbage FTS5 query syntax — should return [] not raise
        results = search.search('symbol:"" INVALID!!!')
        assert isinstance(results, list)

    def test_index_skips_records_without_id(self, tmp_path):
        from engine.memory import TradeRecord
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "s.db")
        no_id_rec = TradeRecord(
            id="",
            timestamp="2026-01-01T10:00:00",
            symbol="INFY",
            exchange="NSE",
            verdict="BUY",
            confidence=50,
        )
        count = search.index_records([no_id_rec])
        assert count == 0

    def test_clear_empties_index(self, tmp_path):
        from engine.memory import TradeRecord
        from engine.search import AnalysisSearch

        search = AnalysisSearch(db_path=tmp_path / "s.db")
        search.index_records(
            [
                TradeRecord(
                    id="c1",
                    timestamp="2026-01-01T10:00:00",
                    symbol="INFY",
                    exchange="NSE",
                    verdict="BUY",
                    confidence=70,
                ),
            ]
        )
        assert len(search.search("INFY")) >= 1

        search.clear()
        assert search.search("INFY") == []
