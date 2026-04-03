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
        # Register a mock broker with passthrough_market_data=True
        # so market data methods raise → fallback chain goes to yfinance
        # Account methods (funds, holdings) still return demo data
        console.print("[dim]  Running without broker (--no-broker). Using yfinance for market data.[/dim]")
        console.print("[dim]  To connect a real broker later, run 'login' in the REPL.[/dim]\n")
        from brokers.mock import MockBrokerAPI
        from brokers.session import register_broker
        mock = MockBrokerAPI(passthrough_market_data=True)
        mock.complete_login()
        register_broker("mock", mock, primary=True)
        broker = mock
    else:
        try:
            broker = login()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Login cancelled.[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Login failed: {e}[/red]")
            console.print("[yellow]Dropping into REPL with mock broker so you can fix credentials.[/yellow]")
            console.print("[dim]  Run 'credentials list' to see saved credentials[/dim]")
            console.print("[dim]  Run 'credentials clear' to wipe all and start fresh[/dim]")
            console.print("[dim]  Run 'login' to try again[/dim]\n")
            from brokers.mock import MockBrokerAPI
            from brokers.session import register_broker
            mock = MockBrokerAPI(passthrough_market_data=True)
            mock.complete_login()
            register_broker("mock", mock, primary=True)
            broker = mock

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
            # Non-daemon threads exist (e.g. WebSocket SDK) — wait up to
            # 2 seconds for them to finish, then force exit.
            for t in non_daemon:
                t.join(timeout=2)
            # If any are still alive after the wait, force kill
            still_alive = [t for t in non_daemon if t.is_alive()]
            if still_alive:
                os._exit(exit_code)
            else:
                sys.exit(exit_code)
        else:
            sys.exit(exit_code)
