"""
Tests for the /skills/analyze/hint endpoint and _active_streams lifecycle (#113).

Covers:
  - POST /skills/analyze/hint with active stream → queued
  - POST /skills/analyze/hint with expired stream → expired
  - POST /skills/analyze/hint when synthesis already started → expired
  - _active_streams registration and cleanup
"""

from __future__ import annotations

import asyncio
import queue
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── App fixture ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with broker/keychain/dotenv loading suppressed."""
    import os

    os.environ["DEPLOY_MODE"] = "self-hosted"
    os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app

        yield TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────


def _mock_analyzer(synthesis_started=False):
    """Create a mock analyzer with user_hints queue and _synthesis_started flag."""
    analyzer = MagicMock()
    analyzer.user_hints = queue.Queue()
    analyzer._synthesis_started = synthesis_started
    analyzer.progress_callback = MagicMock()
    return analyzer


# ── Tests: hint endpoint ─────────────────────────────────────────


class TestHintEndpoint:
    """Tests for POST /skills/analyze/hint."""

    def test_hint_queued_to_active_stream(self, client):
        """Hint should be queued when stream is active."""
        analyzer = _mock_analyzer()

        with patch("web.skills._active_streams", {"INFY_NSE_abc123": analyzer}):
            resp = client.post(
                "/skills/analyze/hint",
                json={"stream_id": "INFY_NSE_abc123", "hint": "Focus on AI deals"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert not analyzer.user_hints.empty()
        assert analyzer.user_hints.get_nowait() == "Focus on AI deals"

    def test_hint_expired_stream(self, client):
        """Hint should return expired when stream doesn't exist."""
        with patch("web.skills._active_streams", {}):
            resp = client.post(
                "/skills/analyze/hint",
                json={"stream_id": "INFY_NSE_gone", "hint": "Focus on AI deals"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "expired"

    def test_hint_expired_when_synthesis_started(self, client):
        """Hint should return expired when synthesis has already started."""
        analyzer = _mock_analyzer(synthesis_started=True)

        with patch("web.skills._active_streams", {"INFY_NSE_abc123": analyzer}):
            resp = client.post(
                "/skills/analyze/hint",
                json={"stream_id": "INFY_NSE_abc123", "hint": "Focus on AI deals"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "expired"
        # Hint should NOT be in the queue
        assert analyzer.user_hints.empty()

    def test_hint_ack_callback_emitted(self, client):
        """progress_callback should emit hint_ack when hint is queued."""
        analyzer = _mock_analyzer()

        with patch("web.skills._active_streams", {"INFY_NSE_abc123": analyzer}):
            client.post(
                "/skills/analyze/hint",
                json={"stream_id": "INFY_NSE_abc123", "hint": "Focus on AI deals"},
            )

        analyzer.progress_callback.assert_called_once_with(
            {"type": "hint_ack", "hint": "Focus on AI deals"}
        )

    def test_empty_hint_ignored(self, client):
        """Empty or whitespace-only hint should not be queued."""
        analyzer = _mock_analyzer()

        with patch("web.skills._active_streams", {"INFY_NSE_abc123": analyzer}):
            resp = client.post(
                "/skills/analyze/hint",
                json={"stream_id": "INFY_NSE_abc123", "hint": "   "},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert analyzer.user_hints.empty()


# ── Tests: _active_streams lifecycle ─────────────────────────────


class TestActiveStreamsLifecycle:
    """Tests for _active_streams registration and cleanup."""

    def test_stream_registered_and_removed(self):
        """Verify that _active_streams dict supports register + cleanup pattern."""
        from web.skills import _active_streams

        analyzer = _mock_analyzer()
        stream_id = "TEST_NSE_xyz789"

        # Register
        _active_streams[stream_id] = analyzer
        assert stream_id in _active_streams

        # Cleanup
        _active_streams.pop(stream_id, None)
        assert stream_id not in _active_streams

    def test_pop_missing_stream_is_safe(self):
        """Popping a non-existent stream_id should not raise."""
        from web.skills import _active_streams

        result = _active_streams.pop("nonexistent_stream", None)
        assert result is None
