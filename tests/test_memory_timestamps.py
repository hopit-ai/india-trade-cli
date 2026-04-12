"""
Tests for memory timestamps, analysis snapshot, and stats fixes (#122, #123).
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def temp_memory(tmp_path, monkeypatch):
    """Each test gets an isolated memory file."""
    monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "trade_memory.json")
    # Re-init singleton for each test
    import engine.memory as mem_mod
    mem_mod.trade_memory = mem_mod.TradeMemory()
    yield
    mem_mod.trade_memory = mem_mod.TradeMemory()


class TestTimestampAlwaysSet:
    def test_store_sets_timestamp(self):
        from engine.memory import trade_memory

        record = trade_memory.store(symbol="INFY", verdict="BUY", confidence=70)
        assert record.timestamp is not None
        assert len(record.timestamp) >= 10  # at least YYYY-MM-DD

    def test_timestamp_is_iso_format(self):
        from engine.memory import trade_memory
        from datetime import datetime

        record = trade_memory.store(symbol="TCS", verdict="HOLD", confidence=55)
        # Should not raise
        dt = datetime.fromisoformat(record.timestamp)
        assert dt is not None

    def test_price_at_analysis_stored(self):
        from engine.memory import trade_memory

        record = trade_memory.store(symbol="RELIANCE", verdict="BUY", confidence=72, price_at_analysis=2950.0)
        assert record.price_at_analysis == 2950.0

    def test_synthesis_text_stored(self):
        from engine.memory import trade_memory

        synth = "VERDICT: BUY\nCONFIDENCE: 72%\nStrategy: Delivery Buy"
        record = trade_memory.store(symbol="INFY", verdict="BUY", confidence=72, synthesis_text=synth)
        assert record.synthesis_text == synth


class TestBackwardCompatLoad:
    def test_load_old_records_without_new_fields(self, monkeypatch, tmp_path):
        """Old JSON records that lack new fields should load without crashing."""
        import engine.memory as mem_mod

        old_data = [
            {
                "id": "abc123",
                "timestamp": "2026-04-01T10:00:00",
                "symbol": "INFY",
                "exchange": "NSE",
                "verdict": "BUY",
                "confidence": 70,
                "analyst_scores": {},
                "strategy": "Delivery Buy",
                "debate_winner": "BULL",
                "bull_summary": "",
                "bear_summary": "",
                "outcome": None,
                "actual_pnl": None,
                "outcome_notes": "",
                "tags": [],
                # NEW fields NOT present (backward compat test)
                # "price_at_analysis", "synthesis_text" are missing
            }
        ]

        mem_file = tmp_path / "trade_memory.json"
        mem_file.write_text(json.dumps(old_data))
        monkeypatch.setattr("engine.memory.MEMORY_FILE", mem_file)

        mem = mem_mod.TradeMemory()
        assert len(mem._records) == 1
        assert mem._records[0].symbol == "INFY"
        # New fields should be None/empty by default
        assert mem._records[0].price_at_analysis is None

    def test_load_records_with_unknown_keys(self, monkeypatch, tmp_path):
        """JSON with extra unknown keys should not crash."""
        import engine.memory as mem_mod

        old_data = [
            {
                "id": "xyz789",
                "timestamp": "2026-04-01T10:00:00",
                "symbol": "TCS",
                "exchange": "NSE",
                "verdict": "HOLD",
                "confidence": 55,
                "analyst_scores": {},
                "strategy": "",
                "debate_winner": "",
                "bull_summary": "",
                "bear_summary": "",
                "outcome": None,
                "actual_pnl": None,
                "outcome_notes": "",
                "tags": [],
                "UNKNOWN_KEY_FUTURE_VERSION": "some_value",  # should be ignored
            }
        ]

        mem_file = tmp_path / "trade_memory.json"
        mem_file.write_text(json.dumps(old_data))
        monkeypatch.setattr("engine.memory.MEMORY_FILE", mem_file)

        mem = mem_mod.TradeMemory()
        assert len(mem._records) == 1  # loaded successfully


class TestParseSynthesisFixed:
    def test_plain_verdict_line(self):
        from engine.memory import _parse_synthesis

        verdict, conf, _ = _parse_synthesis("VERDICT: BUY\nCONFIDENCE: 72%")
        assert verdict == "BUY"
        assert conf == 72

    def test_markdown_bold_verdict(self):
        from engine.memory import _parse_synthesis

        verdict, conf, _ = _parse_synthesis("**VERDICT: STRONG_BUY**\n**CONFIDENCE: 80%**")
        assert verdict == "STRONG_BUY"
        assert conf == 80

    def test_case_insensitive_verdict(self):
        from engine.memory import _parse_synthesis

        verdict, conf, _ = _parse_synthesis("Verdict: sell\nConfidence: 45%")
        assert verdict == "SELL"
        assert conf == 45

    def test_verdict_in_middle_of_text(self):
        from engine.memory import _parse_synthesis

        text = "Based on analysis...\nFinal VERDICT: BUY\nCONFIDENCE: 68%\nStrategy: Iron Bull Spread"
        verdict, conf, strategy = _parse_synthesis(text)
        assert verdict == "BUY"
        assert conf == 68

    def test_default_hold_when_not_found(self):
        from engine.memory import _parse_synthesis

        verdict, conf, _ = _parse_synthesis("The analysis is inconclusive.")
        assert verdict == "HOLD"
        assert conf == 50

    def test_strong_sell_extracted(self):
        from engine.memory import _parse_synthesis

        verdict, _, _ = _parse_synthesis("VERDICT: STRONG_SELL\nCONFIDENCE: 85%")
        assert verdict == "STRONG_SELL"


class TestWinRateMinSample:
    def test_win_rate_none_when_insufficient(self):
        from engine.memory import trade_memory

        # Only 2 outcomes — below 5 minimum
        trade_memory.store(symbol="INFY", verdict="BUY", confidence=70)
        trade_memory.store(symbol="TCS", verdict="BUY", confidence=65)

        r1 = trade_memory._records[0]
        r2 = trade_memory._records[1]
        r1.outcome = "WIN"
        r1.actual_pnl = 500.0
        r2.outcome = "WIN"
        r2.actual_pnl = 300.0

        stats = trade_memory.get_stats()
        assert stats["win_rate"] is None  # insufficient data

    def test_win_rate_shown_when_5_plus_outcomes(self):
        from engine.memory import trade_memory

        for i in range(5):
            trade_memory.store(symbol=f"STOCK{i}", verdict="BUY", confidence=70)

        for r in trade_memory._records:
            r.outcome = "WIN"
            r.actual_pnl = 200.0

        stats = trade_memory.get_stats()
        assert stats["win_rate"] == 100.0

    def test_win_rate_label_shows_fraction(self):
        from engine.memory import trade_memory

        trade_memory.store(symbol="INFY", verdict="BUY", confidence=70)
        trade_memory._records[0].outcome = "WIN"
        trade_memory._records[0].actual_pnl = 500.0

        stats = trade_memory.get_stats()
        assert "win_rate_label" in stats
        assert "1" in stats["win_rate_label"]  # shows "1/1 tracked" or similar
