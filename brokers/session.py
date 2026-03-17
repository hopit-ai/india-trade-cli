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
from rich.panel   import Panel
from rich.prompt  import Prompt
from rich.table   import Table
from rich.text    import Text

from .base    import BrokerAPI
from .zerodha import ZerodhaAPI
from .groww   import GrowwAPI
from .mock    import MockBrokerAPI

from config.credentials import get_credential

console = Console()

# ── Module state ──────────────────────────────────────────────
# All connected brokers, keyed by broker name (lowercase)
_brokers: dict[str, BrokerAPI] = {}

# The "primary" broker — used by get_broker() for single-broker commands
_primary_key: str = ""

# Human-readable names for display
_BROKER_NAMES = {
    "0": "mock", "demo": "mock", "mock": "mock",
    "1": "zerodha", "zerodha": "zerodha",
    "2": "groww",   "groww":   "groww",
}

_BROKER_LABELS = {
    "mock":    "[dim]Mock / Demo[/dim]",
    "zerodha": "[cyan]Zerodha (Kite)[/cyan]",
    "groww":   "[green]Groww[/green]",
}


# ── Public accessors ──────────────────────────────────────────

def get_broker() -> BrokerAPI:
    """Return the primary broker. Raises if login() has not been called."""
    if not _primary_key or _primary_key not in _brokers:
        raise RuntimeError(
            "No active broker session. Run login() first or start the platform with `trade`."
        )
    return _brokers[_primary_key]


def get_all_brokers() -> dict[str, BrokerAPI]:
    """Return all connected broker instances, keyed by broker name."""
    return dict(_brokers)


def is_multi_broker() -> bool:
    """True if more than one broker is currently connected."""
    return len(_brokers) > 1


def list_connected_brokers() -> None:
    """Pretty-print a table of all connected brokers."""
    if not _brokers:
        console.print("[dim]No brokers connected.[/dim]")
        return

    t = Table(title="Connected Brokers", show_header=True, header_style="bold cyan")
    t.add_column("Broker",  style="bold")
    t.add_column("Role",    style="dim")
    t.add_column("Account", style="white")
    t.add_column("Cash",    justify="right")

    for key, broker in _brokers.items():
        try:
            profile = broker.get_profile()
            funds   = broker.get_funds()
            role    = "[bold green]Primary[/bold green]" if key == _primary_key else "Connected"
            t.add_row(
                _BROKER_LABELS.get(key, key.title()),
                role,
                f"{profile.name} ({profile.user_id})",
                f"[green]₹{funds.available_cash:,.0f}[/green]",
            )
        except Exception as e:
            t.add_row(
                _BROKER_LABELS.get(key, key.title()),
                "[red]Error[/red]",
                str(e)[:40],
                "—",
            )

    console.print()
    console.print(t)
    console.print()


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
        api_key    = get_credential("KITE_API_KEY",    "Zerodha API Key",    secret=False)
        api_secret = get_credential("KITE_API_SECRET", "Zerodha API Secret", secret=True)
        return key, ZerodhaAPI(api_key=api_key, api_secret=api_secret)

    else:  # groww
        client_id     = get_credential("GROWW_CLIENT_ID",     "Groww Client ID",     secret=False)
        client_secret = get_credential("GROWW_CLIENT_SECRET",  "Groww Client Secret", secret=True)
        redirect_uri  = os.environ.get(
            "GROWW_REDIRECT_URL", "http://localhost:8765/groww/callback"
        )
        return key, GrowwAPI(
            client_id     = client_id,
            client_secret = client_secret,
            redirect_uri  = redirect_uri,
        )


def _do_auth(key: str, broker: BrokerAPI) -> None:
    """Run the browser-based auth flow for a broker that needs fresh login."""
    login_url = broker.get_login_url()
    console.print(f"\n[bold cyan]🌐 Opening login page for {key.title()}…[/bold cyan]")
    console.print(f"   URL: [link={login_url}]{login_url}[/link]\n")
    webbrowser.open(login_url)

    if key == "zerodha":
        console.print(
            "[dim]After login, the browser will redirect to a URL like:[/dim]\n"
            "[dim]  http://localhost:8765/...?[bold]request_token=XXXXXX[/bold]&status=success[/dim]\n"
        )
        token = Prompt.ask("[bold]Paste the [cyan]request_token[/cyan] here[/bold]")
        broker.complete_login(request_token=token)

    else:  # groww
        console.print(
            "[dim]After login, the browser will redirect to a URL like:[/dim]\n"
            "[dim]  http://localhost:8765/groww/callback?[bold]code=XXXXXX[/bold][/dim]\n"
        )
        code = Prompt.ask("[bold]Paste the [cyan]auth_code[/cyan] here[/bold]")
        broker.complete_login(auth_code=code)


def _print_welcome(broker: BrokerAPI, role: str = "primary") -> None:
    """Print a styled welcome panel after successful login."""
    profile = broker.get_profile()
    funds   = broker.get_funds()

    lines = Text()
    lines.append(f"  Name    : ", style="dim")
    lines.append(f"{profile.name}\n", style="bold white")
    lines.append(f"  Broker  : ", style="dim")
    lines.append(f"{profile.broker}\n", style="bold cyan")
    lines.append(f"  Role    : ", style="dim")
    lines.append(f"{role.title()}\n", style="bold yellow" if role != "primary" else "bold green")
    lines.append(f"  Cash    : ", style="dim")
    lines.append(f"₹{funds.available_cash:,.2f}\n", style="bold green")
    lines.append(f"  Margin  : ", style="dim")
    lines.append(f"₹{funds.used_margin:,.2f} used", style="yellow")

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
        choice: "0"/"demo", "1"/"zerodha", "2"/"groww".
                If None, the user is prompted to choose.

    Returns:
        Authenticated BrokerAPI instance.
    """
    global _brokers, _primary_key

    if choice is None:
        console.print("\n[bold]Choose your primary broker:[/bold]")
        console.print("  [cyan][0][/cyan] Demo     (mock data, no credentials needed)")
        console.print("  [cyan][1][/cyan] Zerodha  (Kite Connect)")
        console.print("  [cyan][2][/cyan] Groww")
        choice = Prompt.ask("\n[bold]>[/bold]", choices=["0", "1", "2"])

    key, broker = _make_broker(choice)

    if key == "mock":
        _brokers[key]  = broker
        _primary_key   = key
        _print_welcome(broker, role="primary")
        return broker

    # Try to resume existing session
    if broker.is_authenticated():
        console.print("[dim]Resuming existing session…[/dim]")
    else:
        _do_auth(key, broker)

    _brokers[key] = broker
    _primary_key  = key
    _print_welcome(broker, role="primary")

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
    global _brokers

    if not _brokers:
        console.print("[yellow]No primary broker yet. Use 'login' first.[/yellow]")
        return login(choice)

    if choice is None:
        console.print("\n[bold]Connect an additional broker:[/bold]")
        for opt, label in [("0", "Demo (mock)"), ("1", "Zerodha"), ("2", "Groww")]:
            key = _BROKER_NAMES[opt]
            already = " [dim](already connected)[/dim]" if key in _brokers else ""
            console.print(f"  [cyan][{opt}][/cyan] {label}{already}")
        choice = Prompt.ask("\n[bold]>[/bold]", choices=["0", "1", "2"])

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
        console.print("[dim]Only the primary broker is connected. Use 'logout' to disconnect it.[/dim]")
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
