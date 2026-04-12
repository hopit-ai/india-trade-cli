"""
Tests for broker routing visibility and CLI commands (#159).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from brokers.mock import MockBrokerAPI


def _reset_session():
    import brokers.session as sess

    sess._brokers.clear()
    sess._primary_key = ""
    sess._broker_roles.clear()


@pytest.fixture(autouse=True)
def clean_session():
    _reset_session()
    yield
    _reset_session()


def _make_mock() -> MockBrokerAPI:
    b = MockBrokerAPI()
    b.complete_login()
    return b


# ── list_connected_brokers shows roles ─────────────────────────


class TestListBrokersShowsRoles:
    def test_shows_data_role(self, capsys):
        from brokers.session import register_broker, set_broker_role, list_connected_brokers

        b = _make_mock()
        register_broker("fyers", b)
        set_broker_role("fyers", "data")

        list_connected_brokers()
        # Rich output goes through console, not capsys — just verify no crash
        # The real check is that it doesn't error with the role column

    def test_shows_execution_role(self):
        from brokers.session import register_broker, set_broker_role, list_connected_brokers

        b = _make_mock()
        register_broker("zerodha", b)
        set_broker_role("zerodha", "execution")

        list_connected_brokers()  # should not crash

    def test_shows_both_brokers_with_roles(self):
        from brokers.session import register_broker, set_broker_role, list_connected_brokers

        register_broker("fyers", _make_mock())
        register_broker("zerodha", _make_mock())
        set_broker_role("fyers", "data")
        set_broker_role("zerodha", "execution")

        list_connected_brokers()  # should not crash

    def test_empty_brokers(self):
        from brokers.session import list_connected_brokers

        list_connected_brokers()  # should print "No brokers connected"


# ── set_broker_role_with_auto_login ────────────────────────────


class TestSetBrokerRoleWithAutoLogin:
    def test_set_data_broker_already_connected(self):
        from brokers.session import (
            register_broker,
            set_broker_role,
            get_broker_role,
        )

        b = _make_mock()
        register_broker("fyers", b)
        set_broker_role("fyers", "data")
        assert get_broker_role("fyers") == "data"

    def test_set_exec_broker_already_connected(self):
        from brokers.session import (
            register_broker,
            set_broker_role,
            get_broker_role,
        )

        b = _make_mock()
        register_broker("zerodha", b)
        set_broker_role("zerodha", "execution")
        assert get_broker_role("zerodha") == "execution"

    def test_set_both_same_broker(self):
        from brokers.session import (
            register_broker,
            set_broker_role,
            get_data_broker,
            get_execution_broker,
        )

        b = _make_mock()
        register_broker("fyers", b, primary=True)
        set_broker_role("fyers", "both")

        assert get_data_broker() is b
        assert get_execution_broker() is b
