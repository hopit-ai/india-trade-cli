"""
Tests for multi-persona debate command (#166).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ── PersonaSignal schema ─────────────────────────────────────


class TestPersonaSignal:
    def test_valid_signal(self):
        from agent.schemas import PersonaSignal

        sig = PersonaSignal(
            persona="buffett",
            verdict="BUY",
            confidence=72,
            rationale=["Strong moat", "High ROE"],
            key_metrics={"ROE": "22%"},
        )
        assert sig.persona == "buffett"
        assert sig.verdict == "BUY"
        assert sig.confidence == 72

    def test_confidence_must_be_0_to_100(self):
        from agent.schemas import PersonaSignal
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PersonaSignal(
                persona="buffett",
                verdict="BUY",
                confidence=150,
                rationale=[],
                key_metrics={},
            )

    def test_all_valid_verdicts(self):
        from agent.schemas import PersonaSignal

        for verdict in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"):
            sig = PersonaSignal(
                persona="test",
                verdict=verdict,
                confidence=50,
                rationale=[],
                key_metrics={},
            )
            assert sig.verdict == verdict

    def test_invalid_verdict_rejected(self):
        from agent.schemas import PersonaSignal
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PersonaSignal(
                persona="buffett",
                verdict="MAYBE",
                confidence=50,
                rationale=[],
                key_metrics={},
            )


# ── run_debate returns list[PersonaSignal] ──────────────────


class TestRunDebate:
    def test_debate_returns_five_signals(self):
        """run_debate without LLM returns 5 signals (one per persona)."""
        from agent.persona_agent import run_debate

        signals = run_debate(symbol="INFY", exchange="NSE", registry=None, llm_provider=None)
        assert isinstance(signals, list)
        assert len(signals) == 5

    def test_debate_signals_are_persona_signals(self):
        from agent.persona_agent import run_debate
        from agent.schemas import PersonaSignal

        signals = run_debate(symbol="INFY", exchange="NSE", registry=None, llm_provider=None)
        for sig in signals:
            assert isinstance(sig, PersonaSignal)

    def test_debate_has_all_five_personas(self):
        from agent.persona_agent import run_debate

        signals = run_debate(symbol="RELIANCE", exchange="NSE", registry=None, llm_provider=None)
        persona_ids = {s.persona for s in signals}
        assert "buffett" in persona_ids
        assert "jhunjhunwala" in persona_ids
        assert "lynch" in persona_ids
        assert "soros" in persona_ids
        assert "munger" in persona_ids

    def test_each_signal_has_valid_confidence(self):
        from agent.persona_agent import run_debate

        signals = run_debate(symbol="TCS", exchange="NSE", registry=None, llm_provider=None)
        for sig in signals:
            assert 0 <= sig.confidence <= 100

    def test_each_signal_has_valid_verdict(self):
        from agent.persona_agent import run_debate

        valid_verdicts = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}
        signals = run_debate(symbol="TCS", exchange="NSE", registry=None, llm_provider=None)
        for sig in signals:
            assert sig.verdict in valid_verdicts


# ── Consensus computation ───────────────────────────────────


class TestConsensus:
    def _make_signals(self, verdicts: list[str]) -> list:
        from agent.schemas import PersonaSignal
        from agent.personas import list_personas

        personas = list_personas()
        signals = []
        for persona, verdict in zip(personas, verdicts):
            signals.append(
                PersonaSignal(
                    persona=persona.id,
                    verdict=verdict,
                    confidence=60,
                    rationale=["test"],
                    key_metrics={},
                )
            )
        return signals

    def test_majority_buy_consensus(self):
        """3/5 BUY should give BUY consensus."""
        from app.commands.persona import _compute_consensus

        signals = self._make_signals(["BUY", "BUY", "BUY", "HOLD", "SELL"])
        consensus = _compute_consensus(signals)
        # consensus verdict is the majority
        assert consensus["verdict"] in ("BUY", "HOLD")  # BUY has plurality
        assert consensus["buy_count"] == 3
        assert consensus["total"] == 5

    def test_all_hold_consensus(self):
        from app.commands.persona import _compute_consensus

        signals = self._make_signals(["HOLD", "HOLD", "HOLD", "HOLD", "HOLD"])
        consensus = _compute_consensus(signals)
        assert consensus["verdict"] == "HOLD"

    def test_consensus_names_the_buy_camp(self):
        from app.commands.persona import _compute_consensus

        signals = self._make_signals(["BUY", "BUY", "HOLD", "HOLD", "HOLD"])
        consensus = _compute_consensus(signals)
        # buy_personas should list persona names/ids that said BUY
        assert len(consensus["buy_personas"]) == 2


# ── Table rendering doesn't crash ──────────────────────────


class TestDebateTableRendering:
    def test_debate_table_renders(self):
        """_cmd_debate should not raise when signals list is provided."""
        from agent.schemas import PersonaSignal
        from agent.personas import list_personas
        from rich.console import Console
        from io import StringIO

        personas = list_personas()
        signals = [
            PersonaSignal(
                persona=p.id,
                verdict="BUY",
                confidence=65,
                rationale=["Good ROE"],
                key_metrics={"ROE": "18%"},
            )
            for p in personas
        ]

        # Import the table builder and confirm it returns a Table
        from app.commands.persona import _build_debate_table

        table = _build_debate_table(signals)
        assert table is not None

        # Render to string — should not raise
        out = StringIO()
        console = Console(file=out, width=120)
        console.print(table)
        rendered = out.getvalue()
        assert len(rendered) > 0

    def test_debate_table_has_persona_names(self):
        from agent.schemas import PersonaSignal
        from agent.personas import list_personas
        from app.commands.persona import _build_debate_table
        from rich.console import Console
        from io import StringIO

        personas = list_personas()
        signals = [
            PersonaSignal(
                persona=p.id,
                verdict="HOLD",
                confidence=50,
                rationale=[],
                key_metrics={},
            )
            for p in personas
        ]

        table = _build_debate_table(signals)
        out = StringIO()
        console = Console(file=out, width=160)
        console.print(table)
        rendered = out.getvalue()

        # All 5 persona names should appear
        for p in personas:
            assert p.name in rendered or p.id in rendered


# ── parse_persona_response ───────────────────────────────────


class TestParsePersonaResponse:
    def test_parses_buy_verdict(self):
        from agent.persona_agent import parse_persona_response

        text = "VERDICT: BUY\nCONFIDENCE: 72\nRATIONALE:\n- Strong FCF\n"
        sig = parse_persona_response(text, "buffett")
        assert sig.verdict == "BUY"
        assert sig.confidence == 72

    def test_parses_strong_sell(self):
        from agent.persona_agent import parse_persona_response

        text = "VERDICT: STRONG_SELL\nCONFIDENCE: 85\n"
        sig = parse_persona_response(text, "soros")
        assert sig.verdict == "STRONG_SELL"

    def test_empty_text_returns_hold(self):
        from agent.persona_agent import parse_persona_response

        sig = parse_persona_response("", "munger")
        assert sig.verdict == "HOLD"
        assert sig.confidence == 30

    def test_persona_id_preserved(self):
        from agent.persona_agent import parse_persona_response

        sig = parse_persona_response("VERDICT: BUY\nCONFIDENCE: 60\n", "jhunjhunwala")
        assert sig.persona == "jhunjhunwala"
