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

    # ── Check for --tui flag ──────────────────────────────────
    use_tui = "--tui" in sys.argv

    # ── Login ─────────────────────────────────────────────────
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
    main()
