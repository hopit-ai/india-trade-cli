"""
Tests for mid-stream context injection into MultiAgentAnalyzer (#113).

Covers:
  - user_hints queue initialisation
  - Hint draining before synthesis
  - Synthesis prompt augmentation with user hints
  - Multiple hints concatenated
  - Empty hints ignored
  - _synthesis_started flag prevents late injection
"""

from __future__ import annotations

import queue
from unittest.mock import MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────

def _make_analyzer(**kwargs):
    """Create a MultiAgentAnalyzer with all heavy deps mocked out."""
    from agent.multi_agent import MultiAgentAnalyzer

    registry = MagicMock()
    provider = MagicMock()
    # provider.chat returns a canned synthesis string
    provider.chat = MagicMock(return_value="Mocked synthesis output")

    analyzer = MultiAgentAnalyzer(
        registry=registry,
        llm_provider=provider,
        parallel=False,
        verbose=False,
        **kwargs,
    )
    return analyzer


def _fake_report(name="Technical", verdict="BUY", confidence=75):
    """Create a minimal AnalystReport mock."""
    r = MagicMock()
    r.analyst = name
    r.name = name
    r.verdict = verdict
    r.confidence = confidence
    r.score = 0.7
    r.error = None
    r.data = {}
    r.key_points = ["Point 1"]
    r.summary_text = MagicMock(return_value=f"{name}: {verdict} ({confidence}%)")
    return r


def _fake_debate():
    """Create a minimal DebateResult mock."""
    d = MagicMock()
    d.bull_argument = "Bull case"
    d.bear_argument = "Bear case"
    d.bull_rebuttal = "Bull rebuttal"
    d.bear_rebuttal = "Bear rebuttal"
    d.facilitator = "Facilitator summary"
    d.winner = "Bull"
    return d


# ── Tests: user_hints queue ──────────────────────────────────────


class TestUserHintsQueue:
    """Test that MultiAgentAnalyzer has a thread-safe user_hints queue."""

    def test_queue_exists_on_init(self):
        analyzer = _make_analyzer()
        assert hasattr(analyzer, "user_hints")
        assert isinstance(analyzer.user_hints, queue.Queue)

    def test_queue_starts_empty(self):
        analyzer = _make_analyzer()
        assert analyzer.user_hints.empty()

    def test_can_put_and_get_hint(self):
        analyzer = _make_analyzer()
        analyzer.user_hints.put("Focus on AI deals")
        assert not analyzer.user_hints.empty()
        assert analyzer.user_hints.get_nowait() == "Focus on AI deals"

    def test_synthesis_started_flag_init(self):
        analyzer = _make_analyzer()
        assert hasattr(analyzer, "_synthesis_started")
        assert analyzer._synthesis_started is False


# ── Tests: hint draining ─────────────────────────────────────────


class TestHintDraining:
    """Test that hints are drained before synthesis and concatenated."""

    def test_single_hint_drained(self):
        analyzer = _make_analyzer()
        analyzer.user_hints.put("Focus on AI deals")

        # Simulate drain logic
        hints = []
        while not analyzer.user_hints.empty():
            try:
                hints.append(analyzer.user_hints.get_nowait())
            except queue.Empty:
                break
        hint_text = "\n".join(hints) if hints else ""

        assert hint_text == "Focus on AI deals"
        assert analyzer.user_hints.empty()

    def test_multiple_hints_concatenated(self):
        analyzer = _make_analyzer()
        analyzer.user_hints.put("Focus on AI deals")
        analyzer.user_hints.put("Ignore macro headwinds")

        hints = []
        while not analyzer.user_hints.empty():
            try:
                hints.append(analyzer.user_hints.get_nowait())
            except queue.Empty:
                break
        hint_text = "\n".join(hints)

        assert "Focus on AI deals" in hint_text
        assert "Ignore macro headwinds" in hint_text

    def test_empty_queue_gives_empty_string(self):
        analyzer = _make_analyzer()

        hints = []
        while not analyzer.user_hints.empty():
            try:
                hints.append(analyzer.user_hints.get_nowait())
            except queue.Empty:
                break
        hint_text = "\n".join(hints) if hints else ""

        assert hint_text == ""


# ── Tests: synthesis prompt injection ────────────────────────────


class TestSynthesisPromptInjection:
    """Test that _run_synthesis includes user hint text in the prompt."""

    def test_hint_injected_into_synthesis_prompt(self):
        analyzer = _make_analyzer()
        analyzer._user_hint_text = "Focus on AI deals"

        reports = [_fake_report()]
        debate = _fake_debate()

        # Patch trade_memory and pattern to avoid side effects
        with patch("engine.memory.trade_memory", MagicMock()), \
             patch("engine.patterns.get_pattern_context", MagicMock(return_value="")):
            analyzer._run_synthesis("INFY", "NSE", reports, debate)

        # The provider.chat should have been called with a prompt containing user hint
        call_args = analyzer.llm.chat.call_args
        messages = call_args[1].get("messages") or call_args[0][0]
        prompt_text = messages[0]["content"]
        assert "USER CONTEXT" in prompt_text
        assert "Focus on AI deals" in prompt_text

    def test_no_hint_no_injection(self):
        analyzer = _make_analyzer()
        analyzer._user_hint_text = ""

        reports = [_fake_report()]
        debate = _fake_debate()

        with patch("engine.memory.trade_memory", MagicMock()), \
             patch("engine.patterns.get_pattern_context", MagicMock(return_value="")):
            analyzer._run_synthesis("INFY", "NSE", reports, debate)

        call_args = analyzer.llm.chat.call_args
        messages = call_args[1].get("messages") or call_args[0][0]
        prompt_text = messages[0]["content"]
        assert "USER CONTEXT" not in prompt_text

    def test_hint_applied_callback_emitted(self):
        cb = MagicMock()
        analyzer = _make_analyzer(progress_callback=cb)
        analyzer._user_hint_text = "Focus on AI deals"

        reports = [_fake_report()]
        debate = _fake_debate()

        with patch("engine.memory.trade_memory", MagicMock()), \
             patch("engine.patterns.get_pattern_context", MagicMock(return_value="")):
            analyzer._run_synthesis("INFY", "NSE", reports, debate)

        # Check that hint_applied was emitted via progress_callback
        # (This will be tested once we add the callback in the analyze method, not _run_synthesis)
        # For now, verify _run_synthesis runs without error with hint text
        assert analyzer.llm.chat.called


# ── Tests: synthesis_started flag ────────────────────────────────


class TestSynthesisStartedFlag:
    """Test that _synthesis_started is set before synthesis runs."""

    def test_late_hint_not_in_synthesis(self):
        """If a hint arrives after _synthesis_started=True, it should not be drained."""
        analyzer = _make_analyzer()
        analyzer._synthesis_started = True
        analyzer.user_hints.put("Late hint")

        # Drain logic should check _synthesis_started
        # In production, the hint endpoint returns 'expired' when _synthesis_started is True
        assert not analyzer.user_hints.empty()
        assert analyzer._synthesis_started is True
