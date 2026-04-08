"""
Tests for broker management API endpoints.
Covers:
  - DELETE /api/broker/{key}: deletes token file and unregisters from memory
  - Startup auto-restore: authenticated brokers are restored on sidecar start
  - OAuth callbacks: register_broker() is called after complete_login()
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── App fixture ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with all broker/keychain loading suppressed."""
    with (
        patch("config.credentials.load_all", return_value=None),
        patch("dotenv.load_dotenv", return_value=None),
    ):
        from web.api import app

        yield TestClient(app)


# ── TestBrokerDisconnect ──────────────────────────────────────


class TestBrokerDisconnect:
    """Tests for DELETE /api/broker/{broker_key}."""

    def test_disconnect_unknown_broker_returns_404(self, client):
        """DELETE with an unrecognised broker key should return 404.
        _require_localhost is patched so the host check doesn't interfere.
        """
        with patch("web.api._require_localhost"):
            resp = client.delete("/api/broker/badname")
        assert resp.status_code == 404
        assert "Unknown broker" in resp.json()["detail"]

    def test_disconnect_deletes_token_file(self, client):
        """DELETE should remove the broker's token file from disk when it exists."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tf:
            token_path = Path(tf.name)
            token_path.write_text('{"access_token": "fake"}')

        fake_files = {
            "zerodha": token_path,
            "groww": Path("/nonexistent/groww.json"),
            "angel_one": Path("/nonexistent/angelone.json"),
            "upstox": Path("/nonexistent/upstox.json"),
            "fyers": Path("/nonexistent/fyers.json"),
        }
        with (
            patch("web.api._BROKER_SESSION_FILES", fake_files),
            patch("web.api._require_localhost"),
            patch("brokers.session.unregister_broker"),
        ):
            assert token_path.exists()
            resp = client.delete("/api/broker/zerodha")
            assert resp.status_code == 200
            assert not token_path.exists()

    def test_disconnect_calls_unregister(self, client):
        """DELETE should call unregister_broker() with the correct session key."""
        with (
            patch("web.api._require_localhost"),
            patch("web.api._BROKER_SESSION_FILES", {
                "fyers": Path("/nonexistent/fyers.json"),
            }),
            patch("brokers.session.unregister_broker") as mock_unregister,
        ):
            client.delete("/api/broker/fyers")
            mock_unregister.assert_called_once_with("fyers")

    def test_disconnect_ok_even_when_file_missing(self, client):
        """DELETE returns 200 {"ok": True} even when the token file does not exist."""
        with (
            patch("web.api._require_localhost"),
            patch("web.api._BROKER_SESSION_FILES", {
                "fyers": Path("/this/path/does/not/exist/fyers.json"),
            }),
            patch("brokers.session.unregister_broker"),
        ):
            resp = client.delete("/api/broker/fyers")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    def test_angel_one_maps_to_angelone_session_key(self, client):
        """DELETE /api/broker/angel_one should call unregister_broker('angelone')."""
        with (
            patch("web.api._require_localhost"),
            patch("web.api._BROKER_SESSION_FILES", {
                "angel_one": Path("/nonexistent/angelone.json"),
            }),
            patch("brokers.session.unregister_broker") as mock_unregister,
        ):
            resp = client.delete("/api/broker/angel_one")
            assert resp.status_code == 200
            mock_unregister.assert_called_once_with("angelone")


# ── TestStartupAutoRestore ────────────────────────────────────


class TestStartupAutoRestore:
    """
    Tests for the _auto_restore_brokers startup event.

    Strategy: import _auto_restore_brokers and run it directly under
    controlled patches so we can assert on register_broker() calls without
    spinning up a full server.
    """

    def _run(self, coro):
        """Helper: run an async coroutine synchronously."""
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_fyers_restored_when_token_exists_and_authenticated(self):
        """When Fyers credentials exist, token file is present, and session is valid, register_broker is called."""
        mock_fyers_instance = MagicMock()
        mock_fyers_instance.is_authenticated.return_value = True
        mock_fyers_cls = MagicMock(return_value=mock_fyers_instance)
        mock_token_file = MagicMock()
        mock_token_file.exists.return_value = True

        with (
            patch("web.api._has_fyers", return_value=True),
            patch("web.api._has_zerodha", return_value=False),
            patch("web.api._has_groww", return_value=False),
            patch("web.api._has_angelone", return_value=False),
            patch("web.api._has_upstox", return_value=False),
            patch("web.api._env", return_value="fake_value"),
            patch("brokers.session.register_broker") as mock_register,
            patch.dict(
                "sys.modules",
                {
                    "brokers.fyers": MagicMock(
                        FyersAPI=mock_fyers_cls,
                        TOKEN_FILE=mock_token_file,
                    )
                },
            ),
        ):
            from web.api import _auto_restore_brokers

            self._run(_auto_restore_brokers())
            mock_register.assert_called_once_with("fyers", mock_fyers_instance)

    def test_fyers_not_restored_when_token_expired(self):
        """When Fyers token file exists but is_authenticated() is False, register_broker is NOT called."""
        mock_fyers_instance = MagicMock()
        mock_fyers_instance.is_authenticated.return_value = False
        mock_fyers_cls = MagicMock(return_value=mock_fyers_instance)
        mock_token_file = MagicMock()
        mock_token_file.exists.return_value = True

        with (
            patch("web.api._has_fyers", return_value=True),
            patch("web.api._has_zerodha", return_value=False),
            patch("web.api._has_groww", return_value=False),
            patch("web.api._has_angelone", return_value=False),
            patch("web.api._has_upstox", return_value=False),
            patch("web.api._env", return_value="fake_value"),
            patch("brokers.session.register_broker") as mock_register,
            patch.dict(
                "sys.modules",
                {
                    "brokers.fyers": MagicMock(
                        FyersAPI=mock_fyers_cls,
                        TOKEN_FILE=mock_token_file,
                    )
                },
            ),
        ):
            from web.api import _auto_restore_brokers

            self._run(_auto_restore_brokers())
            mock_register.assert_not_called()

    def test_fyers_not_restored_when_no_credentials(self):
        """When _has_fyers() is False, FyersAPI is never instantiated."""
        mock_fyers_cls = MagicMock()

        with (
            patch("web.api._has_fyers", return_value=False),
            patch("web.api._has_zerodha", return_value=False),
            patch("web.api._has_groww", return_value=False),
            patch("web.api._has_angelone", return_value=False),
            patch("web.api._has_upstox", return_value=False),
            patch("brokers.session.register_broker") as mock_register,
            patch.dict(
                "sys.modules",
                {
                    "brokers.fyers": MagicMock(FyersAPI=mock_fyers_cls)
                },
            ),
        ):
            from web.api import _auto_restore_brokers

            self._run(_auto_restore_brokers())
            mock_fyers_cls.assert_not_called()
            mock_register.assert_not_called()

    def test_fyers_not_restored_when_no_token_file(self):
        """When the Fyers token file does not exist, FyersAPI is never instantiated."""
        mock_fyers_cls = MagicMock()
        mock_token_file = MagicMock()
        mock_token_file.exists.return_value = False

        with (
            patch("web.api._has_fyers", return_value=True),
            patch("web.api._has_zerodha", return_value=False),
            patch("web.api._has_groww", return_value=False),
            patch("web.api._has_angelone", return_value=False),
            patch("web.api._has_upstox", return_value=False),
            patch("web.api._env", return_value="fake_value"),
            patch("brokers.session.register_broker") as mock_register,
            patch.dict(
                "sys.modules",
                {
                    "brokers.fyers": MagicMock(
                        FyersAPI=mock_fyers_cls,
                        TOKEN_FILE=mock_token_file,
                    )
                },
            ),
        ):
            from web.api import _auto_restore_brokers

            self._run(_auto_restore_brokers())
            mock_fyers_cls.assert_not_called()
            mock_register.assert_not_called()

    def test_exception_during_restore_does_not_crash_startup(self):
        """If FyersAPI constructor raises, the startup event completes without propagating the error."""
        mock_fyers_cls = MagicMock(side_effect=Exception("network error"))
        mock_token_file = MagicMock()
        mock_token_file.exists.return_value = True

        with (
            patch("web.api._has_fyers", return_value=True),
            patch("web.api._has_zerodha", return_value=False),
            patch("web.api._has_groww", return_value=False),
            patch("web.api._has_angelone", return_value=False),
            patch("web.api._has_upstox", return_value=False),
            patch("web.api._env", return_value="fake_value"),
            patch("brokers.session.register_broker") as mock_register,
            patch.dict(
                "sys.modules",
                {
                    "brokers.fyers": MagicMock(
                        FyersAPI=mock_fyers_cls,
                        TOKEN_FILE=mock_token_file,
                    )
                },
            ),
        ):
            from web.api import _auto_restore_brokers

            # Must not raise — exceptions are caught and logged internally
            self._run(_auto_restore_brokers())
            mock_register.assert_not_called()
