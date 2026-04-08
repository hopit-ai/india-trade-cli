"""
Tests for the new unregister_broker() function and updated broker session management.
Covers the broker session restoration fix (Issue: profile/funds showing demo data).
"""

import pytest

import brokers.session as session_mod
from brokers.session import (
    get_broker,
    get_all_brokers,
    register_broker,
    unregister_broker,
)
from brokers.mock import MockBrokerAPI


# ── TestUnregisterBroker ──────────────────────────────────────


class TestUnregisterBroker:
    """Tests for the unregister_broker() function."""

    def setup_method(self):
        """Reset module state before each test."""
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_unregister_removes_broker(self):
        """Registering then unregistering a broker removes it from get_all_brokers()."""
        mock = MockBrokerAPI()
        register_broker("mock", mock, primary=True)
        assert "mock" in get_all_brokers()

        unregister_broker("mock")

        assert "mock" not in get_all_brokers()

    def test_unregister_nonexistent_is_noop(self):
        """Unregistering a key that was never registered should not raise."""
        # No setup — _brokers is empty
        unregister_broker("nonexistent_broker")  # must not raise

    def test_unregister_primary_promotes_next(self):
        """When the primary broker is unregistered and another exists, the next broker becomes primary."""
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        register_broker("mock", mock1, primary=True)
        register_broker("secondary", mock2, primary=False)
        assert session_mod._primary_key == "mock"

        unregister_broker("mock")

        # The remaining broker should now be primary
        assert session_mod._primary_key == "secondary"
        assert get_broker() is mock2

    def test_unregister_primary_clears_key_when_last(self):
        """When the only registered broker is unregistered, get_broker() raises RuntimeError."""
        mock = MockBrokerAPI()
        register_broker("mock", mock, primary=True)

        unregister_broker("mock")

        assert session_mod._primary_key == ""
        with pytest.raises(RuntimeError, match="No broker is connected"):
            get_broker()

    def test_unregister_secondary_keeps_primary(self):
        """Unregistering a non-primary broker leaves the primary broker unchanged."""
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        register_broker("mock", mock1, primary=True)
        register_broker("secondary", mock2, primary=False)
        assert session_mod._primary_key == "mock"

        unregister_broker("secondary")

        assert session_mod._primary_key == "mock"
        assert get_broker() is mock1
        assert "secondary" not in get_all_brokers()


# ── TestRegisterBrokerPrimary ─────────────────────────────────


class TestRegisterBrokerPrimary:
    """Extended coverage for register_broker() primary-selection logic."""

    def setup_method(self):
        """Reset module state before each test."""
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def teardown_method(self):
        session_mod._brokers = {}
        session_mod._primary_key = ""

    def test_first_registration_becomes_primary(self):
        """The very first registered broker should always become primary."""
        mock = MockBrokerAPI()
        register_broker("mock", mock, primary=False)

        # Even with primary=False, the first broker must be primary because
        # _primary_key was empty.
        assert session_mod._primary_key == "mock"
        assert get_broker() is mock

    def test_second_registration_with_primary_true_overrides_primary(self):
        """A second broker registered with primary=True becomes the new primary."""
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        register_broker("mock", mock1, primary=True)
        register_broker("secondary", mock2, primary=True)

        assert session_mod._primary_key == "secondary"
        assert get_broker() is mock2

    def test_second_registration_with_primary_false_keeps_original_primary(self):
        """A second broker registered with primary=False must not change the existing primary."""
        mock1 = MockBrokerAPI()
        mock2 = MockBrokerAPI()
        register_broker("mock", mock1, primary=True)
        register_broker("secondary", mock2, primary=False)

        assert session_mod._primary_key == "mock"
        assert get_broker() is mock1
        assert "secondary" in get_all_brokers()
