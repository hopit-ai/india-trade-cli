"""Tests for the automatic OAuth local callback server (_oauth_local_server)."""

import socket
import threading
import time
import urllib.request
from http.server import HTTPServer

import pytest

from brokers.session import _oauth_local_server


def _free_port() -> int:
    """Return an ephemeral port that is currently unbound."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── Happy path ───────────────────────────────────────────────


class TestOAuthLocalServer:
    def test_captures_fyers_auth_code(self):
        """Browser redirect with auth_code is captured automatically."""
        port = _free_port()

        def _hit():
            time.sleep(0.05)
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/fyers/callback?auth_code=TESTCODE123&state=xyz"
            )

        threading.Thread(target=_hit, daemon=True).start()
        result = _oauth_local_server(port, "/fyers/callback", "auth_code", timeout=5)
        assert result == {"auth_code": "TESTCODE123"}

    def test_captures_zerodha_request_token(self):
        port = _free_port()

        def _hit():
            time.sleep(0.05)
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/zerodha/callback"
                "?request_token=ZTOKEN&status=success"
            )

        threading.Thread(target=_hit, daemon=True).start()
        result = _oauth_local_server(port, "/zerodha/callback", "request_token", timeout=5)
        assert result == {"request_token": "ZTOKEN"}

    def test_captures_upstox_code(self):
        port = _free_port()

        def _hit():
            time.sleep(0.05)
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/upstox/callback?code=UPCODE99"
            )

        threading.Thread(target=_hit, daemon=True).start()
        result = _oauth_local_server(port, "/upstox/callback", "code", timeout=5)
        assert result == {"code": "UPCODE99"}

    def test_success_page_returned_to_browser(self):
        """The server sends a 200 HTML response so the browser shows a success page."""
        port = _free_port()

        def _hit():
            time.sleep(0.05)

        threading.Thread(target=_hit, daemon=True).start()

        port = _free_port()

        result_holder = {}

        def _fetch():
            time.sleep(0.05)
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/fyers/callback?auth_code=ABC"
            )
            result_holder["status"] = resp.status
            result_holder["body"] = resp.read().decode()

        threading.Thread(target=_fetch, daemon=True).start()
        _oauth_local_server(port, "/fyers/callback", "auth_code", timeout=5)

        time.sleep(0.2)
        assert result_holder.get("status") == 200
        assert "Login successful" in result_holder.get("body", "")

    def test_stray_requests_ignored(self):
        """Stray requests (favicon, pre-flight) do not consume the server.
        The real callback still gets captured afterwards."""
        port = _free_port()

        def _requests():
            time.sleep(0.05)
            # Stray request first — server should answer 204 and keep listening
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico")
            except Exception:
                pass
            time.sleep(0.1)
            # Real OAuth callback second
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/fyers/callback?auth_code=REAL123"
                )
            except Exception:
                pass

        threading.Thread(target=_requests, daemon=True).start()
        result = _oauth_local_server(port, "/fyers/callback", "auth_code", timeout=5)
        assert result == {"auth_code": "REAL123"}

    # ── Port busy fallback ────────────────────────────────────

    def test_returns_none_when_port_busy(self):
        """If the port is already in use, returns None so the CLI falls back to manual paste."""
        port = _free_port()
        blocker = HTTPServer(("127.0.0.1", port), None.__class__)  # type: ignore[arg-type]
        try:
            result = _oauth_local_server(port, "/fyers/callback", "auth_code", timeout=2)
            assert result is None
        finally:
            blocker.server_close()

    # ── Timeout ───────────────────────────────────────────────

    def test_returns_none_on_timeout(self):
        """If no redirect arrives within timeout, returns None."""
        port = _free_port()
        result = _oauth_local_server(port, "/fyers/callback", "auth_code", timeout=1)
        assert result is None

    # ── Multiple params ───────────────────────────────────────

    def test_captures_multiple_params(self):
        """Can extract more than one query parameter at once."""
        port = _free_port()

        def _hit():
            time.sleep(0.05)
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/cb?code=CODE&state=STATE"
            )

        threading.Thread(target=_hit, daemon=True).start()
        result = _oauth_local_server(port, "/cb", "code", "state", timeout=5)
        assert result == {"code": "CODE", "state": "STATE"}

    def test_missing_param_returns_empty_string(self):
        """A param listed but absent in the URL comes back as empty string, not KeyError."""
        port = _free_port()

        def _hit():
            time.sleep(0.05)
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/cb?auth_code=ONLY"
            )

        threading.Thread(target=_hit, daemon=True).start()
        result = _oauth_local_server(port, "/cb", "auth_code", "state", timeout=5)
        assert result is not None
        assert result["auth_code"] == "ONLY"
        assert result["state"] == ""
