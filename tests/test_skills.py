"""
Tests for web/skills.py — OpenClaw skill endpoints.

All tests use FastAPI's TestClient with mocked market/engine functions
so no real broker connection or LLM API keys are needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── App fixture ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with all broker/keychain loading suppressed.

    Two extra patches keep the auth middleware from returning 401:
    - DEPLOY_MODE=self-hosted  activates the 'no users yet' bypass path
    - web.api.user_count → 0  satisfies that bypass condition

    In newer starlette/httpx (>=0.21) TestClient sets request.client.host
    to "testclient" rather than "127.0.0.1", so the localhost shortcut no
    longer fires — these patches cover all Python/starlette version combos.
    """
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
        patch("web.api.user_count", return_value=0),
        patch.dict(os.environ, {"DEPLOY_MODE": "self-hosted"}),
    ):
        from web.api import app

        yield TestClient(app)


# ── Shared fake data ──────────────────────────────────────────


@dataclass
class FakeQuote:
    symbol: str = "NSE:RELIANCE"
    last_price: float = 2850.0
    open: float = 2830.0
    high: float = 2870.0
    low: float = 2820.0
    close: float = 2845.0
    volume: int = 1_500_000
    change: float = 20.0
    change_pct: float = 0.71


@dataclass
class FakeFlowAnalysis:
    fii_buy: float = 12000.0
    fii_sell: float = 9500.0
    dii_buy: float = 8000.0
    dii_sell: float = 7200.0
    net_fii: float = 2500.0
    net_dii: float = 800.0
    signal: str = "BULLISH"
    streak: int = 3


@dataclass
class FakeMacroSnapshot:
    usd_inr: float = 83.5
    usd_inr_change_pct: float = -0.1
    crude_oil: float = 85.2
    crude_oil_change_pct: float = 0.5
    gold: float = 2350.0
    gold_change_pct: float = 0.2
    us_10y: float = 4.35
    us_10y_change_pct: float = 0.03


@dataclass
class FakeBacktestResult:
    symbol: str = "INFY"
    strategy: str = "rsi"
    total_return: float = 18.5
    sharpe_ratio: float = 1.2
    max_drawdown: float = -12.3
    win_rate: float = 0.55
    total_trades: int = 42


@dataclass
class FakePairAnalysis:
    stock_a: str = "HDFCBANK"
    stock_b: str = "ICICIBANK"
    correlation: float = 0.87
    spread_zscore: float = 1.4
    half_life: float = 12.3
    signal: str = "LONG_A"


# ── /skills/quote ─────────────────────────────────────────────


class TestQuoteSkill:
    def test_returns_quote(self, client):
        with patch("market.quotes.get_quote", return_value={"NSE:RELIANCE": FakeQuote()}):
            r = client.post("/skills/quote", json={"symbol": "RELIANCE"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["data"]["last_price"] == 2850.0
        assert data["data"]["symbol"] == "NSE:RELIANCE"

    def test_prefixes_exchange(self, client):
        """Symbol without exchange prefix should get NSE: added."""
        with patch(
            "market.quotes.get_quote", return_value={"NSE:TCS": FakeQuote(symbol="NSE:TCS")}
        ) as mock:
            client.post("/skills/quote", json={"symbol": "TCS"})
        mock.assert_called_once_with(["NSE:TCS"])

    def test_passthrough_if_exchange_in_symbol(self, client):
        """If caller already includes exchange, don't double-prefix."""
        with patch(
            "market.quotes.get_quote",
            return_value={"BSE:RELIANCE": FakeQuote(symbol="BSE:RELIANCE")},
        ) as mock:
            client.post("/skills/quote", json={"symbol": "BSE:RELIANCE"})
        mock.assert_called_once_with(["BSE:RELIANCE"])

    def test_404_when_no_quote(self, client):
        with patch("market.quotes.get_quote", return_value={}):
            r = client.post("/skills/quote", json={"symbol": "UNKNOWN"})
        assert r.status_code == 404

    def test_500_on_exception(self, client):
        with patch("market.quotes.get_quote", side_effect=RuntimeError("network down")):
            r = client.post("/skills/quote", json={"symbol": "RELIANCE"})
        assert r.status_code == 500
        assert "network down" in r.json()["detail"]["message"]


# ── /skills/flows ─────────────────────────────────────────────


class TestFlowsSkill:
    def test_returns_flow_data(self, client):
        with patch("market.flow_intel.get_flow_analysis", return_value=FakeFlowAnalysis()):
            r = client.post("/skills/flows")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["signal"] == "BULLISH"
        assert d["net_fii"] == 2500.0

    def test_500_on_exception(self, client):
        with patch("market.flow_intel.get_flow_analysis", side_effect=Exception("upstream error")):
            r = client.post("/skills/flows")
        assert r.status_code == 500


# ── /skills/macro ─────────────────────────────────────────────


class TestMacroSkill:
    def test_returns_macro_snapshot(self, client):
        with patch("market.macro.get_macro_snapshot", return_value=FakeMacroSnapshot()):
            r = client.post("/skills/macro", json={})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["usd_inr"] == 83.5
        assert d["crude_oil"] == 85.2


# ── /skills/earnings ──────────────────────────────────────────


class TestEarningsSkill:
    def test_returns_all_events_when_no_filter(self, client):
        events = [
            MagicMock(__str__=lambda s: "RELIANCE Q4 2025"),
            MagicMock(__str__=lambda s: "TCS Q4 2025"),
        ]
        with patch("market.earnings.get_earnings_calendar", return_value=events):
            r = client.post("/skills/earnings", json={})
        assert r.status_code == 200

    def test_filters_by_symbols(self, client):
        """When symbols list provided, only matching events returned."""
        from dataclasses import dataclass

        @dataclass
        class FakeEntry:
            symbol: str
            company: str

            def __str__(self):
                return f"{self.symbol} {self.company}"

        events = [FakeEntry("RELIANCE", "Reliance"), FakeEntry("TCS", "TCS")]
        with patch("market.earnings.get_earnings_calendar", return_value=events):
            r = client.post("/skills/earnings", json={"symbols": ["RELIANCE"]})
        assert r.status_code == 200
        # only 1 matching
        assert len(r.json()["data"]) == 1


# ── /skills/backtest ──────────────────────────────────────────


class TestBacktestSkill:
    def test_returns_backtest_result(self, client):
        with patch("engine.backtest.run_backtest", return_value=FakeBacktestResult()):
            r = client.post("/skills/backtest", json={"symbol": "INFY", "strategy": "rsi"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["total_return"] == 18.5
        assert d["sharpe_ratio"] == 1.2

    def test_upcases_symbol(self, client):
        with patch("engine.backtest.run_backtest", return_value=FakeBacktestResult()) as mock:
            client.post("/skills/backtest", json={"symbol": "infy", "strategy": "rsi"})
        mock.assert_called_once_with("INFY", "rsi", period="1y")

    def test_default_period_is_1y(self, client):
        with patch("engine.backtest.run_backtest", return_value=FakeBacktestResult()) as mock:
            client.post("/skills/backtest", json={"symbol": "INFY"})
        _, kwargs = mock.call_args
        assert kwargs["period"] == "1y"


# ── /skills/pairs ─────────────────────────────────────────────


class TestPairsSkill:
    def test_returns_pair_analysis(self, client):
        with patch("engine.pairs.analyze_pair", return_value=FakePairAnalysis()):
            r = client.post("/skills/pairs", json={"stock_a": "HDFCBANK", "stock_b": "ICICIBANK"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["correlation"] == 0.87
        assert d["signal"] == "LONG_A"

    def test_upcases_both_symbols(self, client):
        with patch("engine.pairs.analyze_pair", return_value=FakePairAnalysis()) as mock:
            client.post("/skills/pairs", json={"stock_a": "hdfcbank", "stock_b": "icicibank"})
        mock.assert_called_once_with("HDFCBANK", "ICICIBANK")


# ── /skills/morning_brief ─────────────────────────────────────


class TestMorningBriefSkill:
    def test_returns_all_sections(self, client):
        with (
            patch("market.indices.get_market_snapshot", return_value={"nifty": 22500}),
            patch("market.flow_intel.get_flow_analysis", return_value=FakeFlowAnalysis()),
            patch("market.news.get_market_news", return_value=[{"title": "Market up"}]),
            patch(
                "market.sentiment.get_market_breadth",
                return_value={"advance": 1200, "decline": 800},
            ),
            patch("market.events.get_upcoming_events", return_value=[]),
        ):
            r = client.post("/skills/morning_brief")
        assert r.status_code == 200
        d = r.json()["data"]
        assert "market_snapshot" in d
        assert "institutional_flows" in d
        assert "top_news" in d
        assert "market_breadth" in d
        assert "upcoming_events" in d

    def test_partial_failure_still_500(self, client):
        with (
            patch("market.indices.get_market_snapshot", side_effect=Exception("NSE down")),
            patch("market.flow_intel.get_flow_analysis", return_value=FakeFlowAnalysis()),
            patch("market.news.get_market_news", return_value=[]),
            patch("market.sentiment.get_market_breadth", return_value={}),
            patch("market.events.get_upcoming_events", return_value=[]),
        ):
            r = client.post("/skills/morning_brief")
        assert r.status_code == 500


# ── /skills/chat ─────────────────────────────────────────────


class TestChatSkill:
    def test_returns_response(self, client):
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "RELIANCE looks bullish. RSI is 62."
        mock_agent._history = [{"role": "user"}, {"role": "assistant"}]

        with patch("agent.core.TradingAgent", return_value=mock_agent):
            r = client.post(
                "/skills/chat", json={"message": "Analyse RELIANCE", "session_id": "test-1"}
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert "RELIANCE" in d["response"]
        assert d["session_id"] == "test-1"
        assert d["history_length"] == 2

    def test_reuses_session(self, client):
        """Second call with same session_id should not create a new TradingAgent."""
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "Follow-up answer."
        mock_agent._history = []

        # Pre-populate the session store
        from web.skills import _chat_sessions

        _chat_sessions["reuse-session"] = mock_agent

        r = client.post(
            "/skills/chat", json={"message": "Follow up", "session_id": "reuse-session"}
        )
        assert r.status_code == 200
        mock_agent.chat.assert_called_once_with("Follow up")

    def test_chat_reset_clears_session(self, client):
        from web.skills import _chat_sessions

        _chat_sessions["to-clear"] = MagicMock()

        r = client.post("/skills/chat/reset", json={"session_id": "to-clear"})
        assert r.status_code == 200
        assert r.json()["data"]["cleared"] is True
        assert "to-clear" not in _chat_sessions

    def test_chat_reset_nonexistent_session_ok(self, client):
        """Resetting a session that doesn't exist should not error."""
        r = client.post("/skills/chat/reset", json={"session_id": "never-existed"})
        assert r.status_code == 200


# ── /skills/alerts/* ─────────────────────────────────────────


class TestAlertsSkills:
    def _fake_alert(self, **kwargs):
        from engine.alerts import Alert

        defaults = dict(
            id="abc12345",
            alert_type="PRICE",
            symbol="RELIANCE",
            exchange="NSE",
            condition="ABOVE",
            threshold=2800.0,
            created_at="2026-04-03T10:00:00",
        )
        defaults.update(kwargs)
        return Alert(**defaults)

    def test_add_price_alert(self, client):
        fake = self._fake_alert()
        with (
            patch("engine.alerts.alert_manager.add_price_alert", return_value=fake) as mock,
            patch("engine.alerts.alert_manager.start_polling"),
        ):
            r = client.post(
                "/skills/alerts/add",
                json={
                    "symbol": "RELIANCE",
                    "condition": "ABOVE",
                    "threshold": 2800,
                },
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["id"] == "abc12345"
        assert d["alert_type"] == "PRICE"
        mock.assert_called_once_with(
            symbol="RELIANCE",
            condition="ABOVE",
            threshold=2800.0,
            exchange="NSE",
            webhook_url=None,
        )

    def test_add_technical_alert(self, client):
        fake = self._fake_alert(alert_type="TECHNICAL", indicator="RSI", threshold=70.0)
        with (
            patch("engine.alerts.alert_manager.add_technical_alert", return_value=fake) as mock,
            patch("engine.alerts.alert_manager.start_polling"),
        ):
            r = client.post(
                "/skills/alerts/add",
                json={
                    "symbol": "INFY",
                    "indicator": "RSI",
                    "condition": "ABOVE",
                    "threshold": 70,
                },
            )
        assert r.status_code == 200
        mock.assert_called_once_with(
            symbol="INFY",
            indicator="RSI",
            condition="ABOVE",
            threshold=70.0,
            exchange="NSE",
            webhook_url=None,
        )

    def test_add_conditional_alert(self, client):
        fake = self._fake_alert(
            alert_type="CONDITIONAL",
            conditions=[
                {
                    "condition_type": "PRICE",
                    "condition": "ABOVE",
                    "threshold": 2800,
                    "indicator": None,
                },
                {
                    "condition_type": "TECHNICAL",
                    "condition": "ABOVE",
                    "threshold": 60,
                    "indicator": "RSI",
                },
            ],
        )
        with (
            patch("engine.alerts.alert_manager.add_conditional_alert", return_value=fake) as mock,
            patch("engine.alerts.alert_manager.start_polling"),
        ):
            r = client.post(
                "/skills/alerts/add",
                json={
                    "symbol": "RELIANCE",
                    "conditions": [
                        {"condition_type": "PRICE", "condition": "ABOVE", "threshold": 2800},
                        {
                            "condition_type": "TECHNICAL",
                            "condition": "ABOVE",
                            "threshold": 60,
                            "indicator": "RSI",
                        },
                    ],
                },
            )
        assert r.status_code == 200
        assert mock.called

    def test_add_with_webhook_url(self, client):
        fake = self._fake_alert(webhook_url="https://agent.example.com/cb")
        with (
            patch("engine.alerts.alert_manager.add_price_alert", return_value=fake) as mock,
            patch("engine.alerts.alert_manager.start_polling"),
        ):
            client.post(
                "/skills/alerts/add",
                json={
                    "symbol": "RELIANCE",
                    "condition": "ABOVE",
                    "threshold": 2800,
                    "webhook_url": "https://agent.example.com/cb",
                },
            )
        _, kwargs = mock.call_args
        assert kwargs["webhook_url"] == "https://agent.example.com/cb"

    def test_add_alert_missing_fields_returns_400(self, client):
        """Providing symbol only (no condition/indicator/conditions) should return 400."""
        with patch("engine.alerts.alert_manager.start_polling"):
            r = client.post("/skills/alerts/add", json={"symbol": "RELIANCE"})
        assert r.status_code == 400

    def test_list_alerts(self, client):
        fake_list = [
            {
                "id": "a1",
                "alert_type": "PRICE",
                "symbol": "RELIANCE",
                "condition": "ABOVE",
                "threshold": 2800.0,
            },
            {
                "id": "b2",
                "alert_type": "TECHNICAL",
                "symbol": "INFY",
                "condition": "ABOVE",
                "threshold": 70.0,
            },
        ]
        with patch("engine.alerts.alert_manager.list_alerts", return_value=fake_list):
            r = client.post("/skills/alerts/list")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 2

    def test_remove_alert_found(self, client):
        with patch("engine.alerts.alert_manager.remove_alert", return_value=True):
            r = client.post("/skills/alerts/remove", json={"alert_id": "abc12345"})
        assert r.status_code == 200
        assert r.json()["data"]["removed"] is True

    def test_remove_alert_not_found(self, client):
        with patch("engine.alerts.alert_manager.remove_alert", return_value=False):
            r = client.post("/skills/alerts/remove", json={"alert_id": "nonexistent"})
        assert r.status_code == 404

    def test_check_alerts_no_triggers(self, client):
        with (
            patch("engine.alerts.alert_manager.check_alerts", return_value=[]),
            patch("engine.alerts.alert_manager.active_count", return_value=3),
        ):
            r = client.post("/skills/alerts/check")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["triggered"] == []
        assert d["active_remaining"] == 3

    def test_check_alerts_with_triggered(self, client):
        fake = self._fake_alert(triggered=True, triggered_at="2026-04-03T11:00:00")
        with (
            patch("engine.alerts.alert_manager.check_alerts", return_value=[fake]),
            patch("engine.alerts.alert_manager.active_count", return_value=0),
        ):
            r = client.post("/skills/alerts/check")
        assert r.status_code == 200
        triggered = r.json()["data"]["triggered"]
        assert len(triggered) == 1
        assert triggered[0]["symbol"] == "RELIANCE"


# ── /.well-known/openclaw.json ────────────────────────────────


class TestOpenClawManifest:
    def test_manifest_returns_200(self, client):
        r = client.get("/.well-known/openclaw.json")
        assert r.status_code == 200

    def test_manifest_has_required_fields(self, client):
        r = client.get("/.well-known/openclaw.json")
        m = r.json()
        assert m["name"] == "india-trade-cli"
        assert "description" in m
        assert "version" in m
        assert "skills" in m
        assert isinstance(m["skills"], list)

    def test_manifest_has_expected_skills(self, client):
        r = client.get("/.well-known/openclaw.json")
        skill_names = {s["name"] for s in r.json()["skills"]}
        expected = {
            "quote",
            "options_chain",
            "flows",
            "earnings",
            "macro",
            "deals",
            "backtest",
            "pairs",
            "analyze",
            "deep_analyze",
            "morning_brief",
            "chat",
            "chat_reset",
            "alerts_add",
            "alerts_list",
            "alerts_remove",
            "alerts_check",
        }
        assert expected <= skill_names, f"Missing skills: {expected - skill_names}"

    def test_manifest_skills_have_schemas(self, client):
        r = client.get("/.well-known/openclaw.json")
        for skill in r.json()["skills"]:
            assert "name" in skill
            assert "path" in skill
            assert "input_schema" in skill, f"Skill {skill['name']} missing input_schema"
            assert "description" in skill

    def test_manifest_base_url_is_set(self, client):
        r = client.get("/.well-known/openclaw.json")
        assert r.json()["base_url"] != ""
