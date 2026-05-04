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
    orig_data = session_mod._data_key
    orig_exec = session_mod._exec_key
    yield
    session_mod._brokers = orig_brokers
    session_mod._primary_key = orig_primary
    session_mod._data_key = orig_data
    session_mod._exec_key = orig_exec


def _setup_dual(data_key="fyers", exec_key="zerodha"):
    """Register two mock brokers with data/execution roles."""
    data_broker = MockBrokerAPI()
    exec_broker = MockBrokerAPI()
    session_mod._brokers = {data_key: data_broker, exec_key: exec_broker}
    session_mod._primary_key = data_key
    session_mod._data_key = data_key
    session_mod._exec_key = exec_key
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
        session_mod._data_key = "mock"
        session_mod._exec_key = "mock"
        assert get_data_broker() is mock

    def test_single_broker_execution_falls_back_to_primary(self):
        from brokers.session import get_execution_broker

        mock = MockBrokerAPI()
        session_mod._brokers = {"mock": mock}
        session_mod._primary_key = "mock"
        session_mod._data_key = "mock"
        session_mod._exec_key = "mock"
        assert get_execution_broker() is mock

    def test_no_broker_raises(self):
        from brokers.session import get_execution_broker

        session_mod._brokers = {}
        session_mod._primary_key = ""
        session_mod._data_key = ""
        session_mod._exec_key = ""
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


# ── Role assignment on login / connect ────────────────────────


class TestAutoRoleAssignment:
    def _reset(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""
        session_mod._data_key = ""
        session_mod._exec_key = ""

    def test_login_sets_broker_as_both_data_and_exec(self, monkeypatch):
        """Single login: broker handles both data and execution."""
        from brokers.session import get_data_broker, get_execution_broker

        self._reset()
        mock = MockBrokerAPI()
        monkeypatch.setattr(session_mod, "_make_broker", lambda choice: ("fyers", mock))
        monkeypatch.setattr(mock, "is_authenticated", lambda: True)

        session_mod.login("5")
        assert get_data_broker() is mock
        assert get_execution_broker() is mock

    def test_connect_moves_exec_pointer_only(self, monkeypatch):
        """connect() moves _exec_key; _data_key stays on the login broker."""
        from brokers.session import get_data_broker, get_execution_broker

        fyers_mock = MockBrokerAPI()
        zerodha_mock = MockBrokerAPI()
        self._reset()
        session_mod._brokers = {"fyers": fyers_mock}
        session_mod._primary_key = "fyers"
        session_mod._data_key = "fyers"
        session_mod._exec_key = "fyers"

        monkeypatch.setattr(session_mod, "_make_broker", lambda choice: ("zerodha", zerodha_mock))
        monkeypatch.setattr(zerodha_mock, "is_authenticated", lambda: True)
        monkeypatch.setattr(session_mod, "_print_welcome", lambda *a, **kw: None)

        session_mod.connect_broker("1")
        assert get_data_broker() is fyers_mock  # data unchanged
        assert get_execution_broker() is zerodha_mock  # exec moved

    def test_register_broker_fills_empty_slots(self):
        from brokers.session import register_broker, get_data_broker, get_execution_broker

        self._reset()
        mock = MockBrokerAPI()
        register_broker("fyers", mock, primary=True)
        assert get_data_broker() is mock
        assert get_execution_broker() is mock

    def test_dual_broker_routing_after_login_and_connect(self, monkeypatch):
        """After fyers login + zerodha connect, routing resolves correctly."""
        from brokers.session import get_data_broker, get_execution_broker

        fyers_mock = MockBrokerAPI()
        zerodha_mock = MockBrokerAPI()
        self._reset()

        monkeypatch.setattr(session_mod, "_make_broker", lambda choice: ("fyers", fyers_mock))
        monkeypatch.setattr(fyers_mock, "is_authenticated", lambda: True)
        session_mod.login("5")

        monkeypatch.setattr(session_mod, "_make_broker", lambda choice: ("zerodha", zerodha_mock))
        monkeypatch.setattr(zerodha_mock, "is_authenticated", lambda: True)
        monkeypatch.setattr(session_mod, "_print_welcome", lambda *a, **kw: None)
        session_mod.connect_broker("1")

        assert get_data_broker() is fyers_mock
        assert get_execution_broker() is zerodha_mock


# ── Independent pointer switching ────────────────────────────


class TestIndependentPointers:
    """_data_key and _exec_key are independent — moving one never touches the other."""

    def _setup(self):
        session_mod._brokers = {"fyers": MockBrokerAPI(), "zerodha": MockBrokerAPI()}
        session_mod._primary_key = "fyers"
        session_mod._data_key = "fyers"
        session_mod._exec_key = "zerodha"

    def test_set_exec_broker_does_not_change_data(self):
        from brokers.session import set_exec_broker

        self._setup()
        set_exec_broker("fyers")

        assert session_mod._exec_key == "fyers"
        assert session_mod._data_key == "fyers"  # unchanged

    def test_set_data_broker_does_not_change_exec(self):
        from brokers.session import set_data_broker

        self._setup()
        set_data_broker("zerodha")

        assert session_mod._data_key == "zerodha"
        assert session_mod._exec_key == "zerodha"  # unchanged

    def test_same_broker_can_be_both(self):
        from brokers.session import set_exec_broker, get_data_broker, get_execution_broker

        self._setup()
        fyers = session_mod._brokers["fyers"]
        set_exec_broker("fyers")

        assert get_data_broker() is fyers
        assert get_execution_broker() is fyers
        assert session_mod.get_broker_role("fyers") == "both"

    def test_get_broker_role_data(self):
        self._setup()
        assert session_mod.get_broker_role("fyers") == "data"
        assert session_mod.get_broker_role("zerodha") == "execution"

    def test_get_broker_role_both(self):
        self._setup()
        session_mod._exec_key = "fyers"  # both point to fyers
        assert session_mod.get_broker_role("fyers") == "both"

    def test_get_broker_role_unrouted(self):
        self._setup()
        session_mod._brokers["groww"] = MockBrokerAPI()
        # groww is connected but not pointed to by either key
        assert session_mod.get_broker_role("groww") == ""
