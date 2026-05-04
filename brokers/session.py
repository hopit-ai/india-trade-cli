"""
brokers/session.py
──────────────────
Multi-broker session manager.

Supports logging into multiple brokers simultaneously (e.g. Zerodha + Groww)
and presenting a unified view of holdings, positions, and funds.

Usage:
    from brokers.session import login, connect_broker, get_broker, get_all_brokers

    # First login (sets the primary broker)
    broker = login()           # interactive choice
    broker = login("1")        # Zerodha
    broker = login("2")        # Groww

    # Connect a second broker (does NOT replace the primary)
    connect_broker("2")        # now both Zerodha + Groww are active

    # Single-broker access (primary)
    broker = get_broker()

    # All brokers (for aggregated views)
    all_brokers = get_all_brokers()   # {"zerodha": ..., "groww": ...}

    # Check if multiple brokers are connected
    if is_multi_broker():
        ...
"""

from __future__ import annotations

import os
import webbrowser
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .base import BrokerAPI
from .mock import MockBrokerAPI

# Lazy-import broker modules — their SDKs (kiteconnect, smartapi-python)
# are optional and may not be installed.  Imported on first use in _get_broker_class().
from config.credentials import get_credential

console = Console()

# ── Module state ──────────────────────────────────────────────
# All connected brokers, keyed by broker name (lowercase)
_brokers: dict[str, BrokerAPI] = {}

# The "primary" broker — used by get_broker() for single-broker commands
_primary_key: str = ""

# Role routing — two independent pointers, can point to the same broker.
# login()  sets both to the logged-in broker.
# connect() moves _exec_key to the newly connected broker.
# set_data_broker() / set_exec_broker() move each pointer independently.
_data_key: str = ""  # which broker supplies market data / quotes
_exec_key: str = ""  # which broker receives orders

# Human-readable names for display
_BROKER_NAMES = {
    "0": "mock",
    "demo": "mock",
    "mock": "mock",
    "1": "zerodha",
    "zerodha": "zerodha",
    "2": "groww",
    "groww": "groww",
    "3": "angelone",
    "angelone": "angelone",
    "angel": "angelone",
    "4": "upstox",
    "upstox": "upstox",
    "5": "fyers",
    "fyers": "fyers",
}

_BROKER_LABELS = {
    "mock": "[dim]Mock / Demo[/dim]",
    "zerodha": "[cyan]Zerodha (Kite)[/cyan]",
    "groww": "[green]Groww[/green]",
    "angelone": "[bold yellow]Angel One (SmartAPI)[/bold yellow]",
    "upstox": "[magenta]Upstox[/magenta]",
    "fyers": "[blue]Fyers[/blue]",
}

# Brokers that use TOTP auto-login (no browser redirect)
_TOTP_BROKERS = {"angelone"}

# Broker menu display items (number, label, description)
_BROKER_MENU = [
    ("0", "Demo", "mock data, no credentials needed"),
    ("1", "Zerodha", "Kite Connect — redirect login"),
    ("2", "Groww", "OAuth2 — redirect login"),
    ("3", "Angel One", "SmartAPI — free, TOTP auto-login"),
    ("4", "Upstox", "API v3 — redirect login"),
    ("5", "Fyers", "API v3 — redirect login"),
]


# ── Public accessors ──────────────────────────────────────────


def register_broker(
    key: str, broker: BrokerAPI, *, primary: bool = False, role: str | None = None
) -> None:
    """
    Register an externally-created broker instance.

    Used by --no-broker mode to inject a MockBrokerAPI without going
    through the interactive login flow.

    Args:
        key:     Broker name (lowercase), e.g. "fyers", "zerodha".
        broker:  Authenticated BrokerAPI instance.
        primary: If True, set as the primary broker.
        role:    Optional role: "data", "execution", or "both".
                 If omitted, the broker fills whichever slot(s) are empty.
    """
    global _brokers, _primary_key, _data_key, _exec_key
    _brokers[key] = broker
    if primary or not _primary_key:
        _primary_key = key
    if role in ("data", "both"):
        _data_key = key
    if role in ("execution", "both"):
        _exec_key = key
    # If no explicit role, fill empty slots so the broker is reachable
    if role is None:
        if not _data_key:
            _data_key = key
        if not _exec_key:
            _exec_key = key


def unregister_broker(key: str) -> None:
    """
    Remove a broker from the in-memory session registry.

    Called when a broker is disconnected via the web API (token file deleted).
    If the disconnected broker was primary and others are connected, the first
    remaining broker becomes the new primary.
    """
    global _brokers, _primary_key, _data_key, _exec_key
    _brokers.pop(key, None)
    if _primary_key == key:
        _primary_key = next(iter(_brokers), "")
    if _data_key == key:
        _data_key = _primary_key
    if _exec_key == key:
        _exec_key = _primary_key


def get_broker() -> BrokerAPI:
    """Return the primary broker. Raises if login() has not been called."""
    if not _primary_key or _primary_key not in _brokers:
        raise RuntimeError(
            "No broker is connected. Run the 'login' command to connect your broker."
        )
    return _brokers[_primary_key]


def get_all_brokers() -> dict[str, BrokerAPI]:
    """Return all connected broker instances, keyed by broker name."""
    return dict(_brokers)


def is_multi_broker() -> bool:
    """True if more than one broker is currently connected."""
    return len(_brokers) > 1


# ── Role-based routing ───────────────────────────────────────────
# Two independent pointers — can point to the same broker ("both").
# Moving one never affects the other.


def get_broker_role(key: str) -> str:
    """Return the display role for a broker: 'data', 'execution', 'both', or ''."""
    is_data = key == _data_key
    is_exec = key == _exec_key
    if is_data and is_exec:
        return "both"
    if is_data:
        return "data"
    if is_exec:
        return "execution"
    return ""  # connected but not currently routed


def get_data_broker() -> BrokerAPI:
    """Return the current data broker. Falls back to primary if unset."""
    if _data_key and _data_key in _brokers:
        return _brokers[_data_key]
    return get_broker()


def get_execution_broker() -> BrokerAPI:
    """Return the current execution broker. Falls back to primary if unset."""
    if _exec_key and _exec_key in _brokers:
        return _brokers[_exec_key]
    return get_broker()


def list_connected_brokers() -> None:
    """Pretty-print a table of all connected brokers with role routing."""
    if not _brokers:
        console.print("[dim]No brokers connected. Run 'login' to connect.[/dim]")
        return

    _ROLE_STYLES = {
        "data": "[bold blue]DATA[/bold blue]",
        "execution": "[bold yellow]EXEC[/bold yellow]",
        "both": "[bold green]BOTH[/bold green]",
        "": "[dim]—[/dim]",
    }

    t = Table(title="Connected Brokers", show_header=True, header_style="bold cyan")
    t.add_column("Broker", style="bold")
    t.add_column("Role", style="dim")
    t.add_column("Account", style="white")
    t.add_column("Cash", justify="right")

    for key, broker in _brokers.items():
        role = get_broker_role(key)
        role_display = _ROLE_STYLES.get(role, role)
        try:
            profile = broker.get_profile()
            funds = broker.get_funds()
            t.add_row(
                _BROKER_LABELS.get(key, key.title()),
                role_display,
                f"{profile.name} ({profile.user_id})",
                f"[green]₹{funds.available_cash:,.0f}[/green]",
            )
        except Exception as e:
            t.add_row(
                _BROKER_LABELS.get(key, key.title()),
                role_display,
                str(e)[:40],
                "—",
            )

    console.print()
    console.print(t)

    # Footer: show the two independent routing pointers
    data_label = _data_key.title() if _data_key else "none"
    exec_label = _exec_key.title() if _exec_key else "none"
    console.print(
        f"  [dim]Data:[/dim] [bold]{data_label}[/bold]"
        f"  [dim]Execution:[/dim] [bold]{exec_label}[/bold]"
    )
    console.print()


def set_data_broker(key: str) -> None:
    """Move the data pointer to this broker. Execution pointer is unchanged."""
    global _data_key
    key = _BROKER_NAMES.get(key.lower(), key.lower())
    if key not in _brokers:
        console.print(f"[dim]{key.title()} not connected — starting login…[/dim]")
        login(key)
    if key not in _brokers:
        console.print(f"[red]Could not connect {key.title()}.[/red]")
        return
    _data_key = key
    console.print(f"[green]✓ Data broker → {key.title()}[/green]")


def set_exec_broker(key: str) -> None:
    """Move the execution pointer to this broker. Data pointer is unchanged."""
    global _exec_key
    key = _BROKER_NAMES.get(key.lower(), key.lower())
    if key not in _brokers:
        console.print(f"[dim]{key.title()} not connected — starting login…[/dim]")
        login(key)
    if key not in _brokers:
        console.print(f"[red]Could not connect {key.title()}.[/red]")
        return
    _exec_key = key
    console.print(f"[green]✓ Execution broker → {key.title()}[/green]")


# ── Internal helpers ──────────────────────────────────────────


def _make_broker(choice: str) -> tuple[str, BrokerAPI]:
    """Instantiate the right broker. Returns (broker_key, broker_instance)."""
    key = _BROKER_NAMES.get(choice.lower())
    if key is None:
        console.print(f"[red]Unknown broker choice: {choice!r}[/red]")
        raise SystemExit(1)

    if key == "mock":
        broker = MockBrokerAPI()
        broker.complete_login()
        return key, broker

    elif key == "zerodha":
        from .zerodha import ZerodhaAPI

        api_key = get_credential("KITE_API_KEY", "Zerodha API Key", secret=False)
        api_secret = get_credential("KITE_API_SECRET", "Zerodha API Secret", secret=True)
        return key, ZerodhaAPI(api_key=api_key, api_secret=api_secret)

    elif key == "groww":
        from .groww import GrowwAPI

        client_id = get_credential("GROWW_CLIENT_ID", "Groww Client ID", secret=False)
        client_secret = get_credential("GROWW_CLIENT_SECRET", "Groww Client Secret", secret=True)
        redirect_uri = os.environ.get("GROWW_REDIRECT_URL", "http://localhost:8765/groww/callback")
        return key, GrowwAPI(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

    elif key == "angelone":
        from .angelone import AngelOneAPI

        api_key = get_credential("ANGEL_API_KEY", "Angel One API Key", secret=False)
        client_code = get_credential(
            "ANGEL_CLIENT_CODE", "Angel One Client Code (Login ID)", secret=False
        )
        password = get_credential("ANGEL_PASSWORD", "Angel One Trading Password", secret=True)
        totp_secret = get_credential(
            "ANGEL_TOTP_SECRET", "Angel One TOTP Secret", secret=True, required=False
        )
        return key, AngelOneAPI(
            api_key=api_key,
            client_code=client_code,
            password=password,
            totp_secret=totp_secret,
        )

    elif key == "upstox":
        from .upstox import UpstoxAPI

        api_key = get_credential("UPSTOX_API_KEY", "Upstox API Key", secret=False)
        api_secret = get_credential("UPSTOX_API_SECRET", "Upstox API Secret", secret=True)
        redirect_uri = os.environ.get(
            "UPSTOX_REDIRECT_URL", "http://localhost:8765/upstox/callback"
        )
        return key, UpstoxAPI(
            api_key=api_key,
            api_secret=api_secret,
            redirect_uri=redirect_uri,
        )

    else:  # fyers
        from .fyers import FyersAPI

        app_id = get_credential("FYERS_APP_ID", "Fyers App ID", secret=False)
        secret_key = get_credential("FYERS_SECRET_KEY", "Fyers Secret Key", secret=True)
        redirect_uri = os.environ.get("FYERS_REDIRECT_URL", "http://127.0.0.1:8765/fyers/callback")
        return key, FyersAPI(
            app_id=app_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
        )


def _is_sidecar_running(port: int) -> bool:
    """Check if the FastAPI sidecar is already running on this port."""
    import urllib.request

    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
        return r.status == 200
    except Exception:
        return False


def _poll_sidecar_auth(broker_key: str, port: int, timeout: int = 180) -> dict[str, str] | None:
    """
    Poll the sidecar's /api/status until the broker shows authenticated.
    Returns a sentinel dict {"_sidecar": "true"} on success, None on timeout.
    The caller uses this to know the sidecar handled the OAuth.
    """
    import json
    import time
    import urllib.request

    # Map session keys to status keys
    _STATUS_KEYS = {
        "fyers": "fyers",
        "zerodha": "zerodha",
        "groww": "groww",
        "angelone": "angel_one",
        "upstox": "upstox",
    }
    status_key = _STATUS_KEYS.get(broker_key, broker_key)
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            r = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=3)
            data = json.loads(r.read())
            broker_status = data.get(status_key, {})
            if broker_status.get("authenticated"):
                return {"_sidecar": "true"}
        except Exception:
            pass
        time.sleep(2)

    return None


def _oauth_local_server(
    port: int,
    path: str,
    *param_names: str,
    timeout: int = 180,
) -> dict[str, str] | None:
    """
    Bind a temporary HTTP server on 127.0.0.1:port, wait for ONE GET request
    to `path`, extract query params listed in `param_names`, then shut down.

    Returns a dict of {param: value} on success, or None if the port is
    already in use (fall back to manual paste) or the timeout is reached.

    The browser gets a "Login successful — close this tab" page.
    """
    import queue
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse

    result: queue.Queue[dict | None] = queue.Queue()
    _SUCCESS_HTML = (
        b"<!DOCTYPE html><html><head><meta charset=utf-8>"
        b"<style>body{font-family:sans-serif;text-align:center;padding:4em;color:#1a1a1a}"
        b"h2{color:#16a34a}</style></head><body>"
        b"<h2>&#10003; Login successful</h2>"
        b"<p>You can close this tab and return to the terminal.</p>"
        b"</body></html>"
    )

    _done = threading.Event()

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence access log
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == path:
                qs = parse_qs(parsed.query)
                values = {p: (qs.get(p) or [""])[0] for p in param_names}
                result.put(values)
                _done.set()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_SUCCESS_HTML)))
                self.end_headers()
                self.wfile.write(_SUCCESS_HTML)
            else:
                # Stray request (favicon, pre-flight, etc.) — respond and keep waiting
                self.send_response(204)
                self.end_headers()

    try:
        server = HTTPServer(("127.0.0.1", port), _Handler)
        server.timeout = 1  # handle_request poll interval
    except OSError:
        return None  # port busy → fall back to manual paste

    def _serve():
        try:
            # Loop until the correct callback path is hit or the caller gives up
            while not _done.is_set():
                server.handle_request()
        finally:
            server.server_close()

    threading.Thread(target=_serve, daemon=True).start()

    try:
        values = result.get(timeout=timeout)
        return values
    except queue.Empty:
        _done.set()  # stop the server loop
        return None


def _recreate_broker_from_token(key: str):
    """Re-create a broker instance from its saved token file (after sidecar OAuth)."""
    try:
        if key == "fyers":
            from brokers.fyers import FyersAPI, TOKEN_FILE

            if TOKEN_FILE.exists():
                b = FyersAPI(
                    os.environ.get("FYERS_APP_ID", ""),
                    os.environ.get("FYERS_SECRET_KEY", ""),
                )
                if b.is_authenticated():
                    return b
        elif key == "zerodha":
            from brokers.zerodha import ZerodhaAPI, TOKEN_FILE

            if TOKEN_FILE.exists():
                b = ZerodhaAPI(
                    os.environ.get("KITE_API_KEY", ""),
                    os.environ.get("KITE_API_SECRET", ""),
                )
                if b.is_authenticated():
                    return b
    except Exception:
        pass
    return None


def _do_auth(key: str, broker: BrokerAPI) -> BrokerAPI:
    """Run the auth flow for a broker. TOTP brokers auto-login; others use browser redirect.
    Returns the (possibly recreated) broker instance."""
    from urllib.parse import urlparse

    # Angel One: fully automated TOTP login — no browser redirect needed
    if key in _TOTP_BROKERS:
        console.print(f"\n[bold cyan]🔐 Logging in to {key.title()} via TOTP…[/bold cyan]")
        broker.complete_login()
        return broker

    login_url = broker.get_login_url()
    console.print(f"\n[bold cyan]🌐 Opening login page for {key.title()}…[/bold cyan]")
    console.print(f"   URL: [link={login_url}]{login_url}[/link]\n")

    # ── Per-broker OAuth config ───────────────────────────────────
    if key == "fyers":
        redirect = os.environ.get("FYERS_REDIRECT_URL", "http://127.0.0.1:8765/fyers/callback")
        _path = urlparse(redirect).path
        _port = urlparse(redirect).port or 8765
        _params = ("auth_code",)
    elif key == "zerodha":
        redirect = "http://localhost:8765/zerodha/callback"
        _path = "/zerodha/callback"
        _port = 8765
        _params = ("request_token",)
    elif key == "groww":
        redirect = os.environ.get("GROWW_REDIRECT_URL", "http://localhost:8765/groww/callback")
        _path = urlparse(redirect).path
        _port = urlparse(redirect).port or 8765
        _params = ("code",)
    else:  # upstox
        redirect = os.environ.get("UPSTOX_REDIRECT_URL", "http://localhost:8765/upstox/callback")
        _path = urlparse(redirect).path
        _port = urlparse(redirect).port or 8765
        _params = ("code",)

    # Start local callback listener BEFORE opening the browser so we never
    # miss the redirect even on very fast connections.
    # If the sidecar is already running on the same port, the local server
    # can't bind — use the sidecar's callback instead (poll /api/status).
    console.print("[dim]  Waiting for browser login (up to 3 minutes)…[/dim]")
    webbrowser.open(login_url)

    captured = _oauth_local_server(_port, _path, *_params, timeout=180)

    # If local server failed (port busy = sidecar running), poll the sidecar
    if captured is None and _is_sidecar_running(_port):
        console.print("[dim]  Sidecar detected — waiting for OAuth via sidecar…[/dim]")
        captured = _poll_sidecar_auth(key, _port, timeout=180)

    if captured and "_sidecar" in captured:
        # ── Sidecar handled OAuth — token file saved, re-init broker ──
        console.print("[green]  ✓ Broker authenticated via sidecar.[/green]")
        # Re-create the broker from the saved token file
        new_broker = _recreate_broker_from_token(key)
        if new_broker is None:
            console.print("[yellow]  Token file not found — try again.[/yellow]")
            return broker
        return new_broker
    elif captured:
        # ── Auto-captured ─────────────────────────────────────────
        console.print("[dim]  Auth code received automatically.[/dim]")
        if key == "fyers":
            broker.complete_login(auth_code=captured["auth_code"])
        elif key == "zerodha":
            broker.complete_login(request_token=captured["request_token"])
        else:  # groww / upstox
            broker.complete_login(auth_code=captured["code"])
    else:
        # ── Fallback: port busy or timed out — manual paste ───────
        console.print(
            "[yellow]  Could not auto-capture the code (port busy or timed out).[/yellow]\n"
            "[dim]  Copy it from your browser's address bar:[/dim]"
        )
        if key == "fyers":
            console.print(
                "[dim]  http://127.0.0.1:8765/fyers/callback?[bold]auth_code=XXXXXX[/bold][/dim]\n"
            )
            code = Prompt.ask("[bold]Paste the [cyan]auth_code[/cyan] here[/bold]")
            broker.complete_login(auth_code=code)
        elif key == "zerodha":
            console.print(
                "[dim]  http://localhost:8765/...?[bold]request_token=XXXXXX[/bold]&status=success[/dim]\n"
            )
            token = Prompt.ask("[bold]Paste the [cyan]request_token[/cyan] here[/bold]")
            broker.complete_login(request_token=token)
        else:
            console.print(f"[dim]  {redirect}?[bold]code=XXXXXX[/bold][/dim]\n")
            code = Prompt.ask("[bold]Paste the [cyan]auth_code[/cyan] here[/bold]")
            broker.complete_login(auth_code=code)

    return broker


def _start_websocket(broker: BrokerAPI) -> None:
    """Start WebSocket for real-time quotes (Fyers only)."""
    try:
        from market.websocket import ws_manager

        # Access Fyers internal token and app_id
        token = getattr(broker, "_access_token", "")
        app_id = getattr(broker, "_app_id", "")
        if token and app_id:
            ws_manager.start(access_token=token, app_id=app_id)
    except Exception:
        pass  # Status shown in REPL toolbar


def _print_welcome(broker: BrokerAPI, role: str = "primary") -> None:
    """Print a styled welcome panel after successful login."""
    profile = broker.get_profile()
    try:
        funds = broker.get_funds()
    except Exception:
        funds = None

    lines = Text()
    lines.append("  Name    : ", style="dim")
    lines.append(f"{profile.name}\n", style="bold white")
    lines.append("  Broker  : ", style="dim")
    lines.append(f"{profile.broker}\n", style="bold cyan")
    lines.append("  Role    : ", style="dim")
    lines.append(f"{role.title()}\n", style="bold yellow" if role != "primary" else "bold green")
    if funds:
        lines.append("  Cash    : ", style="dim")
        lines.append(f"₹{funds.available_cash:,.2f}\n", style="bold green")
        lines.append("  Margin  : ", style="dim")
        lines.append(f"₹{funds.used_margin:,.2f} used", style="yellow")
    else:
        lines.append("  Cash    : ", style="dim")
        lines.append("(loading...)", style="dim yellow")

    title = (
        "[bold green]✅  LOGIN SUCCESSFUL[/bold green]"
        if role == "primary"
        else "[bold yellow]✅  BROKER CONNECTED[/bold yellow]"
    )
    console.print(Panel(lines, title=title, border_style="green", padding=(0, 2)))


# ── Public login functions ────────────────────────────────────


def login(choice: Optional[str] = None) -> BrokerAPI:
    """
    Interactive primary broker login.

    Sets the primary broker (used by get_broker()) and stores it in the
    multi-broker registry. If a broker is already registered under the same
    key it will be replaced.

    Args:
        choice: "0"/"demo", "1"/"zerodha", "2"/"groww", "3"/"angelone",
                "4"/"upstox", "5"/"fyers". If None, the user is prompted.

    Returns:
        Authenticated BrokerAPI instance.
    """
    global _brokers, _primary_key, _data_key, _exec_key

    if choice is None:
        console.print("\n[bold]Choose your primary broker:[/bold]")
        for num, name, desc in _BROKER_MENU:
            console.print(f"  [cyan][{num}][/cyan] {name:12s}  [dim]{desc}[/dim]")
        choice = Prompt.ask(
            "\n[bold]>[/bold]",
            choices=[num for num, _, _ in _BROKER_MENU],
        )

    key, broker = _make_broker(choice)

    if key == "mock":
        _brokers[key] = broker
        _primary_key = key
        _data_key = key  # login = data broker
        _exec_key = key  # also handles execution until connect() is called
        _print_welcome(broker, role="primary")
        return broker

    # Try to resume existing session
    if broker.is_authenticated():
        console.print("[dim]Resuming existing session…[/dim]")
        # Don't verify with API call — trust token age (instant)
        # If token is actually invalid, first command will trigger re-login
    else:
        broker = _do_auth(key, broker)

    _brokers[key] = broker
    _primary_key = key
    _data_key = key  # login = data broker
    _exec_key = key  # also handles execution until connect() is called

    # Skip _print_welcome on resume (it makes slow API calls)
    # Just show broker name
    if broker.is_authenticated():
        console.print(f"[green]  Connected: {key.title()}[/green]")
    else:
        _print_welcome(broker, role="primary")

    # Auto-start WebSocket in background (non-blocking)
    if key == "fyers":
        import threading

        threading.Thread(target=_start_websocket, args=(broker,), daemon=True).start()

    if len(_brokers) > 1:
        console.print(
            f"[dim]  {len(_brokers)} brokers now connected. "
            f"Type [bold]brokers[/bold] to see all.[/dim]"
        )
    return broker


def connect_broker(choice: Optional[str] = None) -> BrokerAPI:
    """
    Connect an additional broker without replacing the primary.

    Useful for viewing a combined Zerodha + Groww portfolio.
    The primary broker (used for order placement) does not change.

    Args:
        choice: "1"/"zerodha" or "2"/"groww". Prompted if None.

    Returns:
        The newly connected BrokerAPI instance.
    """
    global _brokers, _exec_key

    if not _brokers:
        console.print("[yellow]No primary broker yet. Use 'login' first.[/yellow]")
        return login(choice)

    if choice is None:
        console.print("\n[bold]Connect an additional broker:[/bold]")
        for num, name, desc in _BROKER_MENU:
            key = _BROKER_NAMES[num]
            already = " [dim](already connected)[/dim]" if key in _brokers else ""
            console.print(f"  [cyan][{num}][/cyan] {name:12s}  [dim]{desc}[/dim]{already}")
        choice = Prompt.ask(
            "\n[bold]>[/bold]",
            choices=[num for num, _, _ in _BROKER_MENU],
        )

    key, broker = _make_broker(choice)

    if key in _brokers:
        console.print(
            f"[yellow]{key.title()} is already connected. "
            f"Reconnecting with a fresh session…[/yellow]"
        )

    if key != "mock":
        if broker.is_authenticated():
            console.print(f"[dim]Resuming existing {key.title()} session…[/dim]")
        else:
            _do_auth(key, broker)

    _brokers[key] = broker
    _exec_key = key  # connect = execution broker; data pointer unchanged
    _print_welcome(broker, role="connected")

    console.print(
        f"\n[green]✓  {len(_brokers)} broker(s) now active.[/green]  "
        f"Primary: [bold]{_primary_key.title()}[/bold]  |  "
        f"Type [bold]brokers[/bold] to see all.\n"
    )
    return broker


def disconnect_broker(choice: Optional[str] = None) -> None:
    """Disconnect a secondary broker without logging out of the primary."""
    global _brokers

    if not _brokers:
        console.print("[dim]No brokers connected.[/dim]")
        return

    secondary = {k: v for k, v in _brokers.items() if k != _primary_key}
    if not secondary:
        console.print(
            "[dim]Only the primary broker is connected. Use 'logout' to disconnect it.[/dim]"
        )
        return

    if choice is None:
        console.print("\n[bold]Disconnect which broker?[/bold]")
        for i, key in enumerate(secondary.keys(), 1):
            console.print(f"  [{i}] {key.title()}")
        idx = Prompt.ask("[bold]>[/bold]")
        try:
            key = list(secondary.keys())[int(idx) - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice.[/red]")
            return
    else:
        key = _BROKER_NAMES.get(choice.lower(), choice.lower())

    if key == _primary_key:
        console.print("[red]Cannot disconnect the primary broker. Use 'logout' instead.[/red]")
        return
    if key not in _brokers:
        console.print(f"[red]{key.title()} is not connected.[/red]")
        return

    try:
        _brokers[key].logout()
    except Exception:
        pass
    del _brokers[key]
    console.print(f"[yellow]{key.title()} disconnected.[/yellow]")


def logout() -> None:
    """Logout ALL connected brokers and clear all sessions."""
    global _brokers, _primary_key
    for key, broker in list(_brokers.items()):
        try:
            broker.logout()
        except Exception:
            pass
    _brokers = {}
    _primary_key = ""
    console.print("[yellow]All brokers logged out.[/yellow]")
