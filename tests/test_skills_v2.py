"""
Tests for new skill endpoints added in v2:
  iv_smile, gex, delta_hedge, risk_report, walkforward, whatif, strategy,
  drift, memory, memory/query, audit, telegram/status, provider (GET+POST),
  analyze/followup

All tests use FastAPI TestClient with mocked dependencies.
No real broker, LLM, or network calls.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


# ── App fixture ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    import os

    os.environ["DEPLOY_MODE"] = "self-hosted"
    os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app

        yield TestClient(app)


# ── Shared fake dataclasses ───────────────────────────────────


@dataclass
class FakeDeltaHedge:
    current_delta: float = 50.0
    target_delta: float = 0.0
    gap: float = -50.0
    suggestions: list = field(default_factory=list)
    cost_estimate: float = 0.0


@dataclass
class FakeRiskReport:
    portfolio_value: float = 500000.0
    portfolio_var_95: float = 12000.0
    portfolio_var_99: float = 18000.0
    portfolio_cvar_95: float = 15000.0
    portfolio_volatility: float = 0.18
    holding_vars: list = field(default_factory=list)
    correlation_matrix: dict = None
    high_correlations: list = field(default_factory=list)
    top_concentration: list = field(default_factory=list)
    hhi: float = 0.25
    concentration_risk: str = "LOW"


@dataclass
class FakeWalkForwardResult:
    symbol: str = "NIFTY"
    strategy: str = "rsi"
    windows: list = field(default_factory=list)
    avg_return: float = 12.5
    avg_sharpe: float = 0.9
    consistency: str = "MODERATE"


@dataclass
class FakeScenarioResult:
    scenario_name: str = "Market -5%"
    description: str = "test"
    current_value: float = 100000.0
    projected_value: float = 95000.0
    projected_pnl: float = -5000.0
    projected_pnl_pct: float = -5.0
    impacts: list = field(default_factory=list)


@dataclass
class FakeStrategyReport:
    symbol: str = "NIFTY"
    spot: float = 24000.0
    view: str = "BULLISH"
    dte: int = 30
    capital: float = 100000.0
    risk_pct: float = 2.0
    max_risk_inr: float = 2000.0
    strategies: list = field(default_factory=list)
    top: None = None


@dataclass
class FakeDriftReport:
    total_trades: int = 50
    trades_with_outcome: int = 30
    recent_win_rate: float = 0.6
    older_win_rate: float = 0.55
    win_rate_trend: str = "IMPROVING"
    win_rate_delta: float = 0.05
    low_vix_win_rate: float = 0.65
    high_vix_win_rate: float = 0.50
    buy_accuracy: float = 0.62
    sell_accuracy: float = 0.55
    hold_accuracy: float = 0.48
    analyst_accuracy: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)


@dataclass
class FakeAuditReport:
    trade_id: str = "trade-123"
    symbol: str = "INFY"
    verdict: str = "BULLISH"
    outcome: str = "WIN"
    pnl: float = 5000.0
    analyst_grades: list = field(default_factory=list)
    most_accurate: str = "Technical"
    most_wrong: str = "Sentiment"
    entry_quality: str = "GOOD"
    sl_assessment: str = "FAIR"
    hold_assessment: str = "GOOD"
    lessons: list = field(default_factory=lambda: ["Cut losses early"])


# ── /skills/iv_smile ──────────────────────────────────────────


class TestIVSmile:
    def _fake_df(self):
        return pd.DataFrame(
            {
                "strike": [24000, 24500],
                "ce_iv": [0.18, 0.22],
                "pe_iv": [0.20, 0.24],
                "moneyness": [-0.02, 0.02],
            }
        )

    def test_returns_rows_for_valid_symbol(self, client):
        with patch("analysis.volatility_surface.compute_iv_smile", return_value=self._fake_df()):
            r = client.post("/skills/iv_smile", json={"symbol": "NIFTY"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert isinstance(d["rows"], list)
        assert len(d["rows"]) == 2
        assert d["rows"][0]["strike"] == 24000

    def test_returns_empty_rows_when_none(self, client):
        with patch("analysis.volatility_surface.compute_iv_smile", return_value=None):
            r = client.post("/skills/iv_smile", json={"symbol": "NIFTY"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["rows"] == []

    def test_500_on_exception(self, client):
        with patch(
            "analysis.volatility_surface.compute_iv_smile",
            side_effect=RuntimeError("surface computation failed"),
        ):
            r = client.post("/skills/iv_smile", json={"symbol": "NIFTY"})
        assert r.status_code == 500


# ── /skills/gex ───────────────────────────────────────────────


class TestGEX:
    def _fake_gex(self):
        return {
            "total_net_gex": 1250000.0,
            "flip_point": 24200.0,
            "regime": "POSITIVE_GEX",
            "strikes": [{"strike": 24000, "net_gex": 500000.0}],
        }

    def test_returns_gex_data(self, client):
        with patch("analysis.gex.get_gex_analysis", return_value=self._fake_gex()):
            r = client.post("/skills/gex", json={"symbol": "NIFTY"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["total_net_gex"] == 1250000.0
        assert d["flip_point"] == 24200.0
        assert d["regime"] == "POSITIVE_GEX"
        assert isinstance(d["strikes"], list)

    def test_returns_error_dict_from_backend(self, client):
        # Errors are surfaced in data payload, not as HTTP errors
        with patch("analysis.gex.get_gex_analysis", return_value={"error": "No data"}):
            r = client.post("/skills/gex", json={"symbol": "NIFTY"})
        assert r.status_code == 200
        assert r.json()["data"]["error"] == "No data"

    def test_500_on_exception(self, client):
        with patch(
            "analysis.gex.get_gex_analysis",
            side_effect=RuntimeError("options chain unavailable"),
        ):
            r = client.post("/skills/gex", json={"symbol": "NIFTY"})
        assert r.status_code == 500


# ── /skills/delta_hedge ───────────────────────────────────────


class TestDeltaHedge:
    def test_returns_demo_when_no_broker(self, client):
        with patch("brokers.session.get_broker", side_effect=RuntimeError("no broker")):
            r = client.post("/skills/delta_hedge")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["demo"] is True
        assert d["suggestions"] == []

    def test_returns_hedge_suggestion_when_broker_connected(self, client):
        fake_pg = MagicMock()
        fake_pg.net_delta = 50.0

        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.portfolio.get_position_greeks", return_value=fake_pg),
            patch("engine.greeks_manager.compute_delta_hedge", return_value=FakeDeltaHedge()),
        ):
            r = client.post("/skills/delta_hedge")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["current_delta"] == 50.0
        assert d["target_delta"] == 0.0
        assert d["gap"] == -50.0

    def test_500_on_exception(self, client):
        fake_pg = MagicMock()
        fake_pg.net_delta = 50.0

        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.portfolio.get_position_greeks", return_value=fake_pg),
            patch(
                "engine.greeks_manager.compute_delta_hedge",
                side_effect=RuntimeError("greeks computation failed"),
            ),
        ):
            r = client.post("/skills/delta_hedge")
        assert r.status_code == 500


# ── /skills/risk_report ───────────────────────────────────────


class TestRiskReport:
    def test_returns_demo_when_no_broker(self, client):
        with patch("brokers.session.get_broker", side_effect=RuntimeError("no broker")):
            r = client.post("/skills/risk_report")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["demo"] is True

    def test_returns_report_when_connected(self, client):
        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.risk_metrics.compute_portfolio_risk", return_value=FakeRiskReport()),
        ):
            r = client.post("/skills/risk_report")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["portfolio_value"] == 500000.0
        assert d["portfolio_var_95"] == 12000.0
        assert d["concentration_risk"] == "LOW"


# ── /skills/walkforward ───────────────────────────────────────


class TestWalkForward:
    def test_returns_result(self, client):
        with patch("engine.backtest.walk_forward_test", return_value=FakeWalkForwardResult()):
            r = client.post(
                "/skills/walkforward",
                json={"symbol": "NIFTY", "strategy": "rsi"},
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["symbol"] == "NIFTY"
        assert d["avg_return"] == 12.5
        assert d["consistency"] == "MODERATE"

    def test_default_strategy_is_rsi(self, client):
        with patch(
            "engine.backtest.walk_forward_test", return_value=FakeWalkForwardResult()
        ) as mock:
            client.post("/skills/walkforward", json={"symbol": "NIFTY"})
        _, kwargs = mock.call_args
        assert kwargs["strategy_name"] == "rsi"

    def test_500_on_exception(self, client):
        with patch(
            "engine.backtest.walk_forward_test",
            side_effect=RuntimeError("backtest engine error"),
        ):
            r = client.post("/skills/walkforward", json={"symbol": "NIFTY"})
        assert r.status_code == 500


# ── /skills/whatif ────────────────────────────────────────────


class TestWhatIf:
    def test_returns_demo_when_no_broker(self, client):
        with patch("brokers.session.get_broker", side_effect=RuntimeError("no broker")):
            r = client.post("/skills/whatif", json={"scenario": "market", "nifty_change": -5.0})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["demo"] is True

    def test_market_move_scenario(self, client):
        fake_sim = MagicMock()
        fake_sim.scenario_market_move.return_value = FakeScenarioResult()

        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.simulator.Simulator", return_value=fake_sim),
        ):
            r = client.post(
                "/skills/whatif",
                json={"scenario": "market", "nifty_change": -5.0},
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["projected_pnl"] == -5000.0
        fake_sim.scenario_market_move.assert_called_once_with(-5.0)

    def test_stock_move_scenario(self, client):
        fake_sim = MagicMock()
        fake_sim.scenario_stock_move.return_value = FakeScenarioResult(
            scenario_name="RELIANCE +10%",
            projected_pnl=10000.0,
        )

        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.simulator.Simulator", return_value=fake_sim),
        ):
            r = client.post(
                "/skills/whatif",
                json={"scenario": "stock", "symbol": "RELIANCE", "stock_change": 10.0},
            )
        assert r.status_code == 200
        fake_sim.scenario_stock_move.assert_called_once_with("RELIANCE", 10.0)

    def test_default_three_scenario_sweep(self, client):
        fake_sim = MagicMock()
        fake_sim.scenario_market_move.side_effect = [
            FakeScenarioResult(scenario_name="Market -5%"),
            FakeScenarioResult(scenario_name="Market flat"),
            FakeScenarioResult(scenario_name="Market +5%"),
        ]

        with (
            patch("brokers.session.get_broker", return_value=MagicMock()),
            patch("engine.simulator.Simulator", return_value=fake_sim),
        ):
            # No nifty_change provided — should trigger three-scenario sweep
            r = client.post("/skills/whatif", json={"scenario": "market"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["multi"] is True
        assert len(d["scenarios"]) == 3
        assert fake_sim.scenario_market_move.call_count == 3


# ── /skills/strategy ──────────────────────────────────────────


class TestStrategy:
    def test_returns_strategies(self, client):
        with (
            patch("market.quotes.get_ltp", return_value=24000.0),
            patch("engine.strategy.recommend", return_value=FakeStrategyReport()),
        ):
            r = client.post(
                "/skills/strategy",
                json={"symbol": "NIFTY", "view": "BULLISH", "dte": 30},
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["symbol"] == "NIFTY"
        assert d["spot"] == 24000.0
        assert isinstance(d["strategies"], list)

    def test_500_when_spot_fails(self, client):
        with patch("market.quotes.get_ltp", side_effect=Exception("quote fetch failed")):
            r = client.post(
                "/skills/strategy",
                json={"symbol": "NIFTY", "view": "BULLISH"},
            )
        assert r.status_code == 500

    def test_view_is_uppercased(self, client):
        with (
            patch("market.quotes.get_ltp", return_value=24000.0),
            patch("engine.strategy.recommend", return_value=FakeStrategyReport()) as mock_rec,
        ):
            client.post(
                "/skills/strategy",
                json={"symbol": "NIFTY", "view": "bullish"},
            )
        _, kwargs = mock_rec.call_args
        assert kwargs["view"] == "BULLISH"


# ── /skills/drift ─────────────────────────────────────────────


class TestDrift:
    def test_returns_report(self, client):
        with patch("engine.drift.detect_drift", return_value=FakeDriftReport()):
            r = client.post("/skills/drift")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["total_trades"] == 50
        assert d["win_rate_trend"] == "IMPROVING"
        assert d["recent_win_rate"] == 0.6

    def test_500_on_exception(self, client):
        with patch("engine.drift.detect_drift", side_effect=RuntimeError("memory read failed")):
            r = client.post("/skills/drift")
        assert r.status_code == 500


# ── /skills/memory ────────────────────────────────────────────


class TestMemory:
    def test_returns_stats_and_records(self, client):
        fake_stats = {"total": 100, "wins": 60, "losses": 40}
        fake_records = [{"trade_id": "t1", "symbol": "INFY"}]

        mock_tm = MagicMock()
        mock_tm.get_stats.return_value = fake_stats
        mock_tm.query.return_value = fake_records

        with patch("engine.memory.trade_memory", mock_tm):
            r = client.post("/skills/memory")
        assert r.status_code == 200
        d = r.json()["data"]
        assert "stats" in d
        assert "records" in d
        assert d["stats"]["total"] == 100
        assert isinstance(d["records"], list)

    def test_memory_query_with_filters(self, client):
        fake_records = [{"trade_id": "t2", "symbol": "INFY"}]

        mock_tm = MagicMock()
        mock_tm.query.return_value = fake_records

        with patch("engine.memory.trade_memory", mock_tm):
            r = client.post(
                "/skills/memory/query",
                json={"symbol": "INFY", "limit": 10},
            )
        assert r.status_code == 200
        mock_tm.query.assert_called_once_with(
            symbol="INFY",
            verdict=None,
            limit=10,
            days_back=None,
        )


# ── /skills/audit ─────────────────────────────────────────────


class TestAudit:
    def test_returns_audit_report(self, client):
        with patch("engine.audit.audit_trade", return_value=FakeAuditReport()):
            r = client.post("/skills/audit", json={"trade_id": "trade-123"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["trade_id"] == "trade-123"
        assert d["verdict"] == "BULLISH"
        assert d["outcome"] == "WIN"
        assert d["pnl"] == 5000.0
        assert d["most_accurate"] == "Technical"

    def test_500_on_bad_trade_id(self, client):
        with patch(
            "engine.audit.audit_trade",
            side_effect=ValueError("trade not found in memory"),
        ):
            r = client.post("/skills/audit", json={"trade_id": "nonexistent-trade"})
        assert r.status_code == 500


# ── /skills/telegram/status ───────────────────────────────────


class TestTelegramStatus:
    def test_not_configured_when_no_env_var(self, client, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        r = client.get("/skills/telegram/status")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["configured"] is False
        assert d["token_hint"] is None

    def test_configured_when_token_set(self, client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test:token123")
        r = client.get("/skills/telegram/status")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["configured"] is True
        assert d["token_hint"].endswith("ken123")


# ── /skills/provider ──────────────────────────────────────────


class TestProvider:
    def test_get_returns_current_provider(self, client, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        r = client.post("/skills/provider")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["current"] == "anthropic"
        assert "anthropic" in d["available"]
        assert "ollama" in d["available"]

    def test_post_switches_provider(self, client, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "anthropic")
        r = client.post("/skills/provider/switch", json={"provider": "openai"})
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["current"] == "openai"

    def test_post_rejects_invalid_provider(self, client):
        r = client.post("/skills/provider/switch", json={"provider": "badprovider"})
        assert r.status_code == 400


# ── /skills/analyze/followup ──────────────────────────────────


class TestAnalyzeFollowup:
    def _make_agent(self):
        mock_agent = MagicMock()
        mock_agent.chat.return_value = "The ideal entry for INFY is \u20b91,580."
        mock_agent._history = []
        return mock_agent

    def test_returns_response(self, client):
        mock_agent = self._make_agent()
        with patch("agent.core.TradingAgent", return_value=mock_agent):
            r = client.post(
                "/skills/analyze/followup",
                json={
                    "symbol": "INFY",
                    "question": "What is the ideal entry?",
                    "session_id": "resp-test-1",
                },
            )
        assert r.status_code == 200
        d = r.json()["data"]
        assert "response" in d
        assert "INFY" in d["symbol"]

    def test_seeds_context_on_first_call(self, client):
        """On first call with context, agent.chat is called twice:
        once to prime with context, once for the actual question."""
        mock_agent = self._make_agent()
        with patch("agent.core.TradingAgent", return_value=mock_agent):
            r = client.post(
                "/skills/analyze/followup",
                json={
                    "symbol": "INFY",
                    "question": "What is the ideal entry?",
                    "session_id": "ctx-seed-test-1",
                    "context": {
                        "analysts": [
                            {
                                "name": "Technical",
                                "verdict": "BULLISH",
                                "confidence": 80,
                                "key_points": ["RSI oversold"],
                            }
                        ],
                        "synthesis_text": "Overall bullish bias.",
                    },
                },
            )
        assert r.status_code == 200
        # First call seeds context, second call answers the question
        assert mock_agent.chat.call_count == 2

    def test_reuses_session_on_second_call(self, client):
        """Second call with the same session_id should not instantiate a new TradingAgent."""
        mock_agent = self._make_agent()

        # Pre-populate the session store with the exact key the endpoint builds
        from web.skills import _chat_sessions

        session_key = "followup_MSFT_NSE_reuse-session-99"
        _chat_sessions[session_key] = mock_agent

        r = client.post(
            "/skills/analyze/followup",
            json={
                "symbol": "MSFT",
                "exchange": "NSE",
                "question": "Any updated view?",
                "session_id": "reuse-session-99",
            },
        )
        assert r.status_code == 200
        # Only the direct question call — no context priming
        mock_agent.chat.assert_called_once_with("Any updated view?")

    def test_500_on_agent_error(self, client):
        mock_agent = self._make_agent()
        mock_agent.chat.side_effect = RuntimeError("LLM timeout")

        with patch("agent.core.TradingAgent", return_value=mock_agent):
            r = client.post(
                "/skills/analyze/followup",
                json={
                    "symbol": "TCS",
                    "question": "Should I hold?",
                    "session_id": "err-session-1",
                },
            )
        assert r.status_code == 500
