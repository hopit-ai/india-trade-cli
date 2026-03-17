"""
ui/app.py
─────────
Textual TUI — split-panel terminal UI.

Layout (Claude Code-inspired):
  ┌──────────────────────────────────┬────────────────────┐
  │                                  │  Live Indices      │
  │   Chat / Guidance Panel          │  (NIFTY, VIX...)   │
  │   (scrollable conversation       ├────────────────────┤
  │    with the AI agent)            │  Portfolio + Greeks│
  │                                  ├────────────────────┤
  │                                  │  Risk Meter        │
  ├──────────────────────────────────┴────────────────────┤
  │  Input ❯                                              │
  └────────────────────────────────────────────────────────┘

Keyboard shortcuts:
  Ctrl+B    Toggle morning brief
  Ctrl+O    Load options chain (prompts for symbol)
  Ctrl+R    Refresh all data panels
  Ctrl+P    Toggle paper / live mode display
  Ctrl+Q    Quit
  F1        Show help

Launch:
  python -m ui.app
  or from the REPL: `tui` command (added to repl.py)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing   import ClassVar

import pytz
from textual          import on, work
from textual.app      import App, ComposeResult
from textual.binding  import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets  import (
    Header, Footer, Input, Static, Label,
    DataTable, RichLog, TabbedContent, TabPane,
)
from textual.reactive import reactive

from ui.widgets.portfolio    import PortfolioWidget
from ui.widgets.risk_meter   import RiskMeterWidget
from ui.widgets.options_chain import OptionsChainWidget

IST = pytz.timezone("Asia/Kolkata")

REFRESH_INTERVAL = 30   # seconds between auto-refresh of market panels


class MarketTickerWidget(Static):
    """
    Top-right widget: live index levels + VIX.
    Auto-refreshes every REFRESH_INTERVAL seconds.
    """

    DEFAULT_CSS = """
    MarketTickerWidget {
        height: auto;
        border: round $primary;
        padding: 0 1;
    }
    MarketTickerWidget Label {
        color: $primary;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Market")
        yield Static(id="ticker-body", markup=True)

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(REFRESH_INTERVAL, self.refresh_data)

    def refresh_data(self) -> None:
        try:
            from market.indices import get_market_snapshot
            snap = get_market_snapshot()
            now  = datetime.now(IST).strftime("%H:%M")

            def _row(name, val, chg):
                c = "green" if chg >= 0 else "red"
                s = "+" if chg >= 0 else ""
                return f"{name:<12} [bold]{val:>8,.0f}[/bold]  [{c}]{s}{chg:.2f}%[/{c}]"

            lines = [f"[dim]{now} IST[/dim]"]
            if snap.nifty:
                lines.append(_row("NIFTY 50", snap.nifty, snap.nifty_chg))
            if snap.banknifty:
                lines.append(_row("BANKNIFTY", snap.banknifty, snap.banknifty_chg))
            if snap.sensex:
                lines.append(_row("SENSEX", snap.sensex, snap.sensex_chg))
            if snap.india_vix:
                vc = "red" if snap.india_vix > 20 else "yellow" if snap.india_vix > 15 else "green"
                lines.append(f"India VIX    [{vc}]{snap.india_vix:>8.2f}[/{vc}]")

            posture_color = {"BULLISH": "green", "BEARISH": "red", "VOLATILE": "yellow"}.get(
                snap.posture, "white"
            )
            lines.append(f"\n[{posture_color}]{snap.posture}[/{posture_color}]")

            self.query_one("#ticker-body", Static).update("\n".join(lines))
        except Exception:
            self.query_one("#ticker-body", Static).update("[dim]Fetching...[/dim]")


class ChatPanel(RichLog):
    """
    Left panel: scrollable AI conversation output.
    Written to by the agent as it streams responses.
    """

    DEFAULT_CSS = """
    ChatPanel {
        border: round $surface;
        padding: 0 1;
        height: 1fr;
    }
    """


class TradingTUI(App):
    """
    The main Textual TUI application.

    All trading analysis flows through the chat panel — the right panels
    show live data that auto-refreshes, while the left panel is where
    the AI agent's guidance appears.
    """

    TITLE   = "TradeAI — Guided Trading Terminal"
    SUB_TITLE = f"Paper Mode | {datetime.now(IST).strftime('%d %b %Y')}"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-row {
        layout: horizontal;
        height: 1fr;
    }

    #left-col {
        width: 2fr;
        layout: vertical;
    }

    #right-col {
        width: 1fr;
        layout: vertical;
    }

    #chat-panel {
        height: 1fr;
        border: round $surface;
        padding: 0 1;
    }

    #input-bar {
        height: 3;
        border: round $accent;
        padding: 0 1;
    }

    #input-field {
        border: none;
        height: 1;
    }

    MarketTickerWidget {
        height: auto;
        max-height: 12;
    }

    PortfolioWidget {
        height: 1fr;
    }

    RiskMeterWidget {
        height: auto;
        max-height: 9;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+b",  "morning_brief",   "Brief",    show=True),
        Binding("ctrl+o",  "options_chain",   "Options",  show=True),
        Binding("ctrl+r",  "refresh_all",     "Refresh",  show=True),
        Binding("ctrl+q",  "quit",            "Quit",     show=True),
        Binding("f1",      "show_help",       "Help",     show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-row"):
            # Left: chat + input
            with Vertical(id="left-col"):
                yield ChatPanel(id="chat-panel", highlight=True, markup=True)
                with Static(id="input-bar"):
                    yield Input(
                        placeholder="Ask the agent anything, or type a command...",
                        id="input-field",
                    )

            # Right: live data panels
            with Vertical(id="right-col"):
                yield MarketTickerWidget(id="market-ticker")
                yield PortfolioWidget(id="portfolio-widget")
                yield RiskMeterWidget(id="risk-widget")

        yield Footer()

    def on_mount(self) -> None:
        """Show welcome message and initialise the agent."""
        chat = self.query_one("#chat-panel", ChatPanel)
        mode = os.environ.get("TRADING_MODE", "PAPER")

        chat.write(
            f"[bold cyan]🚀  TradeAI — Guided Trading Terminal[/bold cyan]\n"
            f"[dim]Mode: [bold]{mode}[/bold]   "
            f"Date: {datetime.now(IST).strftime('%d %b %Y  %I:%M %p IST')}[/dim]\n"
        )
        chat.write(
            "Type your question or command below.\n"
            "[dim]Examples:[/dim]\n"
            "  [cyan]Analyse RELIANCE for me[/cyan]\n"
            "  [cyan]Give me a morning brief[/cyan]\n"
            "  [cyan]What is a Bull Call Spread?[/cyan]\n"
            "  [cyan]Show my portfolio Greeks[/cyan]\n"
        )

        # Pre-init the agent in background (avoids first-message delay)
        self.init_agent()

    @work(thread=True)
    def init_agent(self) -> None:
        try:
            from agent.core import get_agent
            get_agent()
        except Exception:
            pass

    # ── Input handling ────────────────────────────────────────

    @on(Input.Submitted, "#input-field")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.clear()
        self._handle_command(text)

    @work(thread=True)
    def _handle_command(self, text: str) -> None:
        """
        Route the input to either a direct command or the AI agent.
        Runs in a background thread so the UI stays responsive.
        """
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.write(f"\n[bold cyan]You ❯[/bold cyan] {text}\n")

        # Direct commands that don't need the AI
        lower = text.lower()
        if lower in ("refresh", "r"):
            self.call_from_thread(self.action_refresh_all)
            return
        if lower in ("help", "?"):
            self.call_from_thread(self.action_show_help)
            return

        # Route everything else to the agent
        try:
            from agent.core import get_agent

            # Redirect agent output to our chat panel
            import rich.console as _rc
            orig_console = _rc.Console

            class TUIConsole(_rc.Console):
                """Intercept rich prints and write to chat panel."""
                def __init__(self_inner, *args, **kwargs):
                    super().__init__(*args, **kwargs)

                def print(self_inner, *args, **kwargs):
                    # Also write to chat panel
                    content = " ".join(str(a) for a in args)
                    self.call_from_thread(chat.write, content)
                    super().print(*args, **kwargs)

            agent = get_agent()
            agent.chat(text)

            # Refresh side panels after agent response
            self.call_from_thread(self._refresh_side_panels)

        except Exception as e:
            chat.write(f"[red]Error: {e}[/red]\n")

    def _refresh_side_panels(self) -> None:
        try:
            self.query_one("#portfolio-widget", PortfolioWidget).refresh_data()
            self.query_one("#risk-widget", RiskMeterWidget).refresh_data()
        except Exception:
            pass

    # ── Actions (keyboard shortcuts) ──────────────────────────

    def action_morning_brief(self) -> None:
        self._handle_command("Give me a morning market brief")

    def action_options_chain(self) -> None:
        """Focus the options chain symbol input."""
        try:
            inp = self.query_one("#chain-symbol", Input)
            inp.focus()
        except Exception:
            self._handle_command("Show me the NIFTY options chain")

    def action_refresh_all(self) -> None:
        try:
            self.query_one("#market-ticker",    MarketTickerWidget).refresh_data()
            self.query_one("#portfolio-widget", PortfolioWidget).refresh_data()
            self.query_one("#risk-widget",      RiskMeterWidget).refresh_data()
        except Exception:
            pass

    def action_show_help(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.write("""
[bold cyan]Keyboard Shortcuts:[/bold cyan]
  Ctrl+B  — Morning market brief
  Ctrl+O  — Focus options chain input
  Ctrl+R  — Refresh all data panels
  Ctrl+Q  — Quit
  F1      — This help

[bold cyan]What you can ask:[/bold cyan]
  • Analyse RELIANCE / NIFTY / any NSE symbol
  • Show me the options chain for BANKNIFTY
  • What is the market sentiment today?
  • Calculate payoff for a Bull Call Spread
  • Should I buy or sell INFY right now?
  • Explain Iron Condor strategy
  • What are my portfolio Greeks?
""")


def run_tui() -> None:
    """Launch the Textual TUI."""
    app = TradingTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
