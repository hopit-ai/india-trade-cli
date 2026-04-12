"""
Tests for dual-broker role-based routing (#129).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from brokers.mock import MockBrokerAPI


# ── Helpers ──────────────────────────────────────────────────────


def _reset_session():
    """Reset the global session state between tests."""
    import brokers.session as sess

    sess._brokers.clear()
    sess._primary_key = ""
    sess._broker_roles.clear()


@pytest.fixture(autouse=True)
def clean_session():
    _reset_session()
    yield
    _reset_session()


def _make_mock(name: str = "mock") -> MockBrokerAPI:
    b = MockBrokerAPI()
    b.complete_login()
    return b


# ── Unit tests ───────────────────────────────────────────────────


def test_set_and_get_broker_role():
    from brokers.session import register_broker, set_broker_role, get_broker_role

    b = _make_mock()
    register_broker("fyers", b)

    set_broker_role("fyers", "data")
    assert get_broker_role("fyers") == "data"

    set_broker_role("fyers", "execution")
    assert get_broker_role("fyers") == "execution"

    set_broker_role("fyers", "both")
    assert get_broker_role("fyers") == "both"


def test_get_broker_role_default():
    from brokers.session import register_broker, get_broker_role

    b = _make_mock()
    register_broker("mock", b)
    # Non-default broker with no explicit role — should return "both"
    assert get_broker_role("mock") == "both"


def test_get_broker_role_fyers_auto_assigns_data():
    from brokers.session import register_broker, get_broker_role

    b = _make_mock()
    register_broker("fyers", b)
    # fyers auto-assigns to "data"
    assert get_broker_role("fyers") == "data"


def test_get_data_broker_returns_data_role():
    from brokers.session import register_broker, set_broker_role, get_data_broker

    fyers_mock = _make_mock()
    zerodha_mock = _make_mock()
    register_broker("fyers", fyers_mock, primary=True)
    register_broker("zerodha", zerodha_mock)

    set_broker_role("fyers", "data")
    set_broker_role("zerodha", "execution")

    assert get_data_broker() is fyers_mock


def test_get_execution_broker_returns_execution_role():
    from brokers.session import register_broker, set_broker_role, get_execution_broker

    fyers_mock = _make_mock()
    zerodha_mock = _make_mock()
    register_broker("fyers", fyers_mock, primary=True)
    register_broker("zerodha", zerodha_mock)

    set_broker_role("fyers", "data")
    set_broker_role("zerodha", "execution")

    assert get_execution_broker() is zerodha_mock


def test_get_data_broker_falls_back_to_primary():
    from brokers.session import register_broker, get_data_broker

    b = _make_mock()
    register_broker("mock", b, primary=True)
    # No roles set at all — should fall back to primary
    assert get_data_broker() is b


def test_get_execution_broker_falls_back_to_primary():
    from brokers.session import register_broker, get_execution_broker

    b = _make_mock()
    register_broker("mock", b, primary=True)
    assert get_execution_broker() is b


def test_auto_assign_roles_fyers_data_zerodha_execution():
    from brokers.session import register_broker, get_broker_role

    fyers_mock = _make_mock()
    zerodha_mock = _make_mock()

    # register_broker should auto-assign roles based on broker key
    register_broker("fyers", fyers_mock)
    register_broker("zerodha", zerodha_mock)

    assert get_broker_role("fyers") == "data"
    assert get_broker_role("zerodha") == "execution"


def test_both_role_matches_data_and_execution():
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


def test_unregister_clears_role():
    from brokers.session import register_broker, set_broker_role, get_broker_role, unregister_broker

    b = _make_mock()
    register_broker("fyers", b)
    set_broker_role("fyers", "data")
    assert get_broker_role("fyers") == "data"

    unregister_broker("fyers")
    # After unregister, role should be gone (default "both")
    assert get_broker_role("fyers") == "both"


def test_invalid_role_raises():
    from brokers.session import register_broker, set_broker_role

    b = _make_mock()
    register_broker("fyers", b)

    with pytest.raises(ValueError):
        set_broker_role("fyers", "invalid")


# ── API tests ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient with auth suppressed."""
    os.environ["DEPLOY_MODE"] = "self-hosted"
    os.environ["AUTH_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app
        from fastapi.testclient import TestClient

        yield TestClient(app)


def test_status_includes_roles(client):
    from brokers.session import register_broker, set_broker_role

    b = _make_mock()
    register_broker("fyers", b)
    set_broker_role("fyers", "data")

    with patch("web.api._require_localhost"):
        resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "fyers" in data
    assert data["fyers"]["role"] == "data"


def test_role_endpoint(client):
    from brokers.session import register_broker, get_broker_role

    b = _make_mock()
    register_broker("fyers", b)

    with patch("web.api._require_localhost"):
        resp = client.post(
            "/api/broker/role",
            json={"broker": "fyers", "role": "execution"},
        )
    assert resp.status_code == 200
    assert get_broker_role("fyers") == "execution"


def test_role_endpoint_invalid_broker(client):
    with patch("web.api._require_localhost"):
        resp = client.post(
            "/api/broker/role",
            json={"broker": "nonexistent", "role": "data"},
        )
    assert resp.status_code == 404


def test_role_endpoint_invalid_role(client):
    from brokers.session import register_broker

    b = _make_mock()
    register_broker("fyers", b)

    with patch("web.api._require_localhost"):
        resp = client.post(
            "/api/broker/role",
            json={"broker": "fyers", "role": "invalid"},
        )
    assert resp.status_code == 400
