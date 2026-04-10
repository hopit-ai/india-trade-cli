"""
tests/test_web_auth.py
───────────────────────
Tests for web auth system (#139).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    """TestClient with a fresh temp SQLite DB for each test."""
    db_path = tmp_path / "test_users.db"
    monkeypatch.setenv("AUTH_DB_PATH", str(db_path))
    monkeypatch.setenv("SESSION_SECRET", "test-secret-key")
    monkeypatch.setenv("DEPLOY_MODE", "self-hosted")
    # Prevent keychain loading from interfering
    monkeypatch.setattr("config.credentials._kr_get", lambda key: None)

    from web.api import app
    from web.auth import init_db, _sessions
    import web.auth

    # Point DB to temp path and init
    web.auth.DB_PATH = db_path
    init_db()
    _sessions.clear()

    return TestClient(app)


# ── Signup ────────────────────────────────────────────────────


class TestSignup:
    def test_signup_creates_user(self, client):
        r = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "securepass123"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["email"] == "test@example.com"
        # Should set session cookie
        assert "session_id" in r.cookies

    def test_signup_rejects_duplicate_email(self, client):
        client.post(
            "/auth/signup",
            json={"email": "dup@example.com", "password": "password123"},
        )
        r = client.post(
            "/auth/signup",
            json={"email": "dup@example.com", "password": "password456"},
        )
        assert r.status_code == 400
        assert "exists" in r.json()["detail"].lower()

    def test_signup_rejects_short_password(self, client):
        r = client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "123"},
        )
        assert r.status_code == 400

    def test_signup_rejects_invalid_email(self, client):
        r = client.post(
            "/auth/signup",
            json={"email": "notanemail", "password": "securepass123"},
        )
        assert r.status_code == 400


# ── Login ─────────────────────────────────────────────────────


class TestLogin:
    def test_login_with_valid_credentials(self, client):
        client.post(
            "/auth/signup",
            json={"email": "user@test.com", "password": "mypassword"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "user@test.com", "password": "mypassword"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert "session_id" in r.cookies

    def test_login_rejects_wrong_password(self, client):
        client.post(
            "/auth/signup",
            json={"email": "user@test.com", "password": "correct"},
        )
        r = client.post(
            "/auth/login",
            json={"email": "user@test.com", "password": "wrong"},
        )
        assert r.status_code == 401

    def test_login_rejects_nonexistent_user(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "nobody@test.com", "password": "whatever"},
        )
        assert r.status_code == 401


# ── Session / Me ──────────────────────────────────────────────


class TestSession:
    def test_me_returns_user_info(self, client):
        client.post(
            "/auth/signup",
            json={"email": "me@test.com", "password": "mypassword"},
        )
        r = client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "me@test.com"

    def test_me_returns_401_without_session(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_logout_clears_session(self, client):
        client.post(
            "/auth/signup",
            json={"email": "out@test.com", "password": "mypassword"},
        )
        r = client.post("/auth/logout")
        assert r.status_code == 200
        # After logout, /auth/me should fail
        r = client.get("/auth/me")
        assert r.status_code == 401


# ── Auth Middleware ────────────────────────────────────────────


class TestAuthMiddleware:
    def test_self_hosted_no_users_allows_access(self, client):
        """Self-hosted with no users bypasses auth (first-time setup)."""
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200

    def test_protected_route_requires_auth_after_signup(self, client):
        """Once a user exists, auth is enforced."""
        # Create a user so the bypass no longer applies
        client.post(
            "/auth/signup",
            json={"email": "first@test.com", "password": "mypassword"},
        )
        # Logout to clear session
        client.post("/auth/logout")
        # Now unauthenticated requests should fail
        r = client.get("/api/onboarding/status")
        assert r.status_code == 401

    def test_protected_route_works_with_auth(self, client):
        client.post(
            "/auth/signup",
            json={"email": "auth@test.com", "password": "mypassword"},
        )
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200

    def test_health_is_public(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_auth_endpoints_are_public(self, client):
        r = client.post(
            "/auth/login",
            json={"email": "x@x.com", "password": "xpassword"},
        )
        # Should return 401 (wrong creds), not 403 (no session)
        assert r.status_code == 401


# ── Static Serving ────────────────────────────────────────────


class TestStaticServing:
    def test_root_serves_something(self, client):
        r = client.get("/")
        # Either serves auth.html or index.html — should not 404
        assert r.status_code in (200, 307)
