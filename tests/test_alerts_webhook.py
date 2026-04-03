"""
Tests for webhook additions to engine/alerts.py.

Covers:
  - webhook_url field on Alert dataclass
  - webhook_url param on add_price_alert / add_technical_alert / add_conditional_alert
  - _webhook_notify fires when alert triggers
  - Backward-compatibility: old JSON without webhook_url still loads cleanly
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from engine.alerts import (
    Alert,
    AlertManager,
    _webhook_notify,
    alert_manager,
)


# ── Alert dataclass ───────────────────────────────────────────

class TestAlertDataclass:
    def test_webhook_url_defaults_to_none(self):
        a = Alert(
            id="test01", alert_type="PRICE", symbol="RELIANCE",
            exchange="NSE", condition="ABOVE", threshold=2800.0,
        )
        assert a.webhook_url is None

    def test_webhook_url_stored(self):
        a = Alert(
            id="test02", alert_type="PRICE", symbol="TCS",
            exchange="NSE", condition="BELOW", threshold=3500.0,
            webhook_url="https://agent.example.com/callback",
        )
        assert a.webhook_url == "https://agent.example.com/callback"

    def test_backward_compat_load_without_webhook_url(self, tmp_path):
        """Alerts saved before webhook_url existed should load without error."""
        old_json = [
            {
                "id": "old001",
                "alert_type": "PRICE",
                "symbol": "INFY",
                "exchange": "NSE",
                "condition": "ABOVE",
                "threshold": 1600.0,
                "indicator": None,
                "message": "INFY price ABOVE ₹1,600.00",
                "created_at": "2025-12-01T09:00:00",
                "triggered": False,
                "triggered_at": None,
                "conditions": [],
                # NOTE: no webhook_url key — simulates old saved format
            }
        ]
        alerts_file = tmp_path / "alerts.json"
        alerts_file.write_text(json.dumps(old_json))

        with patch("engine.alerts.ALERTS_FILE", alerts_file):
            mgr = AlertManager()

        assert len(mgr._alerts) == 1
        assert mgr._alerts[0].webhook_url is None


# ── add_price_alert ───────────────────────────────────────────

class TestAddPriceAlertWebhook:
    def test_webhook_url_stored_on_price_alert(self, tmp_path):
        with patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"):
            mgr = AlertManager()
            alert = mgr.add_price_alert(
                symbol="RELIANCE", condition="ABOVE", threshold=2800.0,
                webhook_url="https://example.com/hook",
            )
        assert alert.webhook_url == "https://example.com/hook"
        assert alert.alert_type == "PRICE"

    def test_no_webhook_url_defaults_to_none(self, tmp_path):
        with patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"):
            mgr = AlertManager()
            alert = mgr.add_price_alert("RELIANCE", "ABOVE", 2800.0)
        assert alert.webhook_url is None

    def test_webhook_url_persisted_to_disk(self, tmp_path):
        alerts_file = tmp_path / "alerts.json"
        with patch("engine.alerts.ALERTS_FILE", alerts_file):
            mgr = AlertManager()
            mgr.add_price_alert(
                "RELIANCE", "ABOVE", 2800.0,
                webhook_url="https://example.com/hook",
            )
        saved = json.loads(alerts_file.read_text())
        assert saved[0]["webhook_url"] == "https://example.com/hook"


# ── add_technical_alert ───────────────────────────────────────

class TestAddTechnicalAlertWebhook:
    def test_webhook_url_stored(self, tmp_path):
        with patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"):
            mgr = AlertManager()
            alert = mgr.add_technical_alert(
                symbol="INFY", indicator="RSI", condition="ABOVE", threshold=70.0,
                webhook_url="https://example.com/rsi-hook",
            )
        assert alert.webhook_url == "https://example.com/rsi-hook"
        assert alert.alert_type == "TECHNICAL"

    def test_no_webhook_url_defaults_to_none(self, tmp_path):
        with patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"):
            mgr = AlertManager()
            alert = mgr.add_technical_alert("INFY", "RSI", "ABOVE", 70.0)
        assert alert.webhook_url is None


# ── add_conditional_alert ─────────────────────────────────────

class TestAddConditionalAlertWebhook:
    def test_webhook_url_stored(self, tmp_path):
        conditions = [
            {"condition_type": "PRICE",     "condition": "ABOVE", "threshold": 2800.0, "indicator": None},
            {"condition_type": "TECHNICAL", "condition": "ABOVE", "threshold": 60.0,   "indicator": "RSI"},
        ]
        with patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"):
            mgr = AlertManager()
            alert = mgr.add_conditional_alert(
                symbol="RELIANCE", conditions=conditions,
                webhook_url="https://example.com/cond-hook",
            )
        assert alert.webhook_url == "https://example.com/cond-hook"
        assert alert.alert_type == "CONDITIONAL"


# ── _webhook_notify ───────────────────────────────────────────

class TestWebhookNotify:
    def test_posts_to_webhook_url(self):
        alert = Alert(
            id="wh001", alert_type="PRICE", symbol="RELIANCE",
            exchange="NSE", condition="ABOVE", threshold=2800.0,
            triggered=True, triggered_at="2026-04-03T11:00:00",
            webhook_url="https://example.com/callback",
        )

        posted = []

        class FakeResponse:
            pass

        def fake_urlopen(req, timeout=10):
            posted.append({
                "url": req.full_url,
                "body": json.loads(req.data),
            })
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _webhook_notify(alert, ltp=2855.0)
            time.sleep(0.1)  # let background thread finish

        assert len(posted) == 1
        payload = posted[0]["body"]
        assert payload["event"] == "alert_triggered"
        assert payload["alert_id"] == "wh001"
        assert payload["symbol"] == "RELIANCE"
        assert payload["ltp"] == 2855.0
        assert posted[0]["url"] == "https://example.com/callback"

    def test_posts_correct_content_type(self):
        alert = Alert(
            id="wh002", alert_type="PRICE", symbol="TCS",
            exchange="NSE", condition="BELOW", threshold=3500.0,
            triggered=True, triggered_at="2026-04-03T12:00:00",
            webhook_url="https://example.com/cb",
        )

        captured_headers = []

        def fake_urlopen(req, timeout=10):
            captured_headers.append(req.get_header("Content-type"))
            return MagicMock()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _webhook_notify(alert)
            time.sleep(0.1)

        assert captured_headers[0] == "application/json"

    def test_webhook_failure_does_not_raise(self):
        """If the webhook endpoint is unreachable, _webhook_notify must not crash."""
        alert = Alert(
            id="wh003", alert_type="PRICE", symbol="INFY",
            exchange="NSE", condition="ABOVE", threshold=1600.0,
            triggered=True, triggered_at="2026-04-03T12:00:00",
            webhook_url="https://unreachable.invalid/cb",
        )
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            _webhook_notify(alert)   # must not raise
            time.sleep(0.1)


# ── _notify fires webhook when alert triggers ─────────────────

class TestNotifyIntegration:
    def test_notify_calls_webhook_when_url_set(self, tmp_path):
        """AlertManager._notify should call _webhook_notify for alerts with webhook_url."""
        alert = Alert(
            id="ni001", alert_type="PRICE", symbol="RELIANCE",
            exchange="NSE", condition="ABOVE", threshold=2800.0,
            triggered=True, triggered_at="2026-04-03T13:00:00",
            webhook_url="https://example.com/fire",
        )

        with (
            patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"),
            patch("engine.alerts._desktop_notify"),
            patch("engine.alerts._telegram_notify"),
            patch("engine.alerts._webhook_notify") as mock_webhook,
            patch("rich.console.Console.print"),
        ):
            mgr = AlertManager()
            mgr._notify(alert, ltp=2855.0)

        mock_webhook.assert_called_once_with(alert, ltp=2855.0)

    def test_notify_skips_webhook_when_no_url(self, tmp_path):
        """AlertManager._notify should NOT call _webhook_notify if webhook_url is None."""
        alert = Alert(
            id="ni002", alert_type="PRICE", symbol="TCS",
            exchange="NSE", condition="ABOVE", threshold=3800.0,
            triggered=True, triggered_at="2026-04-03T13:00:00",
            webhook_url=None,
        )

        with (
            patch("engine.alerts.ALERTS_FILE", tmp_path / "alerts.json"),
            patch("engine.alerts._desktop_notify"),
            patch("engine.alerts._telegram_notify"),
            patch("engine.alerts._webhook_notify") as mock_webhook,
            patch("rich.console.Console.print"),
        ):
            mgr = AlertManager()
            mgr._notify(alert)

        mock_webhook.assert_not_called()
