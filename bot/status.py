"""
bot/status.py
─────────────
Thread-safe shared state for Telegram bot activity.

The REPL prompt reads `get_badge()` on every iteration to show a
persistent indicator when a Telegram command is being processed.
"""

from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
_active_command: Optional[str] = None  # e.g. "/analyze RELIANCE"
_pending_count: int = 0  # how many commands in flight


def set_active(command: str) -> None:
    """Mark a Telegram command as in-flight."""
    global _active_command, _pending_count
    with _lock:
        _active_command = command
        _pending_count += 1


def clear_active() -> None:
    """Mark a Telegram command as finished."""
    global _active_command, _pending_count
    with _lock:
        _pending_count = max(0, _pending_count - 1)
        if _pending_count == 0:
            _active_command = None


def get_badge() -> str:
    """
    Return a short status string for the REPL prompt.

    Returns "" when idle, or something like "📩 /analyze" when busy.
    """
    with _lock:
        if _pending_count == 0:
            return ""
        cmd = _active_command or "cmd"
        # Truncate long commands
        if len(cmd) > 20:
            cmd = cmd[:20] + "…"
        if _pending_count > 1:
            return f" 📩 {cmd} (+{_pending_count - 1})"
        return f" 📩 {cmd}"
