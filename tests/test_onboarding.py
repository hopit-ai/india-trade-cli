"""
tests/test_onboarding.py
─────────────────────────
Tests for onboarding API endpoints (#135).
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Ensure clean env for each test
    for key in (
        "AI_PROVIDER",
        "NEWSAPI_KEY",
        "ONBOARDING_COMPLETE",
        "TOTAL_CAPITAL",
        "DEFAULT_RISK_PCT",
        "TRADING_MODE",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    # Self-hosted mode with empty auth DB — bypasses auth middleware
    monkeypatch.setenv("DEPLOY_MODE", "self-hosted")
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "test.db"))

    # Mock keychain to avoid picking up real credentials
    monkeypatch.setattr("config.credentials._kr_get", lambda key: None)

    from web.api import app

    return TestClient(app)


# ── /api/onboarding/status ────────────────────────────────────


class TestOnboardingStatus:
    def test_incomplete_when_no_provider(self, client, monkeypatch):
        monkeypatch.delenv("AI_PROVIDER", raising=False)
        monkeypatch.delenv("ONBOARDING_COMPLETE", raising=False)
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200
        d = r.json()
        assert d["onboarding_complete"] is False
        assert d["ai_provider"] == ""

    def test_complete_when_provider_set(self, client, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200
        d = r.json()
        assert d["onboarding_complete"] is True
        assert d["ai_provider"] == "gemini"

    def test_defaults_for_capital_and_risk(self, client, monkeypatch):
        monkeypatch.delenv("TOTAL_CAPITAL", raising=False)
        monkeypatch.delenv("DEFAULT_RISK_PCT", raising=False)
        r = client.get("/api/onboarding/status")
        d = r.json()
        assert d["capital"] == "200000"
        assert d["risk_pct"] == "2"
        assert d["trading_mode"] == "PAPER"

    def test_newsapi_key_detected(self, client, monkeypatch):
        monkeypatch.setenv("NEWSAPI_KEY", "test123")
        r = client.get("/api/onboarding/status")
        assert r.json()["newsapi_key_set"] is True

    def test_newsapi_key_missing(self, client, monkeypatch):
        monkeypatch.delenv("NEWSAPI_KEY", raising=False)
        r = client.get("/api/onboarding/status")
        assert r.json()["newsapi_key_set"] is False


# ── /api/onboarding/credential ────────────────────────────────


class TestOnboardingCredential:
    def test_sets_credential_in_env(self, client):
        r = client.post(
            "/api/onboarding/credential",
            json={"key": "AI_PROVIDER", "value": "anthropic"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert os.environ.get("AI_PROVIDER") == "anthropic"

    def test_sets_api_key(self, client):
        r = client.post(
            "/api/onboarding/credential",
            json={"key": "GEMINI_API_KEY", "value": "test_key_123"},
        )
        assert r.status_code == 200
        assert os.environ.get("GEMINI_API_KEY") == "test_key_123"


# ── /api/onboarding/test-provider ─────────────────────────────


class TestOnboardingTestProvider:
    def test_unknown_provider_returns_error(self, client):
        r = client.post(
            "/api/onboarding/test-provider",
            json={"provider": "nonexistent", "api_key": "x"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is False
        assert "Unknown" in r.json()["error"]

    @patch("httpx.AsyncClient.get")
    def test_ollama_check_when_running(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.1"}, {"name": "mistral"}]}
        mock_get.return_value = mock_response
        r = client.post(
            "/api/onboarding/test-provider",
            json={"provider": "ollama"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "2 model" in d["message"]


# ── /api/onboarding/test-newsapi ──────────────────────────────


class TestOnboardingTestNewsAPI:
    @patch("httpx.AsyncClient.get")
    def test_valid_key(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        r = client.post(
            "/api/onboarding/test-newsapi",
            json={"key": "valid_key_123"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    @patch("httpx.AsyncClient.get")
    def test_invalid_key(self, mock_get, client):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"status": "error"}
        mock_get.return_value = mock_response
        r = client.post(
            "/api/onboarding/test-newsapi",
            json={"key": "bad_key"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is False


# ── /api/onboarding/complete ──────────────────────────────────


class TestOnboardingComplete:
    def test_saves_settings(self, client, monkeypatch, tmp_path):
        # Mock the home dir for .env writing
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("NEWSAPI_KEY", "test")

        r = client.post(
            "/api/onboarding/complete",
            json={"capital": 500000, "risk_pct": 3, "trading_mode": "LIVE"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert os.environ.get("TOTAL_CAPITAL") == "500000"
        assert os.environ.get("DEFAULT_RISK_PCT") in ("3", "3.0")
        assert os.environ.get("TRADING_MODE") == "LIVE"
        assert os.environ.get("ONBOARDING_COMPLETE") == "1"

    def test_default_values(self, client, monkeypatch):
        r = client.post("/api/onboarding/complete", json={})
        assert r.status_code == 200
        assert os.environ.get("TOTAL_CAPITAL") == "200000"
        assert os.environ.get("DEFAULT_RISK_PCT") == "2"
        assert os.environ.get("TRADING_MODE") == "PAPER"


# ── /api/onboarding/setup-provider ────────────────────────────


class TestOnboardingSetupProvider:
    @patch("shutil.which")
    def test_ollama_check_not_installed(self, mock_which, client):
        mock_which.return_value = None
        r = client.post(
            "/api/onboarding/setup-provider",
            json={"provider": "ollama", "step": "check"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["installed"] is False
        assert d["next_step"] == "install"

    @patch("shutil.which")
    def test_ollama_install_no_brew(self, mock_which, client):
        mock_which.return_value = None
        r = client.post(
            "/api/onboarding/setup-provider",
            json={"provider": "ollama", "step": "install"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is False
        assert "Homebrew not found" in d["error"]

    @patch("shutil.which")
    def test_claude_sub_check_not_installed(self, mock_which, client):
        mock_which.return_value = None
        r = client.post(
            "/api/onboarding/setup-provider",
            json={"provider": "claude_subscription", "step": "check"},
        )
        assert r.status_code == 200
        d = r.json()
        assert d["installed"] is False
        assert d["next_step"] == "install"

    def test_unknown_provider(self, client):
        r = client.post(
            "/api/onboarding/setup-provider",
            json={"provider": "badprovider", "step": "check"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is False
