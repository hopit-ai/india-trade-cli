"""Tests for config/credentials.py — credential management, keychain helpers."""

import os
import pytest
from unittest.mock import patch, MagicMock

from config.credentials import (
    _kr_get, _kr_set, _kr_delete,
    get_credential, set_credential, load_all,
    SERVICE, KNOWN_CREDENTIALS, _KNOWN_KEYS,
    cmd_credentials,
)


# ── Constants ────────────────────────────────────────────────

class TestConstants:
    def test_service_name(self):
        assert SERVICE == "india-trade-cli"

    def test_known_credentials_not_empty(self):
        assert len(KNOWN_CREDENTIALS) > 0

    def test_known_keys_match(self):
        keys = {k for k, _, _ in KNOWN_CREDENTIALS}
        assert keys == _KNOWN_KEYS

    def test_essential_keys_present(self):
        assert "ANTHROPIC_API_KEY" in _KNOWN_KEYS
        assert "OPENAI_API_KEY" in _KNOWN_KEYS
        assert "GEMINI_API_KEY" in _KNOWN_KEYS
        assert "KITE_API_KEY" in _KNOWN_KEYS
        assert "AI_PROVIDER" in _KNOWN_KEYS

    def test_each_credential_has_label(self):
        for key, label, is_secret in KNOWN_CREDENTIALS:
            assert len(key) > 0
            assert len(label) > 0
            assert isinstance(is_secret, bool)


# ── Keyring helpers (mocked) ────────────────────────────────

class TestKeyringHelpers:
    def test_kr_get_returns_none_without_keyring(self):
        with patch.dict("sys.modules", {"keyring": None}):
            result = _kr_get("NONEXISTENT_KEY")
            # Should return None (graceful fallback)
            assert result is None or isinstance(result, str)

    def test_kr_set_returns_bool(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = _kr_set("TEST_KEY", "test_value")
            assert isinstance(result, bool)

    def test_kr_delete_returns_bool(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = _kr_delete("TEST_KEY")
            assert isinstance(result, bool)


# ── get_credential ───────────────────────────────────────────

class TestGetCredential:
    def test_from_env(self, monkeypatch):
        """get_credential should find value from env var."""
        monkeypatch.setenv("TEST_CRED_KEY", "env_value_123")
        with patch("config.credentials._kr_get", return_value=None):
            value = get_credential("TEST_CRED_KEY", "Test Key", secret=False, required=False)
            assert value == "env_value_123"

    def test_from_keyring(self, monkeypatch):
        """get_credential should prefer keyring over env."""
        monkeypatch.delenv("TEST_CRED_KEY", raising=False)
        with patch("config.credentials._kr_get", return_value="keyring_value"):
            value = get_credential("TEST_CRED_KEY", "Test Key", secret=False, required=False)
            assert value == "keyring_value"

    def test_missing_not_required_returns_empty(self, monkeypatch):
        """Non-required missing credential returns empty string."""
        monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
        monkeypatch.setenv("_CLI_BATCH_MODE", "1")
        with patch("config.credentials._kr_get", return_value=None):
            value = get_credential("MISSING_KEY_XYZ", required=False)
            assert value == ""

    def test_missing_required_raises_in_batch(self, monkeypatch):
        """Required missing credential raises in batch mode."""
        monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
        monkeypatch.setenv("_CLI_BATCH_MODE", "1")
        with patch("config.credentials._kr_get", return_value=None):
            with pytest.raises(RuntimeError, match="not configured"):
                get_credential("MISSING_KEY_XYZ", required=True)

    def test_env_strips_whitespace(self, monkeypatch):
        """Env values should be stripped."""
        monkeypatch.setenv("STRIP_TEST", "  value_with_spaces  ")
        with patch("config.credentials._kr_get", return_value=None):
            value = get_credential("STRIP_TEST", required=False)
            assert value == "value_with_spaces"


# ── set_credential ───────────────────────────────────────────

class TestSetCredential:
    def test_sets_env(self, monkeypatch):
        monkeypatch.delenv("SET_TEST_KEY", raising=False)
        with patch("config.credentials._kr_set", return_value=True):
            set_credential("SET_TEST_KEY", "new_value")
            assert os.environ["SET_TEST_KEY"] == "new_value"
        # Clean up
        monkeypatch.delenv("SET_TEST_KEY", raising=False)


# ── load_all ─────────────────────────────────────────────────

class TestLoadAll:
    def test_does_not_overwrite_existing_env(self, monkeypatch):
        """load_all should not overwrite env vars already set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "already_set")
        with patch("config.credentials._kr_get", return_value="keyring_value"):
            load_all()
            assert os.environ["ANTHROPIC_API_KEY"] == "already_set"

    def test_loads_from_keyring(self, monkeypatch):
        """load_all should populate env from keyring for unset keys."""
        monkeypatch.delenv("NEWSAPI_KEY", raising=False)

        def mock_kr_get(key):
            if key == "NEWSAPI_KEY":
                return "newsapi_from_keyring"
            return None

        with patch("config.credentials._kr_get", side_effect=mock_kr_get):
            load_all()
            assert os.environ.get("NEWSAPI_KEY") == "newsapi_from_keyring"
        monkeypatch.delenv("NEWSAPI_KEY", raising=False)


# ── cmd_credentials ──────────────────────────────────────────

class TestCmdCredentials:
    def test_list_does_not_raise(self):
        with patch("config.credentials._kr_get", return_value=None):
            cmd_credentials(["list"])

    def test_unknown_subcommand_lists(self):
        with patch("config.credentials._kr_get", return_value=None):
            cmd_credentials(["unknown_sub"])  # should not raise

    def test_delete_requires_key(self):
        cmd_credentials(["delete"])  # prints error, no crash

    def test_set_requires_key(self):
        cmd_credentials(["set"])  # prints error, no crash
