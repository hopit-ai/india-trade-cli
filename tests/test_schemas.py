"""
tests/test_schemas.py
─────────────────────
Tests for Pydantic structured output models and the synthesis text parser.
No LLM calls — all tests use canned text/JSON strings.
"""

import json

import pytest
from pydantic import ValidationError

# ── Models ───────────────────────────────────────────────────────────────────

from agent.schemas import AnalystSignal, PersonaSignal, SynthesisOutput

# ── Parser ────────────────────────────────────────────────────────────────────

from agent.schema_parser import parse_synthesis_output

# ── Fixtures ─────────────────────────────────────────────────────────────────

FULL_SYNTHESIS_TEXT = """\
VERDICT: BUY
CONFIDENCE: 72%
WINNER: BULL — stronger argument

TRADE RECOMMENDATION:
Strategy  : Buy on dip
Entry     : ₹2,850
Stop-Loss : ₹2,700 (5.3%)
Target    : ₹3,100 (8.8%)
R:R Ratio : 1.7:1
Position  : 12 shares

RATIONALE (3 bullets):
- Strong technical breakout above 200 DMA
- Institutional buying in F&O data
- RSI not yet overbought at 58

RISKS (2-3 bullets):
- Global sell-off risk in IT sector
- Upcoming earnings could disappoint
"""

STRONG_BUY_TEXT = """\
VERDICT: STRONG_BUY
CONFIDENCE: 90%
WINNER: BULL

TRADE RECOMMENDATION:
Strategy  : Aggressive buy
Entry     : at market
Stop-Loss : ₹1,400
Target    : ₹1,700
R:R Ratio : 2:1
Position  : 20 shares

RATIONALE (3 bullets):
- Massive breakout on huge volume
- FII buying all week
- Sector tailwind

RISKS (2 bullets):
- General market risk
- Regulatory risk
"""

STRONG_SELL_TEXT = """\
VERDICT: STRONG_SELL
CONFIDENCE: 85%
WINNER: BEAR

TRADE RECOMMENDATION:
Strategy  : Short on bounce
Entry     : ₹500
Stop-Loss : ₹530
Target    : ₹430
R:R Ratio : 2.3:1
Position  : 5 shares

RATIONALE (3 bullets):
- Death cross on daily chart
- Promoter selling shares
- Revenue miss three quarters in a row

RISKS (2 bullets):
- Short squeeze risk
- Surprise buyback announcement
"""

VALID_JSON_TEXT = json.dumps(
    {
        "verdict": "SELL",
        "confidence": 60,
        "winner": "BEAR",
        "strategy": "Short futures",
        "entry": "₹1,200",
        "stop_loss": "₹1,280",
        "target": "₹1,050",
        "risk_reward": "1.9:1",
        "position": "1 lot",
        "rationale": ["Bearish engulfing candle", "FII selling"],
        "risks": ["Stop hunt above resistance"],
    }
)

PARTIAL_TEXT = "VERDICT: HOLD\nCONFIDENCE: 45%\n"

EMPTY_TEXT = ""

MALFORMED_TEXT = "This LLM just talked about the stock a lot without any structure."


# ═══════════════════════════════════════════════════════════════════════════════
# SynthesisOutput model tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSynthesisOutputModel:
    def test_valid_construction(self):
        s = SynthesisOutput(verdict="BUY", confidence=72)
        assert s.verdict == "BUY"
        assert s.confidence == 72
        assert s.winner == "NEUTRAL"
        assert s.strategy == ""
        assert s.rationale == []
        assert s.risks == []

    def test_all_fields_construction(self):
        s = SynthesisOutput(
            verdict="STRONG_BUY",
            confidence=90,
            winner="BULL",
            strategy="Buy on dip",
            entry="₹2,850",
            stop_loss="₹2,700",
            target="₹3,100",
            risk_reward="1.7:1",
            position="12 shares",
            rationale=["Strong breakout", "Good volume"],
            risks=["Market risk"],
        )
        assert s.verdict == "STRONG_BUY"
        assert s.winner == "BULL"
        assert len(s.rationale) == 2

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            SynthesisOutput(verdict="MAYBE", confidence=50)

    def test_confidence_too_high_raises(self):
        with pytest.raises(ValidationError):
            SynthesisOutput(verdict="BUY", confidence=101)

    def test_confidence_too_low_raises(self):
        with pytest.raises(ValidationError):
            SynthesisOutput(verdict="BUY", confidence=-1)

    def test_confidence_boundary_values(self):
        low = SynthesisOutput(verdict="HOLD", confidence=0)
        high = SynthesisOutput(verdict="HOLD", confidence=100)
        assert low.confidence == 0
        assert high.confidence == 100

    def test_all_verdicts_valid(self):
        for v in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"):
            s = SynthesisOutput(verdict=v, confidence=50)
            assert s.verdict == v

    def test_all_winners_valid(self):
        for w in ("BULL", "BEAR", "NEUTRAL"):
            s = SynthesisOutput(verdict="HOLD", confidence=50, winner=w)
            assert s.winner == w

    def test_invalid_winner_raises(self):
        with pytest.raises(ValidationError):
            SynthesisOutput(verdict="BUY", confidence=50, winner="NEITHER")

    def test_defaults_are_empty(self):
        s = SynthesisOutput(verdict="HOLD", confidence=50)
        assert s.entry == ""
        assert s.stop_loss == ""
        assert s.target == ""
        assert s.risk_reward == ""
        assert s.position == ""
        assert s.strategy == ""


# ═══════════════════════════════════════════════════════════════════════════════
# AnalystSignal model tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalystSignalModel:
    def test_valid_construction(self):
        a = AnalystSignal(analyst="Technical", verdict="BULLISH", confidence=80, score=0.75)
        assert a.analyst == "Technical"
        assert a.verdict == "BULLISH"

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            AnalystSignal(analyst="Technical", verdict="POSITIVE", confidence=80, score=0.75)

    def test_all_verdicts_valid(self):
        for v in ("BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"):
            a = AnalystSignal(analyst="X", verdict=v, confidence=50, score=0.5)
            assert a.verdict == v

    def test_confidence_validation(self):
        with pytest.raises(ValidationError):
            AnalystSignal(analyst="X", verdict="BULLISH", confidence=150, score=0.5)

    def test_defaults(self):
        a = AnalystSignal(analyst="X", verdict="NEUTRAL", confidence=50, score=0.0)
        assert a.key_points == []
        assert a.error == ""


# ═══════════════════════════════════════════════════════════════════════════════
# PersonaSignal model tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersonaSignalModel:
    def test_valid_construction(self):
        p = PersonaSignal(persona="Buffett", verdict="BUY", confidence=75)
        assert p.persona == "Buffett"
        assert p.verdict == "BUY"

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            PersonaSignal(persona="Buffett", verdict="WATCH", confidence=75)

    def test_defaults(self):
        p = PersonaSignal(persona="Jhunjhunwala", verdict="HOLD", confidence=50)
        assert p.rationale == []
        assert p.key_metrics == {}

    def test_key_metrics_dict(self):
        p = PersonaSignal(
            persona="Lynch",
            verdict="BUY",
            confidence=80,
            key_metrics={"PE": "15", "Growth": "25%"},
        )
        assert p.key_metrics["PE"] == "15"


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — verdict parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseSynthesisVerdicts:
    def test_buy_verdict(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert result.verdict == "BUY"

    def test_strong_buy_verdict(self):
        result = parse_synthesis_output(STRONG_BUY_TEXT)
        assert result.verdict == "STRONG_BUY"

    def test_strong_sell_verdict(self):
        result = parse_synthesis_output(STRONG_SELL_TEXT)
        assert result.verdict == "STRONG_SELL"

    def test_hold_verdict(self):
        result = parse_synthesis_output(PARTIAL_TEXT)
        assert result.verdict == "HOLD"

    def test_sell_verdict(self):
        text = "VERDICT: SELL\nCONFIDENCE: 65%\n"
        result = parse_synthesis_output(text)
        assert result.verdict == "SELL"


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — confidence parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseSynthesisConfidence:
    def test_confidence_with_percent(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert result.confidence == 72

    def test_confidence_without_percent(self):
        text = "VERDICT: BUY\nCONFIDENCE: 55\n"
        result = parse_synthesis_output(text)
        assert result.confidence == 55

    def test_confidence_partial_text(self):
        result = parse_synthesis_output(PARTIAL_TEXT)
        assert result.confidence == 45

    def test_confidence_default_on_missing(self):
        result = parse_synthesis_output("VERDICT: BUY\n")
        assert result.confidence == 50  # default


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — WINNER parsing
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseSynthesisWinner:
    def test_bull_winner(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert result.winner == "BULL"

    def test_bear_winner(self):
        result = parse_synthesis_output(STRONG_SELL_TEXT)
        assert result.winner == "BEAR"

    def test_winner_default_neutral(self):
        result = parse_synthesis_output(PARTIAL_TEXT)
        assert result.winner == "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — TRADE RECOMMENDATION block
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseTradeRecommendation:
    def test_entry_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "2,850" in result.entry or "2850" in result.entry

    def test_stop_loss_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "2,700" in result.stop_loss or "2700" in result.stop_loss

    def test_target_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "3,100" in result.target or "3100" in result.target

    def test_strategy_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "dip" in result.strategy.lower() or result.strategy != ""

    def test_risk_reward_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "1.7" in result.risk_reward

    def test_position_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert "12" in result.position

    def test_at_market_entry(self):
        result = parse_synthesis_output(STRONG_BUY_TEXT)
        assert "market" in result.entry.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — RATIONALE and RISKS bullets
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseBullets:
    def test_rationale_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert len(result.rationale) >= 1
        assert any("200 DMA" in r or "technical" in r.lower() for r in result.rationale)

    def test_risks_parsed(self):
        result = parse_synthesis_output(FULL_SYNTHESIS_TEXT)
        assert len(result.risks) >= 1

    def test_rationale_max_5(self):
        text = FULL_SYNTHESIS_TEXT + "\nRATIONALE (6 bullets):\n"
        text += "".join(f"- Point {i}\n" for i in range(10))
        result = parse_synthesis_output(text)
        assert len(result.rationale) <= 5

    def test_risks_max_5(self):
        text = FULL_SYNTHESIS_TEXT
        result = parse_synthesis_output(text)
        assert len(result.risks) <= 5


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseEdgeCases:
    def test_empty_string_returns_defaults(self):
        result = parse_synthesis_output(EMPTY_TEXT)
        assert isinstance(result, SynthesisOutput)
        assert result.verdict == "HOLD"
        assert result.confidence == 50
        assert result.winner == "NEUTRAL"
        assert result.rationale == []
        assert result.risks == []

    def test_malformed_text_returns_defaults(self):
        result = parse_synthesis_output(MALFORMED_TEXT)
        assert isinstance(result, SynthesisOutput)
        assert result.verdict == "HOLD"

    def test_partial_text_returns_partial(self):
        result = parse_synthesis_output(PARTIAL_TEXT)
        assert result.verdict == "HOLD"
        assert result.confidence == 45
        assert result.entry == ""

    def test_never_raises(self):
        """Parser must never raise — returns defaults on any input."""
        bad_inputs = [
            None if False else "",  # empty
            "VERDICT: INVALID_VERDICT\nCONFIDENCE: 999%\n",
            "CONFIDENCE: not_a_number\n",
            "{invalid json}",
            "{ completely }{ broken }{ json }",
        ]
        for bad in bad_inputs:
            result = parse_synthesis_output(bad)
            assert isinstance(result, SynthesisOutput)

    def test_confidence_clamped_on_parse(self):
        # If line parsing produces out-of-range, should clamp or use default
        text = "VERDICT: BUY\nCONFIDENCE: 999%\n"
        result = parse_synthesis_output(text)
        assert 0 <= result.confidence <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# parse_synthesis_output — JSON path
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseJsonPath:
    def test_valid_json_parsed(self):
        result = parse_synthesis_output(VALID_JSON_TEXT)
        assert result.verdict == "SELL"
        assert result.confidence == 60
        assert result.winner == "BEAR"
        assert result.strategy == "Short futures"
        assert result.entry == "₹1,200"
        assert result.stop_loss == "₹1,280"
        assert result.target == "₹1,050"
        assert result.risk_reward == "1.9:1"
        assert result.position == "1 lot"
        assert len(result.rationale) == 2
        assert len(result.risks) == 1

    def test_json_with_surrounding_text(self):
        """JSON embedded in prose text (LLM often wraps JSON in explanation)."""
        text = (
            "Here is my analysis:\n"
            + VALID_JSON_TEXT
            + "\nPlease use the above for your trade plan."
        )
        result = parse_synthesis_output(text)
        assert result.verdict == "SELL"

    def test_invalid_json_falls_back_to_text(self):
        """Broken JSON should fall back to text parsing."""
        text = "{ broken json }\nVERDICT: BUY\nCONFIDENCE: 70%\n"
        result = parse_synthesis_output(text)
        assert isinstance(result, SynthesisOutput)
        # Should have parsed from text path or returned defaults
        assert result.verdict in ("BUY", "HOLD")

    def test_json_invalid_verdict_falls_back(self):
        """JSON with invalid verdict enum should fall back gracefully."""
        bad_json = json.dumps({"verdict": "MAYBE", "confidence": 50})
        result = parse_synthesis_output(bad_json)
        assert isinstance(result, SynthesisOutput)
        assert result.verdict == "HOLD"  # default

    def test_json_confidence_out_of_range_clamped(self):
        """JSON with out-of-range confidence should clamp or fall back."""
        bad_json = json.dumps({"verdict": "BUY", "confidence": 150})
        result = parse_synthesis_output(bad_json)
        assert isinstance(result, SynthesisOutput)
        assert 0 <= result.confidence <= 100
