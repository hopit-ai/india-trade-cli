"""Tests for brokers/session.py — session management, broker registry."""

import pytest
from unittest.mock import patch, MagicMock

import brokers.session as session_mod
from brokers.session import (
    _BROKER_NAMES, _BROKER_LABELS, _BROKER_MENU,
    get_broker, get_all_brokers, is_multi_broker, register_broker,
)
from brokers.mock import MockBrokerAPI


# ── Broker name mapping ─────────────────────────────────────

class TestBrokerNames:
    def test_numeric_choices(self):
        assert _BROKER_NAMES["0"] == "mock"
        assert _BROKER_NAMES["1"] == "zerodha"
        assert _BROKER_NAMES["2"] == "groww"
        assert _BROKER_NAMES["3"] == "angelone"
        assert _BROKER_NAMES["4"] == "upstox"
        assert _BROKER_NAMES["5"] == "fyers"

    def test_name_choices(self):
        assert _BROKER_NAMES["demo"] == "mock"
        assert _BROKER_NAMES["zerodha"] == "zerodha"
        assert _BROKER_NAMES["groww"] == "groww"
        assert _BROKER_NAMES["angel"] == "angelone"

    def test_all_labels_exist(self):
        for key in ("mock", "zerodha", "groww", "angelone", "upstox", "fyers"):
            assert key in _BROKER_LABELS

    def test_menu_has_all_entries(self):
        nums = [num for num, _, _ in _BROKER_MENU]
        assert "0" in nums
        assert "5" in nums
        assert len(_BROKER_MENU) == 6


# ── get_broker / get_all_brokers ─────────────────────────────

class TestBrokerAccessors:
    def setup_method(self):
        """Reset module state before each test."""
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_get_broker_raises_when_not_logged_in(self):
        with pytest.raises(RuntimeError, match="No active broker"):
            get_broker()

    def test_get_all_brokers_empty(self):
        assert get_all_brokers() == {}

    def test_is_multi_broker_false_when_empty(self):
        assert is_multi_broker() is False

    def test_get_broker_returns_primary(self):
        mock = MockBrokerAPI()
        mock.complete_login()
        session_mod._brokers["mock"] = mock
        session_mod._primary_key = "mock"
        assert get_broker() is mock

    def test_is_multi_broker_true(self):
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        session_mod._brokers = {"mock": mock1, "zerodha": mock2}
        session_mod._primary_key = "mock"
        assert is_multi_broker() is True

    def test_get_all_brokers_returns_copy(self):
        mock = MockBrokerAPI()
        session_mod._brokers["mock"] = mock
        result = get_all_brokers()
        assert result == {"mock": mock}
        # Should be a copy
        result["new"] = "test"
        assert "new" not in session_mod._brokers


# ── _make_broker ─────────────────────────────────────────────

class TestMakeBroker:
    def test_mock_broker(self):
        key, broker = session_mod._make_broker("0")
        assert key == "mock"
        assert isinstance(broker, MockBrokerAPI)

    def test_mock_by_name(self):
        key, broker = session_mod._make_broker("demo")
        assert key == "mock"

    def test_unknown_choice_raises(self):
        with pytest.raises(SystemExit):
            session_mod._make_broker("99")


# ── logout ───────────────────────────────────────────────────

class TestLogout:
    def setup_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_logout_clears_all(self):
        mock = MockBrokerAPI()
        mock.complete_login()
        session_mod._brokers["mock"] = mock
        session_mod._primary_key = "mock"

        session_mod.logout()
        assert session_mod._brokers == {}
        assert session_mod._primary_key == ""

    def test_logout_when_empty(self):
        session_mod.logout()  # should not raise


# ── disconnect_broker ────────────────────────────────────────

class TestDisconnectBroker:
    def setup_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_disconnect_when_empty(self):
        session_mod.disconnect_broker("1")  # should not raise

    def test_cannot_disconnect_primary(self):
        mock = MockBrokerAPI()
        session_mod._brokers["mock"] = mock
        session_mod._primary_key = "mock"
        session_mod.disconnect_broker("0")  # prints error but doesn't crash
        assert "mock" in session_mod._brokers  # still there


# ── register_broker ──────────────────────────────────────────

class TestRegisterBroker:
    def setup_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_register_sets_primary(self):
        mock = MockBrokerAPI()
        register_broker("mock", mock, primary=True)
        assert get_broker() is mock
        assert session_mod._primary_key == "mock"

    def test_register_non_primary(self):
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        register_broker("mock", mock1, primary=True)
        register_broker("secondary", mock2, primary=False)
        assert get_broker() is mock1  # primary unchanged
        assert is_multi_broker() is True

    def test_register_first_broker_always_primary(self):
        mock = MockBrokerAPI()
        register_broker("mock", mock, primary=False)
        # First broker becomes primary even if primary=False
        assert session_mod._primary_key == "mock"
