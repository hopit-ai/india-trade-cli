"""
Tests for multi-session chat (#110).

Verifies that different session_ids get independent TradingAgent instances
and that resetting one session doesn't affect another.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from web.api import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_sessions():
    """Clear chat sessions between tests."""
    from web.skills import _chat_sessions

    _chat_sessions.clear()
    yield
    _chat_sessions.clear()


def test_chat_session_id_independent(client):
    """Two different session_ids should get independent TradingAgents."""
    from web.skills import _chat_sessions

    # Send a message on session A
    resp_a = client.post(
        "/skills/chat",
        json={
            "message": "hello from session A",
            "session_id": "session-a",
        },
    )
    assert resp_a.status_code == 200

    # Send a message on session B
    resp_b = client.post(
        "/skills/chat",
        json={
            "message": "hello from session B",
            "session_id": "session-b",
        },
    )
    assert resp_b.status_code == 200

    # Both sessions should exist as separate entries
    assert "session-a" in _chat_sessions
    assert "session-b" in _chat_sessions
    assert _chat_sessions["session-a"] is not _chat_sessions["session-b"]


def test_chat_reset_clears_session(client):
    """Resetting one session should not affect another."""
    from web.skills import _chat_sessions

    # Create two sessions
    client.post(
        "/skills/chat",
        json={
            "message": "hello A",
            "session_id": "session-a",
        },
    )
    client.post(
        "/skills/chat",
        json={
            "message": "hello B",
            "session_id": "session-b",
        },
    )
    assert "session-a" in _chat_sessions
    assert "session-b" in _chat_sessions

    # Reset session A
    resp = client.post("/skills/chat/reset", json={"session_id": "session-a"})
    assert resp.status_code == 200

    # Session A should be gone, session B should remain
    assert "session-a" not in _chat_sessions
    assert "session-b" in _chat_sessions
