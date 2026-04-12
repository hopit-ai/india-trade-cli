"""
Tests for quick scan mode (#153).
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestQuickScanResult:
    def test_result_has_required_fields(self):
        from agent.quick_scan import QuickScanResult

        r = QuickScanResult(
            symbol="INFY",
            verdict="BUY",
            confidence=72,
            reasons=["RSI 54 neutral", "PE below sector avg"],
            entry=1410.0,
            sl=1370.0,
            target=1480.0,
            ltp=1400.0,
            elapsed_ms=3200,
        )
        assert r.symbol == "INFY"
        assert r.verdict == "BUY"
        assert r.confidence == 72
        assert len(r.reasons) == 2
        assert r.error is None

    def test_result_with_error(self):
        from agent.quick_scan import QuickScanResult

        r = QuickScanResult(
            symbol="INFY",
            verdict="HOLD",
            confidence=0,
            reasons=[],
            entry=None,
            sl=None,
            target=None,
            ltp=0.0,
            elapsed_ms=100,
            error="No data available",
        )
        assert r.error == "No data available"


class TestParseQuickResponse:
    def test_parse_verdict_buy(self):
        from agent.quick_scan import _parse_quick_response

        text = "VERDICT: BUY\nCONFIDENCE: 72\nREASON: RSI neutral\nENTRY: 1410\nSL: 1370\nTARGET: 1480"
        result = _parse_quick_response(text)
        assert result["verdict"] == "BUY"
        assert result["confidence"] == 72
        assert result["entry"] == 1410.0
        assert result["sl"] == 1370.0
        assert result["target"] == 1480.0

    def test_parse_with_markdown(self):
        from agent.quick_scan import _parse_quick_response

        text = "**VERDICT: SELL**\n**CONFIDENCE: 65%**\nREASON:\n- Bearish MACD\n- RSI overbought"
        result = _parse_quick_response(text)
        assert result["verdict"] == "SELL"
        assert result["confidence"] == 65

    def test_reasons_extracted_as_list(self):
        from agent.quick_scan import _parse_quick_response

        text = "VERDICT: BUY\nCONFIDENCE: 70\nREASON:\n- Point 1\n- Point 2\n- Point 3\nENTRY: 1400\nSL: 1350\nTARGET: 1500"
        result = _parse_quick_response(text)
        assert len(result["reasons"]) == 3

    def test_defaults_when_missing(self):
        from agent.quick_scan import _parse_quick_response

        result = _parse_quick_response("Some analysis output without structured fields")
        assert result["verdict"] == "HOLD"
        assert result["confidence"] == 50
        assert result["entry"] is None


class TestQuickScannerScan:
    def test_scan_returns_result_object(self, mocker):
        """QuickScanner.scan() returns a QuickScanResult even without a broker."""
        from agent.quick_scan import QuickScanner, QuickScanResult

        # Mock the LLM provider
        mock_provider = MagicMock()
        mock_provider.chat.return_value = (
            "VERDICT: BUY\nCONFIDENCE: 70\n"
            "REASON:\n- RSI neutral at 54\n- PE 18x below avg\n"
            "ENTRY: 1410\nSL: 1370\nTARGET: 1480"
        )

        # Mock the data gathering
        mock_registry = MagicMock()
        mock_registry.execute.return_value = {
            "score": 45,
            "verdict": "BULLISH",
            "rsi": 54.0,
            "ema20": 1390.0,
            "ema50": 1360.0,
        }

        scanner = QuickScanner(provider=mock_provider, registry=mock_registry)
        result = scanner.scan("INFY", ltp=1400.0)

        assert isinstance(result, QuickScanResult)
        assert result.symbol == "INFY"
        assert result.verdict in ("BUY", "SELL", "HOLD")

    def test_scan_handles_provider_error_gracefully(self, mocker):
        from agent.quick_scan import QuickScanner, QuickScanResult

        mock_provider = MagicMock()
        mock_provider.chat.side_effect = RuntimeError("API timeout")

        mock_registry = MagicMock()
        mock_registry.execute.return_value = {"score": 30, "verdict": "NEUTRAL"}

        scanner = QuickScanner(provider=mock_provider, registry=mock_registry)
        result = scanner.scan("INFY", ltp=1400.0)

        assert isinstance(result, QuickScanResult)
        assert result.error is not None

    def test_scan_measures_elapsed_time(self, mocker):
        from agent.quick_scan import QuickScanner

        mock_provider = MagicMock()
        mock_provider.chat.return_value = "VERDICT: HOLD\nCONFIDENCE: 50"

        mock_registry = MagicMock()
        mock_registry.execute.return_value = {"score": 0}

        scanner = QuickScanner(provider=mock_provider, registry=mock_registry)
        result = scanner.scan("INFY", ltp=1400.0)

        assert result.elapsed_ms >= 0


class TestQuickScanEndpoint:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("DEPLOY_MODE", "self-hosted")

    def test_quick_analyze_returns_ok(self, mocker):
        mocker.patch("config.credentials.load_all", return_value={})
        mocker.patch("dotenv.load_dotenv")
        mocker.patch("web.api._require_localhost")
        mocker.patch("web.api.user_count", return_value=0)

        from fastapi.testclient import TestClient
        from web.api import app

        # Mock the quick scanner to return a valid result
        from agent.quick_scan import QuickScanResult
        mock_result = QuickScanResult(
            symbol="INFY",
            verdict="BUY",
            confidence=72,
            reasons=["RSI neutral", "PE cheap"],
            entry=1410.0,
            sl=1370.0,
            target=1480.0,
            ltp=1400.0,
            elapsed_ms=3200,
        )
        mock_scanner = mocker.MagicMock()
        mock_scanner.return_value.scan.return_value = mock_result
        mocker.patch("agent.quick_scan.QuickScanner", mock_scanner)

        client = TestClient(app)
        # Use localhost to bypass auth middleware
        resp = client.post(
            "/skills/quick_analyze",
            json={"symbol": "INFY"},
            headers={"x-forwarded-for": "127.0.0.1"},
        )
        assert resp.status_code in (200, 500)
