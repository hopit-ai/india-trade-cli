"""
engine/tool_limiter.py
──────────────────────
Tracks tool calls per session and detects runaway loops.

Used by ToolRegistry.execute() to warn when tools are called excessively or
when an alternating loop (A-B-A-B-A-B) is detected.

The limiter never raises — it only returns warning strings or None.
The caller appends the warning as a prefix to the tool result.

Usage:
    from engine.tool_limiter import ToolLimiter

    limiter = ToolLimiter()
    warning = limiter.check_and_record("technical_analyse")
    if warning:
        result = f"[WARNING: {warning}] {result}"
"""

from __future__ import annotations

from collections import deque


class ToolLimiter:
    """Tracks tool calls per session and detects loops.

    Thread-safe for single-threaded use. Not intended for concurrent tool execution.
    """

    def __init__(self, soft_limit_per_tool: int = 5, hard_limit_total: int = 30) -> None:
        self.soft_limit_per_tool = soft_limit_per_tool
        self.hard_limit_total = hard_limit_total
        self._counts: dict[str, int] = {}
        self._recent: deque[str] = deque(maxlen=10)  # last 10 tool names for loop detection

    def check_and_record(self, tool_name: str) -> str | None:
        """
        Record a tool call. Returns a warning string if limits approached, None if fine.

        Detects:
        - Same tool called > soft_limit_per_tool times → warning
        - Last 6 calls alternate between same 2 tools → loop detected
        - Total calls > hard_limit_total → strong warning

        Returns:
            Warning string if a limit is hit, None otherwise.
        """
        # Record the call
        self._counts[tool_name] = self._counts.get(tool_name, 0) + 1
        self._recent.append(tool_name)

        total = sum(self._counts.values())
        count_for_tool = self._counts[tool_name]

        # Hard limit check (highest priority)
        if total > self.hard_limit_total:
            return (
                f"HARD LIMIT: {total} total tool calls this session exceeds "
                f"hard_limit_total={self.hard_limit_total}. "
                "Stop calling tools and synthesise your final answer now."
            )

        # Loop detection: check last 6 calls for A-B-A-B-A-B pattern
        loop_warning = self._detect_loop()
        if loop_warning:
            return loop_warning

        # Per-tool soft limit
        if count_for_tool > self.soft_limit_per_tool:
            return (
                f"SOFT LIMIT: '{tool_name}' called {count_for_tool}x this session "
                f"(soft_limit_per_tool={self.soft_limit_per_tool}). "
                "Consider whether you need to call it again."
            )

        return None

    def _detect_loop(self) -> str | None:
        """Detect A-B-A-B-A-B alternating loop in the last 6 tool calls."""
        recent = list(self._recent)
        if len(recent) < 6:
            return None

        last6 = recent[-6:]

        # Check for 2-tool alternating pattern: [A, B, A, B, A, B]
        a, b = last6[0], last6[1]
        if a == b:
            return None  # same tool repeated — different pattern

        pattern = True
        for i in range(6):
            expected = a if i % 2 == 0 else b
            if last6[i] != expected:
                pattern = False
                break

        if pattern:
            return (
                f"LOOP DETECTED: tools '{a}' and '{b}' are alternating repeatedly "
                f"({a}→{b}→{a}→{b}→{a}→{b}). This is likely a reasoning loop. "
                "Stop, review your data, and produce a final answer."
            )

        return None

    def get_summary(self) -> dict:
        """Return tool call counts and any detected issues."""
        total = sum(self._counts.values())
        issues = []

        for tool, count in self._counts.items():
            if count > self.soft_limit_per_tool:
                issues.append(f"{tool} called {count}x (soft limit: {self.soft_limit_per_tool})")

        if total > self.hard_limit_total:
            issues.append(f"Total {total} calls exceeds hard limit {self.hard_limit_total}")

        loop = self._detect_loop()
        if loop:
            issues.append("alternating loop detected")

        return {
            "total_calls": total,
            "by_tool": dict(self._counts),
            "issues": issues,
            "hard_limit_total": self.hard_limit_total,
            "soft_limit_per_tool": self.soft_limit_per_tool,
        }

    def reset(self) -> None:
        """Reset all counters for a new session."""
        self._counts.clear()
        self._recent.clear()
