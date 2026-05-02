"""
Tests for memory verdict extraction — #123.

Ensures that store_from_analysis() records the correct verdict from LLM synthesis
output instead of silently defaulting to HOLD.
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


class TestParseSynthesisOutput:
    """Unit tests for agent.schema_parser.parse_synthesis_output."""

    def test_plain_buy(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("VERDICT: BUY\nCONFIDENCE: 72%")
        assert verdict == "BUY"
        assert conf == 72

    def test_plain_sell(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("VERDICT: SELL\nCONFIDENCE: 60%")
        assert verdict == "SELL"
        assert conf == 60

    def test_strong_buy(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("VERDICT: STRONG_BUY\nCONFIDENCE: 85%")
        assert verdict == "STRONG_BUY"
        assert conf == 85

    def test_strong_sell(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, _, _ = parse_synthesis_output("VERDICT: STRONG_SELL\nCONFIDENCE: 90%")
        assert verdict == "STRONG_SELL"

    def test_markdown_bold(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("**VERDICT: STRONG_BUY**\n**CONFIDENCE: 80%**")
        assert verdict == "STRONG_BUY"
        assert conf == 80

    def test_case_insensitive(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("Verdict: sell\nConfidence: 45%")
        assert verdict == "SELL"
        assert conf == 45

    def test_verdict_in_paragraph(self):
        from agent.schema_parser import parse_synthesis_output

        text = (
            "Based on the analysis of technical and fundamental factors,\n"
            "Final VERDICT: BUY\nCONFIDENCE: 68%\nStrategy: Iron Bull Spread"
        )
        verdict, conf, strategy = parse_synthesis_output(text)
        assert verdict == "BUY"
        assert conf == 68
        assert "Iron Bull Spread" in strategy

    def test_default_hold_when_absent(self):
        from agent.schema_parser import parse_synthesis_output

        verdict, conf, _ = parse_synthesis_output("The analysis is inconclusive.")
        assert verdict == "HOLD"
        assert conf == 50

    def test_keyword_fallback(self):
        """If no explicit label, keyword scan should still catch the verdict."""
        from agent.schema_parser import parse_synthesis_output

        text = "All indicators point to a STRONG_BUY opportunity here."
        verdict, _, _ = parse_synthesis_output(text)
        assert verdict == "STRONG_BUY"

    def test_confidence_clamped_to_100(self):
        from agent.schema_parser import parse_synthesis_output

        _, conf, _ = parse_synthesis_output("VERDICT: BUY\nCONFIDENCE: 150%")
        assert conf == 100

    def test_confidence_clamped_to_0(self):
        from agent.schema_parser import parse_synthesis_output

        # Negative or zero should clamp
        _, conf, _ = parse_synthesis_output("VERDICT: HOLD\nCONFIDENCE: 0%")
        assert conf == 0


class TestStoreFromAnalysisSavesCorrectVerdict:
    """Integration tests: store_from_analysis must persist non-HOLD verdicts."""

    def _make_report(self, analyst, score):
        """Create a minimal analyst report stub."""

        class FakeReport:
            pass

        r = FakeReport()
        r.analyst = analyst
        r.score = score
        r.data = {}
        return r

    def test_buy_verdict_stored(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "VERDICT: BUY\nCONFIDENCE: 75%\nStrategy: Delivery Buy"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="INFY",
            exchange="NSE",
            analyst_reports=[self._make_report("Technical", 70)],
            debate=None,
            synthesis=synthesis,
        )
        assert record.verdict == "BUY"
        assert record.confidence == 75

    def test_strong_buy_verdict_stored(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm2.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "**VERDICT: STRONG_BUY**\n**CONFIDENCE: 88%**"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="RELIANCE",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        assert record.verdict == "STRONG_BUY"
        assert record.confidence == 88

    def test_sell_verdict_stored(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm3.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "Final VERDICT: SELL\nCONFIDENCE: 65%"
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="NIFTY",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        assert record.verdict == "SELL"

    def test_hold_verdict_stored_when_absent(self, tmp_path, monkeypatch):
        import engine.memory as mem_mod

        monkeypatch.setattr("engine.memory.MEMORY_FILE", tmp_path / "tm4.json")
        mem_mod.trade_memory = mem_mod.TradeMemory()

        synthesis = "Market conditions are mixed and inconclusive."
        record = mem_mod.trade_memory.store_from_analysis(
            symbol="TCS",
            exchange="NSE",
            analyst_reports=[],
            debate=None,
            synthesis=synthesis,
        )
        assert record.verdict == "HOLD"
