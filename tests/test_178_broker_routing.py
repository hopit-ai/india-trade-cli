"""
Tests for GitHub issue #178: Intelligent broker routing.

Covers:
  - auto_assign_roles(): both fyers+zerodha → auto-assigns correctly
  - auto_assign_roles(): only zerodha → no assignment, returns False
  - auto_assign_roles(): after assignment, get_data_broker() returns fyers mock
  - POST /api/broker/role: valid body → 200 OK
  - POST /api/broker/role: invalid role → 400
  - POST /api/broker/role: unknown broker → 404
  - GET /api/status: includes role field per broker
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from brokers.mock import MockBrokerAPI


# ── Session reset helper ──────────────────────────────────────


def _reset_session():
    import brokers.session as sess

    sess._brokers.clear()
    sess._primary_key = ""
    sess._data_key = ""
    sess._exec_key = ""


@pytest.fixture(autouse=True)
def clean_session():
    _reset_session()
    yield
    _reset_session()


def _make_mock() -> MockBrokerAPI:
    b = MockBrokerAPI()
    b.complete_login()
    return b


# ── App fixture ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with all broker/keychain loading suppressed."""
    import os

    os.environ["DEPLOY_MODE"] = "self-hosted"
    os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app

        yield TestClient(app)


# ── auto_assign_roles() unit tests ───────────────────────────


class TestAutoAssignRoles:
    def test_both_fyers_and_zerodha_auto_assigns(self):
        """When both fyers and zerodha are connected, auto_assign_roles sets them correctly."""
        import brokers.session as sess
        from brokers.session import auto_assign_roles

        fyers_mock = _make_mock()
        zerodha_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        result = auto_assign_roles()

        assert result is True
        assert sess._data_key == "fyers"
        assert sess._exec_key == "zerodha"

    def test_only_zerodha_returns_false(self):
        """When only zerodha is connected (no fyers), auto_assign_roles returns False."""
        import brokers.session as sess
        from brokers.session import auto_assign_roles

        zerodha_mock = _make_mock()
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        result = auto_assign_roles()

        assert result is False
        # Keys should remain unchanged
        assert sess._data_key == ""
        assert sess._exec_key == ""

    def test_only_fyers_returns_false(self):
        """When only fyers is connected (no zerodha), auto_assign_roles returns False."""
        import brokers.session as sess
        from brokers.session import auto_assign_roles

        fyers_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._primary_key = "fyers"

        result = auto_assign_roles()

        assert result is False

    def test_empty_brokers_returns_false(self):
        """When no brokers are connected, auto_assign_roles returns False."""
        from brokers.session import auto_assign_roles

        result = auto_assign_roles()

        assert result is False

    def test_after_assignment_get_data_broker_returns_fyers(self):
        """After auto_assign_roles(), get_data_broker() returns the fyers instance."""
        import brokers.session as sess
        from brokers.session import auto_assign_roles, get_data_broker

        fyers_mock = _make_mock()
        zerodha_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        auto_assign_roles()

        broker = get_data_broker()
        assert broker is fyers_mock

    def test_after_assignment_get_execution_broker_returns_zerodha(self):
        """After auto_assign_roles(), get_execution_broker() returns the zerodha instance."""
        import brokers.session as sess
        from brokers.session import auto_assign_roles, get_execution_broker

        fyers_mock = _make_mock()
        zerodha_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        auto_assign_roles()

        broker = get_execution_broker()
        assert broker is zerodha_mock


# ── POST /api/broker/role endpoint tests ─────────────────────


class TestBrokerRoleEndpoint:
    def test_valid_role_returns_200(self, client, clean_session):
        """POST /api/broker/role with valid body returns 200 OK."""
        import brokers.session as sess

        fyers_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._primary_key = "fyers"

        with patch("web.api._require_localhost"):
            resp = client.post("/api/broker/role", json={"broker": "fyers", "role": "data"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["broker"] == "fyers"
        assert data["role"] == "data"

    def test_invalid_role_returns_400(self, client, clean_session):
        """POST /api/broker/role with invalid role returns 400."""
        import brokers.session as sess

        # Broker must be connected for role validation to run (broker check is first)
        fyers_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._primary_key = "fyers"

        with patch("web.api._require_localhost"):
            resp = client.post("/api/broker/role", json={"broker": "fyers", "role": "unknown"})

        assert resp.status_code == 400

    def test_unknown_broker_returns_404(self, client, clean_session):
        """POST /api/broker/role with unconnected broker returns 404."""
        import brokers.session as sess

        # Ensure fyers is NOT in _brokers
        sess._brokers.pop("fyers", None)

        with patch("web.api._require_localhost"):
            resp = client.post("/api/broker/role", json={"broker": "fyers", "role": "data"})

        assert resp.status_code == 404
        assert "fyers" in resp.json()["detail"]

    def test_execution_role_sets_exec_key(self, client, clean_session):
        """POST /api/broker/role with role='execution' sets the execution broker."""
        import brokers.session as sess

        zerodha_mock = _make_mock()
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        with patch("web.api._require_localhost"):
            resp = client.post("/api/broker/role", json={"broker": "zerodha", "role": "execution"})

        assert resp.status_code == 200
        assert sess._exec_key == "zerodha"

    def test_both_role_sets_both_keys(self, client, clean_session):
        """POST /api/broker/role with role='both' sets data and exec keys."""
        import brokers.session as sess

        zerodha_mock = _make_mock()
        sess._brokers["zerodha"] = zerodha_mock
        sess._primary_key = "zerodha"

        with patch("web.api._require_localhost"):
            resp = client.post("/api/broker/role", json={"broker": "zerodha", "role": "both"})

        assert resp.status_code == 200
        assert sess._data_key == "zerodha"
        assert sess._exec_key == "zerodha"


# ── GET /api/status role field tests ─────────────────────────


class TestApiStatusRoleField:
    def test_status_includes_role_field_for_each_broker(self, client):
        """GET /api/status returns role field for each broker entry."""
        with patch("web.api._require_localhost"):
            resp = client.get("/api/status")

        assert resp.status_code == 200
        data = resp.json()
        # Each broker entry should have a 'role' key
        for broker_name in ("zerodha", "groww", "fyers", "upstox"):
            assert broker_name in data, f"Missing broker {broker_name!r} in status"
            assert "role" in data[broker_name], f"Missing 'role' in {broker_name!r} status"

    def test_status_role_reflects_assigned_roles(self, client, clean_session):
        """GET /api/status returns correct role when brokers are assigned."""
        import brokers.session as sess

        fyers_mock = _make_mock()
        zerodha_mock = _make_mock()
        sess._brokers["fyers"] = fyers_mock
        sess._brokers["zerodha"] = zerodha_mock
        sess._data_key = "fyers"
        sess._exec_key = "zerodha"

        with patch("web.api._require_localhost"):
            resp = client.get("/api/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["fyers"]["role"] == "data"
        assert data["zerodha"]["role"] == "execution"
