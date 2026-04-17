"""
Tests for GET/POST /skills/settings endpoints (#135).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "self-hosted")


@pytest.fixture
def client(mocker):
    mocker.patch("config.credentials.load_all", return_value={})
    mocker.patch("dotenv.load_dotenv")
    mocker.patch("web.api._require_localhost")
    mocker.patch("web.api.user_count", return_value=0)

    from fastapi.testclient import TestClient
    from web.api import app

    return TestClient(app)


class TestGetSettings:
    def test_endpoint_exists(self, client):
        resp = client.get("/skills/settings")
        assert resp.status_code == 200

    def test_returns_expected_keys(self, client, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "anthropic")
        monkeypatch.setenv("TRADING_MODE", "paper")
        monkeypatch.setenv("TRADING_CAPITAL", "150000")

        resp = client.get("/skills/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        cfg = data["data"]
        # Must expose these keys
        assert "ai_provider" in cfg
        assert "trading_mode" in cfg
        assert "trading_capital" in cfg

    def test_secrets_are_masked(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real-key-12345")
        monkeypatch.setenv("GEMINI_API_KEY", "AIza-real-key")

        resp = client.get("/skills/settings")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # API keys should NOT be exposed as plain text
        assert data.get("anthropic_api_key") != "sk-real-key-12345"
        assert data.get("gemini_api_key") != "AIza-real-key"

    def test_api_key_presence_flags(self, client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        resp = client.get("/skills/settings")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["anthropic_api_key_set"] is True
        assert data["openai_api_key_set"] is False


class TestPostSettings:
    def test_endpoint_exists(self, client, mocker):
        mocker.patch("config.credentials.set_credential")

        resp = client.post(
            "/skills/settings",
            json={"settings": {"AI_PROVIDER": "gemini"}},
        )
        assert resp.status_code == 200

    def test_updates_env_and_returns_updated_list(self, client, mocker):
        mock_set = mocker.patch("config.credentials.set_credential")

        resp = client.post(
            "/skills/settings",
            json={"settings": {"AI_PROVIDER": "gemini", "TRADING_MODE": "paper"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert set(data["data"]["updated"]) == {"AI_PROVIDER", "TRADING_MODE"}
        # set_credential should have been called for each key
        assert mock_set.call_count == 2

    def test_empty_settings_returns_empty_updated(self, client):
        resp = client.post("/skills/settings", json={"settings": {}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["updated"] == []

    def test_disallowed_key_returns_400(self, client):
        resp = client.post(
            "/skills/settings",
            json={"settings": {"SOME_UNKNOWN_KEY": "value"}},
        )
        assert resp.status_code == 400

    def test_missing_settings_field_returns_422(self, client):
        resp = client.post("/skills/settings", json={})
        assert resp.status_code == 422

    def test_capital_is_written_as_string(self, client, mocker):
        mock_set = mocker.patch("config.credentials.set_credential")

        resp = client.post(
            "/skills/settings",
            json={"settings": {"TRADING_CAPITAL": "250000"}},
        )
        assert resp.status_code == 200
        # Verify set_credential was called with the TRADING_CAPITAL key
        calls = {call.args[0]: call.args[1] for call in mock_set.call_args_list}
        assert "TRADING_CAPITAL" in calls
        assert calls["TRADING_CAPITAL"] == "250000"
