"""
tests/test_risk_debate.py
─────────────────────────
Tests for the three-way risk debate (aggressive / conservative / neutral)
added to MultiAgentAnalyzer as Phase 2.5.

Covers:
  - RiskDebateResult dataclass fields
  - _run_risk_debate() calls correct prompts and returns RiskDebateResult
  - Risk debate skipped when scorecard verdict is HOLD
  - Risk debate runs when verdict is BUY / SELL / STRONG_BUY / STRONG_SELL
  - Synthesis prompt receives risk_debate_text when debate ran
  - Synthesis prompt receives empty risk_debate_text when debate skipped
  - AGGRESSIVE / CONSERVATIVE / NEUTRAL prompt templates contain key phrases
  - Full analyze() pipeline integration (mocked LLM)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent.multi_agent import (
    RiskDebateResult,
    DebateResult,
    AnalystReport,
    AnalystScorecard,
    MultiAgentAnalyzer,
    AGGRESSIVE_DEBATER_PROMPT,
    CONSERVATIVE_DEBATER_PROMPT,
    NEUTRAL_DEBATER_PROMPT,
    SYNTHESIS_PROMPT,
)


# ── Fixtures ──────────────────────────────────────────────────


def _make_scorecard(verdict: str = "BUY") -> AnalystScorecard:
    return AnalystScorecard(
        verdict=verdict,
        weighted_total=10.0,
        agreement=75.0,
        scores={"Technical": 5.0, "Fundamental": 5.0},
        weights={"Technical": 0.5, "Fundamental": 0.5},
    )


def _make_debate() -> DebateResult:
    return DebateResult(
        bull_argument="Strong bull case",
        bear_argument="Moderate bear case",
        bull_rebuttal="Bull rebuts",
        bear_rebuttal="Bear final",
        facilitator="WINNER: BULL",
        winner="BULL",
        rounds=2,
    )


def _make_report(analyst: str = "Technical", verdict: str = "BULLISH") -> AnalystReport:
    return AnalystReport(
        analyst=analyst,
        verdict=verdict,
        score=5.0,
        confidence=70,
        key_points=["key point"],
        data={},
    )


def _make_mock_llm(responses: list[str] | None = None) -> MagicMock:
    """Return a mock LLM provider whose chat() returns responses in sequence."""
    mock = MagicMock()
    if responses:
        mock.chat.side_effect = responses
    else:
        mock.chat.return_value = "mock LLM response"
    return mock


# ── RiskDebateResult dataclass ────────────────────────────────


class TestRiskDebateResultDataclass:
    def test_required_fields(self):
        r = RiskDebateResult(
            aggressive_view="go big",
            conservative_view="go small",
            neutral_view="go medium",
        )
        assert r.aggressive_view == "go big"
        assert r.conservative_view == "go small"
        assert r.neutral_view == "go medium"

    def test_consensus_defaults_to_empty(self):
        r = RiskDebateResult(
            aggressive_view="a",
            conservative_view="b",
            neutral_view="c",
        )
        assert r.consensus == ""

    def test_consensus_set_explicitly(self):
        r = RiskDebateResult(
            aggressive_view="a",
            conservative_view="b",
            neutral_view="c",
            consensus="5% capital, SL at 2300",
        )
        assert r.consensus == "5% capital, SL at 2300"


# ── Prompt template sanity ────────────────────────────────────


class TestRiskDebatePrompts:
    def test_aggressive_prompt_contains_key_themes(self):
        rendered = AGGRESSIVE_DEBATER_PROMPT.format(
            symbol="RELIANCE",
            exchange="NSE",
            scorecard="BUY 75%",
            debate_summary="WINNER: BULL",
            risk_params="Capital: ₹2L | VIX: 14",
        )
        assert "AGGRESSIVE" in rendered
        assert "position size" in rendered.lower()
        assert "stop" in rendered.lower()

    def test_conservative_prompt_contains_key_themes(self):
        rendered = CONSERVATIVE_DEBATER_PROMPT.format(
            symbol="RELIANCE",
            exchange="NSE",
            scorecard="BUY 75%",
            debate_summary="WINNER: BULL",
            risk_params="Capital: ₹2L | VIX: 14",
        )
        assert "CONSERVATIVE" in rendered
        assert "hedge" in rendered.lower()
        assert "capital" in rendered.lower()

    def test_neutral_prompt_includes_both_views(self):
        rendered = NEUTRAL_DEBATER_PROMPT.format(
            symbol="RELIANCE",
            exchange="NSE",
            scorecard="BUY 75%",
            debate_summary="WINNER: BULL",
            risk_params="Capital: ₹2L | VIX: 14",
            aggressive_view="go big",
            conservative_view="go small",
        )
        assert "go big" in rendered
        assert "go small" in rendered
        assert "NEUTRAL" in rendered

    def test_synthesis_prompt_has_risk_debate_placeholder(self):
        assert "{risk_debate_text}" in SYNTHESIS_PROMPT


# ── _run_risk_debate() ────────────────────────────────────────


class TestRunRiskDebate:
    def _make_analyzer(self, llm_responses=None):
        mock_registry = MagicMock()
        mock_llm = _make_mock_llm(llm_responses or ["aggressive", "conservative", "neutral"])
        analyzer = MultiAgentAnalyzer.__new__(MultiAgentAnalyzer)
        analyzer.registry = mock_registry
        analyzer.llm = mock_llm
        analyzer.verbose = False
        return analyzer, mock_llm

    def test_returns_risk_debate_result(self):
        analyzer, _ = self._make_analyzer()
        result = analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert isinstance(result, RiskDebateResult)

    def test_calls_llm_three_times(self):
        analyzer, mock_llm = self._make_analyzer()
        analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert mock_llm.chat.call_count == 3

    def test_aggressive_view_from_first_call(self):
        analyzer, _ = self._make_analyzer(["aggressive_resp", "conservative_resp", "neutral_resp"])
        result = analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert result.aggressive_view == "aggressive_resp"

    def test_conservative_view_from_second_call(self):
        analyzer, _ = self._make_analyzer(["a", "conservative_resp", "n"])
        result = analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert result.conservative_view == "conservative_resp"

    def test_neutral_view_from_third_call(self):
        analyzer, _ = self._make_analyzer(["a", "c", "neutral_resp"])
        result = analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert result.neutral_view == "neutral_resp"

    def test_consensus_is_first_line_of_neutral_view(self):
        neutral = "5% capital, SL at ₹2300\nmore detail here"
        analyzer, _ = self._make_analyzer(["a", "c", neutral])
        result = analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        assert result.consensus == "5% capital, SL at ₹2300"

    def test_neutral_prompt_includes_aggressive_and_conservative_views(self):
        analyzer, mock_llm = self._make_analyzer(["agg_view", "cons_view", "neutral_view"])
        analyzer._run_risk_debate(
            "RELIANCE",
            "NSE",
            _make_scorecard("BUY"),
            _make_debate(),
            [_make_report()],
        )
        # Third call (neutral) should include the first two views
        third_call_content = mock_llm.chat.call_args_list[2][1]["messages"][0]["content"]
        assert "agg_view" in third_call_content
        assert "cons_view" in third_call_content


# ── Risk debate skipped on HOLD ───────────────────────────────


class TestRiskDebateSkippedOnHold:
    def _build_analyzer(self, verdict: str, risk_debate_flag: bool = True):
        """Build an analyzer with all sub-phases mocked so we can inspect calls."""
        mock_registry = MagicMock()
        mock_llm = _make_mock_llm()
        analyzer = MultiAgentAnalyzer.__new__(MultiAgentAnalyzer)
        analyzer.registry = mock_registry
        analyzer.llm = mock_llm
        analyzer.parallel = False
        analyzer.verbose = False
        analyzer.risk_debate = risk_debate_flag
        analyzer.analysts = []
        analyzer.last_trade_plans = {}
        return analyzer

    def test_risk_debate_not_called_when_hold(self):
        """Risk debate skipped when verdict is HOLD even if flag is on."""
        analyzer = self._build_analyzer("HOLD", risk_debate_flag=True)
        scorecard = _make_scorecard("HOLD")
        debate = _make_debate()
        reports = [_make_report()]

        with (
            patch.object(analyzer, "_run_risk_debate") as mock_risk,
            patch.object(analyzer, "_run_synthesis", return_value="synthesis"),
            patch.object(analyzer, "_run_analysts", return_value=reports),
            patch.object(analyzer, "_run_debate", return_value=debate),
            patch.object(analyzer, "_print_analyst_summary"),
            patch.object(analyzer, "_print_debate"),
            patch("agent.multi_agent.compute_scorecard", return_value=scorecard),
            patch("agent.multi_agent.console"),
            patch("engine.memory.trade_memory.store_from_analysis"),
        ):
            analyzer.analyze("RELIANCE")

        mock_risk.assert_not_called()

    def test_risk_debate_not_called_when_flag_off(self):
        """Risk debate skipped when flag is False, even with a BUY verdict."""
        analyzer = self._build_analyzer("BUY", risk_debate_flag=False)
        scorecard = _make_scorecard("BUY")
        debate = _make_debate()
        reports = [_make_report()]

        with (
            patch.object(analyzer, "_run_risk_debate") as mock_risk,
            patch.object(analyzer, "_run_synthesis", return_value="synthesis"),
            patch.object(analyzer, "_run_analysts", return_value=reports),
            patch.object(analyzer, "_run_debate", return_value=debate),
            patch.object(analyzer, "_print_analyst_summary"),
            patch.object(analyzer, "_print_debate"),
            patch("agent.multi_agent.compute_scorecard", return_value=scorecard),
            patch("agent.multi_agent.console"),
            patch("engine.memory.trade_memory.store_from_analysis"),
        ):
            analyzer.analyze("RELIANCE")

        mock_risk.assert_not_called()

    @pytest.mark.parametrize("verdict", ["BUY", "SELL", "STRONG_BUY", "STRONG_SELL"])
    def test_risk_debate_called_when_flag_on_and_non_hold(self, verdict):
        """Risk debate runs when flag=True and verdict is not HOLD."""
        analyzer = self._build_analyzer(verdict, risk_debate_flag=True)
        scorecard = _make_scorecard(verdict)
        debate = _make_debate()
        reports = [_make_report()]
        mock_risk_result = RiskDebateResult("a", "c", "n", "consensus")

        with (
            patch.object(analyzer, "_run_risk_debate", return_value=mock_risk_result) as mock_risk,
            patch.object(analyzer, "_run_synthesis", return_value="synthesis"),
            patch.object(analyzer, "_run_analysts", return_value=reports),
            patch.object(analyzer, "_run_debate", return_value=debate),
            patch.object(analyzer, "_print_analyst_summary"),
            patch.object(analyzer, "_print_debate"),
            patch("agent.multi_agent.compute_scorecard", return_value=scorecard),
            patch("agent.multi_agent.console"),
            patch("engine.memory.trade_memory.store_from_analysis"),
        ):
            analyzer.analyze("RELIANCE")

        mock_risk.assert_called_once()


# ── _run_synthesis receives risk debate text ──────────────────


class TestSynthesisReceivesRiskDebate:
    def _make_analyzer(self):
        mock_registry = MagicMock()
        mock_llm = _make_mock_llm()
        analyzer = MultiAgentAnalyzer.__new__(MultiAgentAnalyzer)
        analyzer.registry = mock_registry
        analyzer.llm = mock_llm
        analyzer.verbose = False
        return analyzer

    def test_synthesis_prompt_includes_risk_views_when_debate_ran(self):
        analyzer = self._make_analyzer()
        risk_debate = RiskDebateResult(
            aggressive_view="go big",
            conservative_view="go small",
            neutral_view="go medium",
        )
        reports = [_make_report("Risk Manager", "NEUTRAL")]
        reports[0].data = {}

        with (
            patch("engine.memory.trade_memory.get_context_for_symbol", return_value=""),
            patch("engine.patterns.get_pattern_context", return_value=""),
        ):
            analyzer._run_synthesis("RELIANCE", "NSE", reports, _make_debate(), risk_debate)

        call_content = analyzer.llm.chat.call_args[1]["messages"][0]["content"]
        assert "go big" in call_content
        assert "go small" in call_content
        assert "go medium" in call_content

    def test_synthesis_prompt_risk_section_empty_when_no_debate(self):
        analyzer = self._make_analyzer()
        reports = [_make_report("Risk Manager", "NEUTRAL")]
        reports[0].data = {}

        with (
            patch("engine.memory.trade_memory.get_context_for_symbol", return_value=""),
            patch("engine.patterns.get_pattern_context", return_value=""),
        ):
            analyzer._run_synthesis("RELIANCE", "NSE", reports, _make_debate(), None)

        call_content = analyzer.llm.chat.call_args[1]["messages"][0]["content"]
        # Section header still present but content is empty
        assert "Risk Team Debate" in call_content
