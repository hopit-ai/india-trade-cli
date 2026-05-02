"""
Tests for soft tool limiting and loop detection (#177).
"""

from __future__ import annotations

import pytest


class TestSoftLimitWarning:
    def test_no_warning_below_soft_limit(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=5, hard_limit_total=30)
        # Call 5 times — no warning on 5th call (limit is >5 i.e. 6th call triggers)
        for i in range(5):
            result = limiter.check_and_record("technical_analyse")
        assert result is None

    def test_warning_triggered_above_soft_limit(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=5, hard_limit_total=30)
        for i in range(6):
            result = limiter.check_and_record("technical_analyse")
        # 6th call should trigger warning
        assert result is not None
        assert "technical_analyse" in result
        assert "SOFT LIMIT" in result

    def test_soft_limit_custom_threshold(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=2, hard_limit_total=30)
        limiter.check_and_record("get_quote")
        limiter.check_and_record("get_quote")
        result = limiter.check_and_record("get_quote")  # 3rd call = > 2
        assert result is not None
        assert "SOFT LIMIT" in result

    def test_different_tools_independent_counts(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=5, hard_limit_total=30)
        # Call tool A 5 times — no warning
        for _ in range(5):
            limiter.check_and_record("tool_a")
        # Call tool B 5 times — no warning
        for _ in range(5):
            result = limiter.check_and_record("tool_b")
        assert result is None


class TestLoopDetection:
    def test_alternating_ab_loop_detected(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=10, hard_limit_total=50)
        # A-B-A-B-A-B pattern
        tools = ["tool_a", "tool_b"] * 3
        result = None
        for t in tools:
            result = limiter.check_and_record(t)
        # Should detect loop on 6th call
        assert result is not None
        assert "LOOP DETECTED" in result
        assert "tool_a" in result
        assert "tool_b" in result

    def test_no_loop_with_three_tools(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=10, hard_limit_total=50)
        # A-B-C-A-B-C pattern — not a 2-tool alternation
        tools = ["tool_a", "tool_b", "tool_c"] * 2
        result = None
        for t in tools:
            result = limiter.check_and_record(t)
        # No loop warning (3 tools, not 2)
        assert result is None

    def test_no_loop_with_same_tool_repeated(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=10, hard_limit_total=50)
        # Same tool 6 times — soft limit, not loop
        for _ in range(6):
            result = limiter.check_and_record("same_tool")
        # Should be soft limit warning, not loop
        assert result is not None
        assert "LOOP DETECTED" not in result

    def test_loop_requires_exactly_6_alternating(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=10, hard_limit_total=50)
        # Only 4 alternating calls — not enough for loop detection
        tools = ["tool_a", "tool_b"] * 2
        result = None
        for t in tools:
            result = limiter.check_and_record(t)
        # No loop detected yet (need 6)
        assert result is None or "LOOP" not in result


class TestHardLimit:
    def test_hard_limit_warning(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=100, hard_limit_total=5)
        for i in range(6):
            result = limiter.check_and_record(f"tool_{i}")
        assert result is not None
        assert "HARD LIMIT" in result

    def test_hard_limit_overrides_soft_limit(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=3, hard_limit_total=4)
        # Call 5 times — hard limit (4) triggers first
        for _ in range(5):
            result = limiter.check_and_record("tool_a")
        assert "HARD LIMIT" in result


class TestReset:
    def test_reset_clears_counts(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=5, hard_limit_total=30)
        for _ in range(6):
            limiter.check_and_record("tool_a")

        limiter.reset()
        # After reset, counts should be zero
        summary = limiter.get_summary()
        assert summary["total_calls"] == 0
        assert summary["by_tool"] == {}

    def test_reset_allows_fresh_start(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=5, hard_limit_total=30)
        for _ in range(6):
            limiter.check_and_record("tool_a")

        limiter.reset()
        # After reset, no warning for first 5 calls
        result = None
        for _ in range(5):
            result = limiter.check_and_record("tool_a")
        assert result is None

    def test_reset_clears_loop_history(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter(soft_limit_per_tool=10, hard_limit_total=50)
        # Build up a loop pattern
        for _ in range(3):
            limiter.check_and_record("tool_a")
            limiter.check_and_record("tool_b")

        limiter.reset()
        # After reset, alternating calls don't trigger loop immediately
        limiter.check_and_record("tool_a")
        limiter.check_and_record("tool_b")
        result = limiter.check_and_record("tool_a")
        assert result is None  # only 3 calls, not 6


class TestGetSummary:
    def test_summary_has_required_keys(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter()
        limiter.check_and_record("technical_analyse")
        limiter.check_and_record("fundamental_analyse")

        summary = limiter.get_summary()
        assert "total_calls" in summary
        assert "by_tool" in summary
        assert "issues" in summary

    def test_summary_counts_correctly(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter()
        limiter.check_and_record("tool_a")
        limiter.check_and_record("tool_a")
        limiter.check_and_record("tool_b")

        summary = limiter.get_summary()
        assert summary["total_calls"] == 3
        assert summary["by_tool"]["tool_a"] == 2
        assert summary["by_tool"]["tool_b"] == 1

    def test_summary_empty_initially(self):
        from engine.tool_limiter import ToolLimiter

        limiter = ToolLimiter()
        summary = limiter.get_summary()
        assert summary["total_calls"] == 0
        assert summary["issues"] == []


class TestToolRegistryIntegration:
    def test_limiter_wired_into_registry(self):
        """ToolRegistry should have a _limiter attribute."""
        from agent.tools import ToolRegistry

        registry = ToolRegistry()
        assert hasattr(registry, "_limiter")

    def test_warning_added_to_result_on_soft_limit(self):
        """Executing a tool many times should add _tool_warning to result."""
        from agent.tools import ToolRegistry

        registry = ToolRegistry()
        # Override the limiter with a very low limit for testing
        from engine.tool_limiter import ToolLimiter

        registry._limiter = ToolLimiter(soft_limit_per_tool=1, hard_limit_total=100)

        # Register a trivial tool
        registry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            fn=lambda: {"value": 42},
        )

        # First call — no warning
        result1 = registry.execute("test_tool", {})
        assert "_tool_warning" not in result1

        # Second call — exceeds soft limit of 1 → warning
        result2 = registry.execute("test_tool", {})
        assert "_tool_warning" in result2
        assert "SOFT LIMIT" in result2["_tool_warning"]
