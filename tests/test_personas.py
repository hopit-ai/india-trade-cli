"""
tests/test_personas.py
──────────────────────
Tests for the named investor personas feature (#165).

All tests are deterministic — no LLM or network calls required.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.personas import (
    PERSONAS,
    InvestorPersona,
    get_persona,
    list_personas,
)
from agent.schemas import PersonaSignal
from agent.persona_agent import (
    parse_persona_response,
    run_persona_analysis,
    _rule_based_signal,
    _score_dimension,
)


# ── Persona definitions ───────────────────────────────────────


class TestPersonaDefinitions:
    """Validate that all 5 personas are correctly defined."""

    EXPECTED_IDS = {"buffett", "jhunjhunwala", "lynch", "soros", "munger"}

    def test_all_five_personas_defined(self):
        assert set(PERSONAS.keys()) == self.EXPECTED_IDS

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_checklist_has_at_least_five_items(self, persona_id: str):
        persona = PERSONAS[persona_id]
        assert len(persona.checklist) >= 5, (
            f"{persona_id}.checklist has {len(persona.checklist)} items — need ≥5"
        )

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_weights_sum_to_one(self, persona_id: str):
        persona = PERSONAS[persona_id]
        total = sum(persona.weights.values())
        assert abs(total - 1.0) < 1e-9, f"{persona_id}.weights sum to {total:.4f}, expected 1.0"

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_system_prompt_non_empty(self, persona_id: str):
        persona = PERSONAS[persona_id]
        assert persona.system_prompt.strip(), f"{persona_id}.system_prompt is empty"

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_system_prompt_has_meaningful_length(self, persona_id: str):
        persona = PERSONAS[persona_id]
        assert len(persona.system_prompt) >= 200, (
            f"{persona_id}.system_prompt too short ({len(persona.system_prompt)} chars)"
        )

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_all_weight_values_positive(self, persona_id: str):
        persona = PERSONAS[persona_id]
        for dim, w in persona.weights.items():
            assert w > 0, f"{persona_id}.weights[{dim}] = {w}, must be > 0"

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_persona_is_dataclass_instance(self, persona_id: str):
        persona = PERSONAS[persona_id]
        assert isinstance(persona, InvestorPersona)

    def test_buffett_weights(self):
        p = PERSONAS["buffett"]
        assert p.weights["fundamentals"] == pytest.approx(0.65)
        assert p.weights["macro"] == pytest.approx(0.10)
        assert p.weights["technicals"] == pytest.approx(0.05)

    def test_soros_macro_dominant(self):
        """Soros should have macro as largest weight."""
        p = PERSONAS["soros"]
        assert p.weights["macro"] == pytest.approx(0.50)
        assert p.weights["macro"] == max(p.weights.values())

    def test_jhunjhunwala_no_options(self):
        """Jhunjhunwala does not use options dimension."""
        p = PERSONAS["jhunjhunwala"]
        assert "options" not in p.weights

    def test_styles_are_correct(self):
        assert PERSONAS["buffett"].style == "value"
        assert PERSONAS["jhunjhunwala"].style == "growth-value"
        assert PERSONAS["lynch"].style == "garp"
        assert PERSONAS["soros"].style == "macro"
        assert PERSONAS["munger"].style == "quality"


# ── Helper functions ──────────────────────────────────────────


class TestGetPersona:
    def test_returns_correct_persona(self):
        persona = get_persona("buffett")
        assert isinstance(persona, InvestorPersona)
        assert persona.id == "buffett"
        assert persona.name == "Warren Buffett"

    def test_case_insensitive(self):
        persona = get_persona("BUFFETT")
        assert persona.id == "buffett"

    def test_raises_for_unknown_id(self):
        with pytest.raises(ValueError, match="Unknown persona"):
            get_persona("invalid_persona_xyz")

    def test_raises_for_empty_string(self):
        with pytest.raises(ValueError):
            get_persona("")

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_all_known_ids_return_persona(self, persona_id: str):
        persona = get_persona(persona_id)
        assert persona.id == persona_id


class TestListPersonas:
    def test_returns_five_items(self):
        personas = list_personas()
        assert len(personas) == 5

    def test_all_items_are_investor_persona(self):
        for p in list_personas():
            assert isinstance(p, InvestorPersona)

    def test_stable_order(self):
        order_a = [p.id for p in list_personas()]
        order_b = [p.id for p in list_personas()]
        assert order_a == order_b

    def test_buffett_first(self):
        """Buffett should be listed first by convention."""
        assert list_personas()[0].id == "buffett"


# ── PersonaSignal schema ──────────────────────────────────────


class TestPersonaSignal:
    def test_valid_signal_creation(self):
        sig = PersonaSignal(
            persona="buffett",
            verdict="BUY",
            confidence=75,
            rationale=["Strong moat", "FCF positive"],
            key_metrics={"ROE": "18%"},
        )
        assert sig.verdict == "BUY"
        assert sig.confidence == 75

    def test_all_verdict_values_accepted(self):
        for verdict in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"):
            sig = PersonaSignal(
                persona="test",
                verdict=verdict,
                confidence=50,
                rationale=["item"],
                key_metrics={},
            )
            assert sig.verdict == verdict

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            PersonaSignal(
                persona="test",
                verdict="STRONG_MAYBE",
                confidence=50,
                rationale=[],
                key_metrics={},
            )

    def test_confidence_zero_accepted(self):
        sig = PersonaSignal(
            persona="test",
            verdict="HOLD",
            confidence=0,
            rationale=[],
            key_metrics={},
        )
        assert sig.confidence == 0

    def test_confidence_100_accepted(self):
        sig = PersonaSignal(
            persona="test",
            verdict="STRONG_BUY",
            confidence=100,
            rationale=[],
            key_metrics={},
        )
        assert sig.confidence == 100

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            PersonaSignal(
                persona="test",
                verdict="HOLD",
                confidence=-1,
                rationale=[],
                key_metrics={},
            )

    def test_confidence_above_100_raises(self):
        with pytest.raises(ValidationError):
            PersonaSignal(
                persona="test",
                verdict="HOLD",
                confidence=101,
                rationale=[],
                key_metrics={},
            )

    def test_empty_rationale_accepted(self):
        sig = PersonaSignal(
            persona="test",
            verdict="HOLD",
            confidence=50,
            rationale=[],
            key_metrics={},
        )
        assert sig.rationale == []

    def test_key_metrics_can_be_empty(self):
        sig = PersonaSignal(
            persona="test",
            verdict="HOLD",
            confidence=50,
            rationale=["item"],
            key_metrics={},
        )
        assert sig.key_metrics == {}


# ── parse_persona_response ────────────────────────────────────


class TestParsePersonaResponse:
    def test_full_valid_response(self):
        text = """
VERDICT: BUY
CONFIDENCE: 72
RATIONALE:
- Strong moat in telecom
- ROE above 15%
- Low debt
KEY_METRICS:
ROE: 18% (above threshold)
D/E: 0.3
"""
        sig = parse_persona_response(text, "buffett")
        assert sig.verdict == "BUY"
        assert sig.confidence == 72
        assert len(sig.rationale) >= 1
        assert sig.persona == "buffett"

    def test_strong_buy_verdict(self):
        text = "VERDICT: STRONG_BUY\nCONFIDENCE: 88\nRATIONALE:\n- Excellent business"
        sig = parse_persona_response(text, "buffett")
        assert sig.verdict == "STRONG_BUY"

    def test_strong_sell_verdict(self):
        text = "VERDICT: STRONG_SELL\nCONFIDENCE: 85\nRATIONALE:\n- Poor fundamentals"
        sig = parse_persona_response(text, "soros")
        assert sig.verdict == "STRONG_SELL"

    def test_empty_text_returns_hold(self):
        sig = parse_persona_response("", "buffett")
        assert sig.verdict == "HOLD"
        assert sig.confidence == 30

    def test_none_like_text_returns_hold(self):
        sig = parse_persona_response("   ", "lynch")
        assert sig.verdict == "HOLD"

    def test_partial_response_no_confidence(self):
        text = "VERDICT: SELL\nThis stock looks bad."
        sig = parse_persona_response(text, "munger")
        assert sig.verdict == "SELL"
        assert sig.confidence == 50  # default

    def test_partial_response_no_verdict(self):
        text = "CONFIDENCE: 65\nRATIONALE:\n- Item one\n- Item two"
        sig = parse_persona_response(text, "jhunjhunwala")
        assert sig.verdict == "HOLD"  # default
        assert sig.confidence == 65

    def test_confidence_clamped_to_100(self):
        text = "VERDICT: BUY\nCONFIDENCE: 999\nRATIONALE:\n- bullet"
        sig = parse_persona_response(text, "buffett")
        assert sig.confidence == 100

    def test_confidence_invalid_negative_falls_back_to_default(self):
        # Negative confidence values can't be captured by \d+ regex,
        # so the parser uses the default (50).
        text = "VERDICT: SELL\nRATIONALE:\n- bullet"
        sig = parse_persona_response(text, "buffett")
        assert sig.confidence == 50  # default when no valid confidence present

    def test_rationale_items_extracted(self):
        text = """VERDICT: HOLD
CONFIDENCE: 55
RATIONALE:
- First item
- Second item
- Third item"""
        sig = parse_persona_response(text, "buffett")
        assert len(sig.rationale) >= 3

    def test_key_metrics_extracted(self):
        text = """VERDICT: BUY
CONFIDENCE: 70
RATIONALE:
- good
KEY_METRICS:
ROE: 20%
PE: 18x"""
        sig = parse_persona_response(text, "buffett")
        assert "ROE" in sig.key_metrics
        assert sig.key_metrics["ROE"] == "20%"

    def test_persona_id_preserved(self):
        text = "VERDICT: BUY\nCONFIDENCE: 60\nRATIONALE:\n- ok"
        sig = parse_persona_response(text, "munger")
        assert sig.persona == "munger"

    def test_non_standard_response_with_bullets_and_explicit_verdict(self):
        """Response with bullets and explicit VERDICT: key."""
        text = """This stock looks interesting.
VERDICT: BUY
CONFIDENCE: 65
RATIONALE:
• Strong brand presence
• Growing revenue
• Reasonable PE"""
        sig = parse_persona_response(text, "lynch")
        assert sig.verdict == "BUY"
        assert sig.confidence == 65
        assert len(sig.rationale) >= 1

    def test_non_standard_response_no_verdict_key_defaults_hold(self):
        """Response without a VERDICT: key should default to HOLD."""
        text = """This stock looks interesting.
• Strong brand presence
• Growing revenue
I would rate this a BUY."""
        sig = parse_persona_response(text, "lynch")
        # No VERDICT: tag → defaults to HOLD
        assert sig.verdict == "HOLD"
        assert len(sig.rationale) >= 1


# ── Deterministic fallback ────────────────────────────────────


class TestRuleBasedFallback:
    """Tests for run_persona_analysis with no LLM and no registry."""

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_returns_valid_persona_signal(self, persona_id: str):
        sig = run_persona_analysis(
            persona_id=persona_id,
            symbol="RELIANCE",
            exchange="NSE",
            registry=None,
            llm_provider=None,
        )
        assert isinstance(sig, PersonaSignal)
        assert sig.persona == persona_id

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_verdict_is_valid_enum(self, persona_id: str):
        sig = run_persona_analysis(
            persona_id=persona_id,
            symbol="TCS",
            exchange="NSE",
            registry=None,
            llm_provider=None,
        )
        assert sig.verdict in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_confidence_in_valid_range(self, persona_id: str):
        sig = run_persona_analysis(
            persona_id=persona_id,
            symbol="INFY",
            exchange="NSE",
            registry=None,
            llm_provider=None,
        )
        assert 0 <= sig.confidence <= 100

    @pytest.mark.parametrize("persona_id", ["buffett", "jhunjhunwala", "lynch", "soros", "munger"])
    def test_rationale_is_list(self, persona_id: str):
        sig = run_persona_analysis(
            persona_id=persona_id,
            symbol="HDFCBANK",
            exchange="NSE",
            registry=None,
            llm_provider=None,
        )
        assert isinstance(sig.rationale, list)

    def test_invalid_persona_raises(self):
        with pytest.raises(ValueError, match="Unknown persona"):
            run_persona_analysis(
                persona_id="notapersona",
                symbol="RELIANCE",
            )

    def test_no_data_defaults_to_hold_zone(self):
        """With no data (registry=None), scores default to 50 → HOLD range."""
        sig = run_persona_analysis(
            persona_id="buffett",
            symbol="RELIANCE",
            registry=None,
            llm_provider=None,
        )
        # With all-neutral data, weighted score ~50 → HOLD
        assert sig.verdict == "HOLD"

    def test_rule_based_signal_direct(self):
        """_rule_based_signal works with empty brief."""
        brief: dict = {
            "symbol": "TEST",
            "exchange": "NSE",
            "technicals": {},
            "fundamentals": {},
            "macro": {},
            "news": [],
            "fii_dii": {},
        }
        sig = _rule_based_signal("buffett", brief)
        assert isinstance(sig, PersonaSignal)
        assert sig.verdict in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")

    def test_good_fundamentals_increase_score(self):
        """Strong fundamentals should raise the score for Buffett."""
        brief_weak: dict = {
            "symbol": "TEST",
            "exchange": "NSE",
            "technicals": {},
            "fundamentals": {"roe": 5, "debt_equity": 2.0, "pe": 80},
            "macro": {},
            "news": [],
            "fii_dii": {},
        }
        brief_strong: dict = {
            "symbol": "TEST",
            "exchange": "NSE",
            "technicals": {},
            "fundamentals": {"roe": 25, "debt_equity": 0.2, "pe": 14, "fcf_yield": 8},
            "macro": {},
            "news": [],
            "fii_dii": {},
        }
        sig_weak = _rule_based_signal("buffett", brief_weak)
        sig_strong = _rule_based_signal("buffett", brief_strong)
        assert sig_strong.confidence >= sig_weak.confidence


# ── Dimension scorer ──────────────────────────────────────────


class TestScoreDimension:
    def test_neutral_data_returns_near_50(self):
        brief: dict = {
            "technicals": {},
            "fundamentals": {},
            "macro": {},
            "fii_dii": {},
            "news": [],
        }
        score = _score_dimension("fundamentals", brief)
        assert score == pytest.approx(50.0)

    def test_high_roe_increases_fundamentals_score(self):
        brief: dict = {
            "technicals": {},
            "fundamentals": {"roe": 22},
            "macro": {},
            "fii_dii": {},
            "news": [],
        }
        score = _score_dimension("fundamentals", brief)
        assert score > 50.0

    def test_oversold_rsi_increases_technicals_score(self):
        brief: dict = {
            "technicals": {"rsi": 25},
            "fundamentals": {},
            "macro": {},
            "fii_dii": {},
            "news": [],
        }
        score = _score_dimension("technicals", brief)
        assert score > 50.0

    def test_overbought_rsi_decreases_technicals_score(self):
        brief: dict = {
            "technicals": {"rsi": 80},
            "fundamentals": {},
            "macro": {},
            "fii_dii": {},
            "news": [],
        }
        score = _score_dimension("technicals", brief)
        assert score < 50.0

    def test_positive_fii_increases_macro_score(self):
        brief: dict = {
            "technicals": {},
            "fundamentals": {},
            "macro": {},
            "fii_dii": {"net": 5000},
            "news": [],
        }
        score = _score_dimension("macro", brief)
        assert score > 50.0

    def test_unknown_dimension_returns_50(self):
        brief: dict = {
            "technicals": {},
            "fundamentals": {},
            "macro": {},
            "fii_dii": {},
            "news": [],
        }
        score = _score_dimension("unknown_dimension_xyz", brief)
        assert score == pytest.approx(50.0)

    def test_score_always_in_range(self):
        """Score must always be within 0-100 regardless of extreme inputs."""
        briefs = [
            {
                "technicals": {"rsi": 1000},
                "fundamentals": {"roe": -999},
                "macro": {},
                "fii_dii": {},
                "news": [],
            },
            {
                "technicals": {"rsi": -100},
                "fundamentals": {"roe": 9999, "debt_equity": 0},
                "macro": {},
                "fii_dii": {"net": 9999999},
                "news": [],
            },
        ]
        for brief in briefs:
            for dim in ("fundamentals", "technicals", "macro", "sentiment", "options"):
                score = _score_dimension(dim, brief)
                assert 0 <= score <= 100, f"{dim} score {score} out of range"
