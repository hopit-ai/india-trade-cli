"""
Tests for multi-session chat (#110).

Verifies that different session_ids get independent TradingAgent instances
and that resetting one session doesn't affect another.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ["DEPLOY_MODE"] = "self-hosted"
    os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app

        yield TestClient(app)


@pytest.fixture(autouse=True)
def clean_sessions():
    """Clear chat sessions between tests."""
    from web.skills import _chat_sessions

    _chat_sessions.clear()
    yield
    _chat_sessions.clear()


def _mock_agent():
    agent = MagicMock()
    agent.chat = MagicMock(return_value="mock response")
    agent._history = [{"role": "user", "content": "test"}]
    return agent


def test_chat_session_id_independent(client):
    """Two different session_ids should get independent TradingAgents."""
    from web.skills import _chat_sessions

    # Pre-populate sessions with mock agents (avoids needing real LLM)
    _chat_sessions["session-a"] = _mock_agent()
    _chat_sessions["session-b"] = _mock_agent()

    resp_a = client.post(
        "/skills/chat",
        json={"message": "hello from A", "session_id": "session-a"},
    )
    assert resp_a.status_code == 200

    resp_b = client.post(
        "/skills/chat",
        json={"message": "hello from B", "session_id": "session-b"},
    )
    assert resp_b.status_code == 200

    # Both sessions exist and are different objects
    assert _chat_sessions["session-a"] is not _chat_sessions["session-b"]

    # Each agent was called with the right message
    _chat_sessions["session-a"].chat.assert_called_with("hello from A")
    _chat_sessions["session-b"].chat.assert_called_with("hello from B")


def test_chat_reset_clears_session(client):
    """Resetting one session should not affect another."""
    from web.skills import _chat_sessions

    _chat_sessions["session-a"] = _mock_agent()
    _chat_sessions["session-b"] = _mock_agent()

    # Reset session A
    resp = client.post("/skills/chat/reset", json={"session_id": "session-a"})
    assert resp.status_code == 200

    # Session A should be gone, session B should remain
    assert "session-a" not in _chat_sessions
    assert "session-b" in _chat_sessions
