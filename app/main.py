"""
app/main.py
───────────
Entry point for the trading platform.

Run with:
    python -m app.main
    # or after pip install -e .:
    trade
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Load .env before anything else ───────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Pull keychain credentials into env (after .env so .env wins) ─
from config.credentials import load_all as _load_keychain
_load_keychain()

from rich.console import Console
from rich.text    import Text

from brokers.session import login, get_broker

console = Console()

BANNER = """
[bold cyan]
 ████████╗██████╗  █████╗ ██████╗ ███████╗
    ██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
    ██║   ██████╔╝███████║██║  ██║█████╗
    ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝
    ██║   ██║  ██║██║  ██║██████╔╝███████╗
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
[/bold cyan]
[dim]  Indian Stock & Options Platform  |  Powered by Claude[/dim]
"""


def main() -> None:
    console.print(BANNER)

    # ── Check for flags ───────────────────────────────────────
    use_tui = "--tui" in sys.argv
    no_broker = "--no-broker" in sys.argv

    # ── Login ─────────────────────────────────────────────────
    if no_broker:
        # Skip broker selection UI — auto-login to Demo/Mock broker
        # This registers it in the session registry so get_broker() works
        console.print("[dim]  Running without broker (--no-broker). Using yfinance for market data.[/dim]")
        console.print("[dim]  To connect a real broker later, run 'login' in the REPL.[/dim]\n")
        broker = login("0")  # "0" = Demo/Mock broker
    else:
        try:
            broker = login()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Login cancelled.[/yellow]")
            sys.exit(0)

    if use_tui:
        # Launch Textual TUI
        from ui.app import run_tui
        run_tui()
    else:
        # Drop into REPL (default)
        from app.repl import run_repl
        run_repl(broker)


if __name__ == "__main__":
    exit_code = 0
    try:
        main()
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        # Give daemon threads 2 seconds to finish, then force exit
        # if they don't (WebSocket SDK can hold non-daemon threads)
        import threading
        non_daemon = [t for t in threading.enumerate()
                      if t.is_alive() and not t.daemon and t != threading.main_thread()]
        if non_daemon:
            # Non-daemon threads exist — force kill after brief wait
            import signal
            signal.alarm(2) if hasattr(signal, 'alarm') else None
            os._exit(exit_code)
        else:
            sys.exit(exit_code)
