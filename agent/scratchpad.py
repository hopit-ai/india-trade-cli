"""
agent/scratchpad.py
───────────────────
Per-analysis scratchpad for tracking intermediate tool calls and results (#168).

Prevents context bloat by keeping a rolling log of tool calls within one analysis
session.  Old entries are compacted to a summary once the log exceeds a threshold,
so the effective working-memory stays small regardless of analysis depth.

Usage:
    pad = AnalysisScratchpad(symbol="INFY")
    pad.append("technical", "RSI=42, MACD bearish cross, support at 1620")
    pad.append("options", "Max pain 1650, PCR=0.8 bearish")
    context = pad.to_context_string()   # inject into LLM prompt

Compaction (auto at COMPACT_AFTER entries):
    pad.compact()   # or triggered automatically by append()
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# After this many entries, compact() is called automatically
COMPACT_AFTER: int = 8
# Keep this many recent entries verbatim after compaction
KEEP_RECENT: int = 3


@dataclass
class _Entry:
    """One tool-call result logged to the scratchpad."""

    tool: str
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat()[:19])


class AnalysisScratchpad:
    """
    Rolling per-analysis tool-call log with automatic compaction.

    Thread-safety: not thread-safe; designed for single-threaded analysis runs.
    """

    def __init__(self, symbol: str = "") -> None:
        self.symbol = symbol
        self._entries: list[_Entry] = []
        self._compact_summary: str = ""  # compressed history, replaced on each compact()
        self._compactions: int = 0

    # ── Public API ───────────────────────────────────────────────

    def append(self, tool: str, summary: str) -> None:
        """
        Record a tool call result.  Auto-compacts when log exceeds COMPACT_AFTER entries.

        Args:
            tool:    Name of the analyst or tool (e.g. "technical", "options", "news")
            summary: Short text summary of the result (will be truncated to 300 chars)
        """
        trimmed = summary.strip()[:300]
        self._entries.append(_Entry(tool=tool, summary=trimmed))
        if len(self._entries) >= COMPACT_AFTER:
            self.compact()

    def compact(self) -> None:
        """
        Compress all but the most recent KEEP_RECENT entries into a short summary.
        The summary replaces the previous compact_summary; recent entries are kept verbatim.
        """
        if len(self._entries) <= KEEP_RECENT:
            return

        to_compress = self._entries[:-KEEP_RECENT]
        keep = self._entries[-KEEP_RECENT:]

        # Build new compact summary from previous summary + entries being compressed
        parts: list[str] = []
        if self._compact_summary:
            parts.append(f"[Earlier summary] {self._compact_summary}")
        for e in to_compress:
            parts.append(f"{e.tool}: {e.summary[:120]}")

        self._compact_summary = "; ".join(parts)[:600]
        self._entries = keep
        self._compactions += 1

    def reset(self, symbol: str = "") -> None:
        """Start a fresh scratchpad (call between analysis runs)."""
        self.symbol = symbol or self.symbol
        self._entries = []
        self._compact_summary = ""
        self._compactions = 0

    def to_context_string(self) -> str:
        """
        Return formatted text suitable for injecting into an LLM prompt.
        Returns empty string when nothing has been logged.
        """
        if not self._entries and not self._compact_summary:
            return ""

        header = f"## Analysis Scratchpad ({self.symbol})"
        parts: list[str] = [header]

        if self._compact_summary:
            parts.append(
                textwrap.fill(
                    f"Earlier work (compacted): {self._compact_summary}",
                    width=100,
                    subsequent_indent="  ",
                )
            )
        if self._entries:
            parts.append("Recent tool results:")
            for e in self._entries:
                parts.append(f"  [{e.tool}] {e.summary}")

        return "\n".join(parts)

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries or self._compact_summary)


# ── Module-level singleton (per-session) ─────────────────────────
# One scratchpad per analysis run; reset between runs via scratchpad.reset(symbol)

analysis_scratchpad: AnalysisScratchpad = AnalysisScratchpad()


def get_scratchpad(symbol: Optional[str] = None) -> AnalysisScratchpad:
    """
    Return the module-level scratchpad, resetting it for a new symbol if provided.

    Call with symbol= at the start of each `analyze` run.
    Call without args to append results within the same run.
    """
    global analysis_scratchpad
    if symbol is not None and symbol != analysis_scratchpad.symbol:
        analysis_scratchpad.reset(symbol=symbol)
    return analysis_scratchpad
