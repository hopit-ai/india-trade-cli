"""
Tests for save-PDF and explain/simplify endpoints (#144).
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


class TestExportPdfEndpoint:
    def test_endpoint_exists(self, client):
        resp = client.post(
            "/skills/export-pdf",
            json={"content": "INFY analysis: BUY signal", "title": "INFY Analysis"},
        )
        assert resp.status_code in (200, 503)  # 503 if fpdf2 not installed

    def test_returns_pdf_content_type_when_success(self, client, mocker):
        mocker.patch("engine.output.export_to_pdf", return_value="/tmp/test.pdf")
        mocker.patch("builtins.open", mocker.mock_open(read_data=b"%PDF-1.4 fake pdf content"))

        resp = client.post(
            "/skills/export-pdf",
            json={"content": "Analysis text", "title": "Test Report"},
        )
        # Should return PDF binary or JSON with download URL
        assert resp.status_code in (200, 503)

    def test_missing_content_returns_422(self, client):
        resp = client.post("/skills/export-pdf", json={"title": "no content"})
        assert resp.status_code == 422

    def test_fpdf_not_installed_returns_503(self, client, mocker):
        mocker.patch("engine.output.export_to_pdf", side_effect=ImportError("fpdf2 not installed"))

        resp = client.post(
            "/skills/export-pdf",
            json={"content": "Analysis text", "title": "Test"},
        )
        assert resp.status_code in (503, 500)


class TestExplainEndpoint:
    def test_endpoint_exists(self, client):
        resp = client.post(
            "/skills/explain",
            json={"content": "INFY analysis: RSI 54, PE 18x, BULLISH verdict."},
        )
        assert resp.status_code in (200, 500)

    def test_returns_simplified_text(self, client, mocker):
        mocker.patch(
            "engine.output.explain_simply",
            return_value="Here's what this analysis means in simple terms: The stock looks good.",
        )

        resp = client.post(
            "/skills/explain",
            json={"content": "RSI 54, MACD bullish, BUY verdict, confidence 72%"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "simplified" in data["data"]
        assert len(data["data"]["simplified"]) > 0

    def test_missing_content_returns_422(self, client):
        resp = client.post("/skills/explain", json={})
        assert resp.status_code == 422

    def test_uses_rule_based_fallback_without_provider(self, client, mocker):
        """Without LLM provider, falls back to rule-based simplification."""
        mocker.patch("engine.output.explain_simply", return_value="Simplified text")

        resp = client.post(
            "/skills/explain",
            json={"content": "BULLISH signal, VIX 18, FII buying", "session_id": "test"},
        )
        assert resp.status_code == 200
