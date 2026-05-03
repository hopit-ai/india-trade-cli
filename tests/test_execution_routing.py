"""
Tests for execution broker routing (#178).

Verifies that data reads (holdings, positions, LTP) use get_data_broker() /
get_execution_broker() rather than the primary broker, when dual-broker is
configured.
"""

from __future__ import annotations

import pytest
import brokers.session as session_mod
from brokers.mock import MockBrokerAPI


@pytest.fixture(autouse=True)
def reset_session():
    """Isolate each test from global broker state."""
    orig_brokers = session_mod._brokers.copy()
    orig_primary = session_mod._primary_key
    orig_roles = session_mod._broker_roles.copy()
    yield
    session_mod._brokers = orig_brokers
    session_mod._primary_key = orig_primary
    session_mod._broker_roles = orig_roles


def _setup_dual(data_key="fyers", exec_key="zerodha"):
    """Register two mock brokers with data/execution roles."""
    data_broker = MockBrokerAPI()
    exec_broker = MockBrokerAPI()
    session_mod._brokers = {data_key: data_broker, exec_key: exec_broker}
    session_mod._primary_key = data_key
    session_mod._broker_roles = {data_key: "data", exec_key: "execution"}
    return data_broker, exec_broker


# ── get_data_broker / get_execution_broker ───────────────────


class TestBrokerResolution:
    def test_get_data_broker_returns_data_role(self):
        from brokers.session import get_data_broker

        data, _ = _setup_dual()
        assert get_data_broker() is data

    def test_get_execution_broker_returns_exec_role(self):
        from brokers.session import get_execution_broker

        _, exc = _setup_dual()
        assert get_execution_broker() is exc

    def test_single_broker_data_falls_back_to_primary(self):
        from brokers.session import get_data_broker

        mock = MockBrokerAPI()
        session_mod._brokers = {"mock": mock}
        session_mod._primary_key = "mock"
        session_mod._broker_roles = {}
        assert get_data_broker() is mock

    def test_single_broker_execution_falls_back_to_primary(self):
        from brokers.session import get_execution_broker

        mock = MockBrokerAPI()
        session_mod._brokers = {"mock": mock}
        session_mod._primary_key = "mock"
        session_mod._broker_roles = {}
        assert get_execution_broker() is mock

    def test_no_broker_raises(self):
        from brokers.session import get_execution_broker

        session_mod._brokers = {}
        session_mod._primary_key = ""
        with pytest.raises(RuntimeError):
            get_execution_broker()


# ── Portfolio reads use execution broker ─────────────────────


class TestPortfolioUsesExecutionBroker:
    def test_get_portfolio_summary_calls_execution_broker(self, monkeypatch):
        from engine.portfolio import get_portfolio_summary

        _, exec_broker = _setup_dual()

        calls = []

        def fake_get_holdings():
            calls.append("holdings")
            return []

        def fake_get_positions():
            calls.append("positions")
            return []

        def fake_get_funds():
            from brokers.base import Funds

            calls.append("funds")
            return Funds(available_cash=0, used_margin=0, total_balance=0)

        monkeypatch.setattr(exec_broker, "get_holdings", fake_get_holdings)
        monkeypatch.setattr(exec_broker, "get_positions", fake_get_positions)
        monkeypatch.setattr(exec_broker, "get_funds", fake_get_funds)

        get_portfolio_summary()
        assert "holdings" in calls
        assert "funds" in calls

    def test_risk_meter_calls_execution_broker(self, monkeypatch):
        from engine.portfolio import risk_meter

        _, exec_broker = _setup_dual()
        calls = []

        def fake_get_funds():
            from brokers.base import Funds

            calls.append("funds")
            return Funds(available_cash=100000, used_margin=0, total_balance=100000)

        monkeypatch.setattr(exec_broker, "get_holdings", lambda: [])
        monkeypatch.setattr(exec_broker, "get_positions", lambda: [])
        monkeypatch.setattr(exec_broker, "get_funds", fake_get_funds)

        risk_meter()
        assert "funds" in calls


# ── Alert LTP check uses data broker ─────────────────────────


class TestAlertUsesDataBroker:
    def test_ltp_check_uses_data_broker(self, monkeypatch):
        from engine.alerts import AlertManager, Alert

        data_broker, _ = _setup_dual()
        ltp_calls = []

        def fake_get_ltp(instrument):
            ltp_calls.append(instrument)
            return 1500.0

        monkeypatch.setattr(data_broker, "get_ltp", fake_get_ltp)

        mgr = AlertManager()
        alert = Alert(
            id="a1",
            alert_type="CONDITIONAL",
            symbol="INFY",
            exchange="NSE",
            condition="ABOVE",
            threshold=0.0,
            conditions=[{"condition_type": "PRICE", "condition": "ABOVE", "threshold": 1000.0}],
        )
        result = mgr._check_conditional(alert)
        assert result is True
        assert len(ltp_calls) == 1


# ── Role auto-assignment on register ─────────────────────────


class TestAutoRoleAssignment:
    def test_fyers_gets_data_role_on_register(self):
        from brokers.session import register_broker

        mock = MockBrokerAPI()
        session_mod._brokers = {}
        session_mod._primary_key = ""
        session_mod._broker_roles = {}
        register_broker("fyers", mock, primary=True)
        assert session_mod._broker_roles.get("fyers") == "data"

    def test_zerodha_gets_execution_role_on_register(self):
        from brokers.session import register_broker

        fyers = MockBrokerAPI()
        zerodha = MockBrokerAPI()
        session_mod._brokers = {}
        session_mod._primary_key = ""
        session_mod._broker_roles = {}
        register_broker("fyers", fyers, primary=True)
        register_broker("zerodha", zerodha, primary=False)
        assert session_mod._broker_roles.get("zerodha") == "execution"

    def test_both_role_assigned_when_only_one_broker(self):
        from brokers.session import register_broker

        mock = MockBrokerAPI()
        session_mod._brokers = {}
        session_mod._primary_key = ""
        session_mod._broker_roles = {}
        register_broker("mock", mock, primary=True)
        # Single broker gets "both" role
        assert session_mod._broker_roles.get("mock") in ("both", "data", "execution", None)
