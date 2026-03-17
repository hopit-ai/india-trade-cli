"""
app/repl.py
────────────
Command REPL — the main interactive loop.
Each command is a thin dispatcher; the real logic lives in
app/commands/, engine/, analysis/, etc.

Available commands:
  login            Log in (primary broker)
  connect          Connect an additional broker (e.g. add Groww after Zerodha)
  disconnect       Remove a secondary broker connection
  brokers          List all connected brokers with cash summary
  logout           Log out of all brokers
  profile          Show account profile (primary broker)
  funds            Show available funds / margin (primary broker)
  holdings         Holdings from primary broker
  positions        Open positions from primary broker
  portfolio        Unified view — all connected brokers, Greeks, risk meter
  orders           Today's orders (primary broker)
  morning-brief    Daily AI market briefing
  analyze <SYM>    Full analysis: fundamental + technical + options
  trade            Interactive strategy builder
  paper            Show paper-trading mode status
  ai <message>     Chat directly with the AI agent
  provider         Show / switch AI provider
  tui              Launch split-panel Textual TUI
  quit / exit      Exit the platform
"""

from __future__ import annotations

from prompt_toolkit              import PromptSession
from prompt_toolkit.completion   import WordCompleter
from prompt_toolkit.history      import FileHistory
from prompt_toolkit.styles       import Style
from rich.console                import Console
from rich.table                  import Table
from rich.text                   import Text

from brokers.base    import BrokerAPI
from brokers.session import (
    login as do_login,
    logout as do_logout,
    connect_broker,
    disconnect_broker,
    list_connected_brokers,
    get_broker,
    is_multi_broker,
)
from agent.core import get_agent, ALL_PROVIDERS

console = Console()

HISTORY_FILE = "~/.trading_platform/.repl_history"

COMMANDS = [
    "login", "connect", "disconnect", "brokers",
    "logout", "profile", "funds",
    "holdings", "positions", "orders",
    "morning-brief", "analyze", "trade",
    "portfolio", "paper",
    "ai", "provider", "tui",
    "help", "quit", "exit",
]

STYLE = Style.from_dict({
    "prompt": "bold ansicyan",
})


# ── Command handlers ──────────────────────────────────────────

def cmd_profile(broker: BrokerAPI) -> None:
    p = broker.get_profile()
    console.print(f"\n  [bold]Name  :[/bold] {p.name}")
    console.print(f"  [bold]ID    :[/bold] {p.user_id}")
    console.print(f"  [bold]Email :[/bold] {p.email}")
    console.print(f"  [bold]Broker:[/bold] [cyan]{p.broker}[/cyan]\n")


def cmd_funds(broker: BrokerAPI) -> None:
    f = broker.get_funds()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold")
    table.add_row("Available Cash", f"[green]₹{f.available_cash:,.2f}[/green]")
    table.add_row("Used Margin",    f"[yellow]₹{f.used_margin:,.2f}[/yellow]")
    table.add_row("Total Balance",  f"[white]₹{f.total_balance:,.2f}[/white]")
    console.print()
    console.print(table)
    console.print()


def cmd_holdings(broker: BrokerAPI) -> None:
    holdings = broker.get_holdings()
    if not holdings:
        console.print("[dim]No holdings found.[/dim]")
        return

    table = Table(title="Holdings", show_header=True, header_style="bold cyan")
    table.add_column("Symbol",   style="bold white")
    table.add_column("Qty",      justify="right")
    table.add_column("Avg",      justify="right")
    table.add_column("LTP",      justify="right")
    table.add_column("P&L",      justify="right")
    table.add_column("P&L %",    justify="right")

    for h in holdings:
        pnl_style = "green" if h.pnl >= 0 else "red"
        table.add_row(
            h.symbol,
            str(h.quantity),
            f"₹{h.avg_price:,.2f}",
            f"₹{h.last_price:,.2f}",
            f"[{pnl_style}]₹{h.pnl:,.2f}[/{pnl_style}]",
            f"[{pnl_style}]{h.pnl_pct:+.2f}%[/{pnl_style}]",
        )

    console.print()
    console.print(table)
    total_pnl = sum(h.pnl for h in holdings)
    pnl_style = "green" if total_pnl >= 0 else "red"
    console.print(f"\n  Net P&L: [{pnl_style}]₹{total_pnl:,.2f}[/{pnl_style}]\n")


def cmd_positions(broker: BrokerAPI) -> None:
    positions = broker.get_positions()
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        return

    table = Table(title="Open Positions", show_header=True, header_style="bold cyan")
    table.add_column("Symbol",   style="bold white")
    table.add_column("Product",  style="dim")
    table.add_column("Qty",      justify="right")
    table.add_column("Avg",      justify="right")
    table.add_column("LTP",      justify="right")
    table.add_column("P&L",      justify="right")

    for p in positions:
        pnl_style = "green" if p.pnl >= 0 else "red"
        qty_str   = f"+{p.quantity}" if p.quantity > 0 else str(p.quantity)
        table.add_row(
            p.symbol,
            p.product,
            qty_str,
            f"₹{p.avg_price:,.2f}",
            f"₹{p.last_price:,.2f}",
            f"[{pnl_style}]₹{p.pnl:,.2f}[/{pnl_style}]",
        )

    console.print()
    console.print(table)
    total_pnl = sum(p.pnl for p in positions)
    pnl_style = "green" if total_pnl >= 0 else "red"
    console.print(f"\n  Net P&L: [{pnl_style}]₹{total_pnl:,.2f}[/{pnl_style}]\n")


def cmd_orders(broker: BrokerAPI) -> None:
    orders = broker.get_orders()
    if not orders:
        console.print("[dim]No orders today.[/dim]")
        return

    table = Table(title="Today's Orders", show_header=True, header_style="bold cyan")
    table.add_column("Order ID", style="dim")
    table.add_column("Symbol",   style="bold white")
    table.add_column("Type")
    table.add_column("Qty",      justify="right")
    table.add_column("Price",    justify="right")
    table.add_column("Status")

    status_colors = {
        "COMPLETE": "green", "OPEN": "cyan",
        "REJECTED": "red",   "CANCELLED": "yellow",
    }
    for o in orders:
        color = status_colors.get(o.status.upper(), "white")
        price = f"₹{o.average_price or o.price or 0:,.2f}"
        table.add_row(
            o.order_id[:12] + "…",
            o.symbol,
            f"{'🟢' if o.transaction_type == 'BUY' else '🔴'} {o.transaction_type}",
            str(o.quantity),
            price,
            f"[{color}]{o.status}[/{color}]",
        )

    console.print()
    console.print(table)
    console.print()


def _cmd_portfolio(summary) -> None:
    """
    Display full portfolio: holdings + positions + Greeks + risk meter.
    When summary.multi_broker is True, shows a Broker column in every table
    and a combined funds header.
    """
    from rich import box as rbox

    multi = summary.multi_broker
    brokers_label = " + ".join(b.title() for b in summary.brokers) if summary.brokers else ""

    # ── Header ───────────────────────────────────────────────
    if multi:
        console.print(
            f"\n[bold cyan]Combined Portfolio:[/bold cyan]  "
            f"[dim]{brokers_label}[/dim]  |  "
            f"Total Value: [bold]₹{summary.total_value:,.0f}[/bold]  "
            f"Net P&L: {'[green]' if summary.total_pnl >= 0 else '[red]'}"
            f"₹{summary.total_pnl:,.0f}"
            f"{'[/green]' if summary.total_pnl >= 0 else '[/red]'}"
        )

    # ── Holdings table ────────────────────────────────────────
    if summary.holdings:
        title = "Holdings (CNC)" + (f" — {brokers_label}" if multi else "")
        ht = Table(title=title, show_header=True, header_style="bold cyan", box=rbox.SIMPLE)

        cols = ["Symbol", "Qty", "Avg", "LTP", "Value", "P&L", "%"]
        if multi:
            cols.append("Broker")
        for col in cols:
            ht.add_column(col, justify="right" if col not in ("Symbol", "Broker") else "left")

        # Group by broker for cleaner display in multi mode
        prev_broker = None
        for h in sorted(summary.holdings, key=lambda x: (x.broker, x.symbol)):
            if multi and h.broker != prev_broker:
                if prev_broker is not None:
                    ht.add_row(*[""] * len(cols))   # blank separator row
                prev_broker = h.broker

            c = "green" if h.pnl >= 0 else "red"
            row = [
                h.symbol, str(h.qty),
                f"₹{h.avg_price:,.2f}", f"₹{h.ltp:,.2f}",
                f"₹{h.value:,.0f}",
                f"[{c}]₹{h.pnl:,.0f}[/{c}]",
                f"[{c}]{h.pnl_pct:+.1f}%[/{c}]",
            ]
            if multi:
                row.append(f"[dim]{h.broker.title()}[/dim]")
            ht.add_row(*row)

        console.print()
        console.print(ht)

        # Holdings subtotal by broker in multi mode
        if multi:
            by_broker: dict[str, float] = {}
            for h in summary.holdings:
                by_broker[h.broker] = by_broker.get(h.broker, 0) + h.pnl
            parts = [
                f"{b.title()}: {'[green]' if v >= 0 else '[red]'}₹{v:,.0f}{'[/green]' if v >= 0 else '[/red]'}"
                for b, v in by_broker.items()
            ]
            console.print(f"  [dim]Holdings P&L:[/dim]  {'  |  '.join(parts)}")

    # ── Positions table ────────────────────────────────────────
    if summary.positions:
        title = "F&O / Intraday Positions" + (f" — {brokers_label}" if multi else "")
        pt = Table(title=title, show_header=True, header_style="bold cyan", box=rbox.SIMPLE)
        cols = ["Symbol", "Qty", "Avg", "LTP", "P&L", "Δ Delta", "Θ Theta"]
        if multi:
            cols.append("Broker")
        for col in cols:
            pt.add_column(col, justify="right" if col not in ("Symbol", "Broker") else "left")

        for p in sorted(summary.positions, key=lambda x: (x.broker, x.symbol)):
            c = "green" if p.pnl >= 0 else "red"
            row = [
                p.symbol, str(p.qty),
                f"₹{p.avg_price:,.2f}", f"₹{p.ltp:,.2f}",
                f"[{c}]₹{p.pnl:,.0f}[/{c}]",
                f"{p.delta:.3f}" if p.delta is not None else "—",
                f"₹{p.theta:.0f}" if p.theta is not None else "—",
            ]
            if multi:
                row.append(f"[dim]{p.broker.title()}[/dim]")
            pt.add_row(*row)

        console.print(pt)

    if not summary.holdings and not summary.positions:
        console.print("[dim]No holdings or positions found.[/dim]")

    # ── Funds breakdown (multi-broker) ─────────────────────────
    if multi:
        f = summary.funds
        console.print(
            f"\n  [bold]Combined Funds:[/bold]  "
            f"Cash: [green]₹{f.available_cash:,.0f}[/green]  "
            f"Margin used: [yellow]₹{f.used_margin:,.0f}[/yellow]  "
            f"Total: [white]₹{f.total_balance:,.0f}[/white]"
        )

    # ── Greeks summary ─────────────────────────────────────────
    g = summary.greeks
    if g.net_delta or g.net_theta or g.net_vega:
        console.print(
            f"\n  [bold]Net Greeks:[/bold]  "
            f"Δ Delta [cyan]{g.net_delta:+.3f}[/cyan]  "
            f"Θ Theta [red]₹{g.net_theta:,.0f}/day[/red]  "
            f"ν Vega [yellow]₹{g.net_vega:,.0f} per 1% IV[/yellow]"
        )

    # ── Risk meter ─────────────────────────────────────────────
    r = summary.risk
    rating_color = {
        "LOW":    "green",
        "MEDIUM": "yellow",
        "HIGH":   "orange3",
        "DANGER": "bold red",
    }.get(r.risk_rating, "white")

    bar_len = 20
    filled  = int(r.deployment_pct / 100 * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)

    console.print(
        f"\n  [bold]Risk Meter:[/bold]  [{rating_color}]{r.risk_rating}[/{rating_color}]  "
        f"[{rating_color}]{bar}[/{rating_color}]  {r.deployment_pct:.1f}%"
    )
    console.print(
        f"  Free cash: [green]₹{r.free_cash:,.0f}[/green]  "
        f"Unrealised P&L: {'[green]' if r.unrealised_pnl >= 0 else '[red]'}"
        f"₹{r.unrealised_pnl:,.0f}"
        f"{'[/green]' if r.unrealised_pnl >= 0 else '[/red]'}"
    )
    console.print(
        f"  Max loss estimate: [red]₹{r.max_loss_estimate:,.0f}[/red]  "
        f"({r.max_loss_estimate / r.total_capital * 100:.1f}% of capital)\n"
        if r.total_capital > 0 else
        f"  Max loss estimate: [red]₹{r.max_loss_estimate:,.0f}[/red]\n"
    )


def _cmd_toggle_paper() -> None:
    """Show current paper / live trading mode."""
    import os
    current = os.environ.get("TRADING_MODE", "PAPER")
    if current == "PAPER":
        console.print(
            "\n[bold green]✓  Currently in PAPER mode.[/bold green]\n"
            "  All orders simulate fills without real money.\n"
            "  To switch to LIVE, set [bold]TRADING_MODE=LIVE[/bold] in .env\n"
            "  and restart. [red]Real money will be at risk.[/red]\n"
        )
    else:
        console.print(
            f"\n[bold yellow]⚠  Currently in {current} mode.[/bold yellow]\n"
            "  To switch to PAPER mode, set [bold]TRADING_MODE=PAPER[/bold] in .env and restart.\n"
        )


def cmd_help() -> None:
    console.print("""
[bold cyan]Available commands:[/bold cyan]

  [bold]Session[/bold]
    login            Log in (sets primary broker)
    connect          Add a second broker (e.g. connect Groww after Zerodha)
    disconnect       Remove a secondary broker connection
    brokers          List all connected brokers with fund summary
    logout           Log out of all brokers
    profile          Account profile (primary broker)
    funds            Cash and margin (primary broker)

  [bold]Portfolio[/bold]
    holdings         Delivery holdings (primary broker)
    positions        Open intraday / F&O positions (primary broker)
    portfolio        [bold green]Combined view: all brokers + Greeks + risk[/bold green]
    orders           Today's order history (primary broker)

  [bold]Analysis & Trading[/bold]
    morning-brief    Daily market context and recommended posture
    analyze <SYM>    Full fundamental + technical + options analysis
    trade            Guided strategy builder with AI recommendation

  [bold]AI[/bold]
    ai <message>     Chat directly with the AI agent
    provider         Show / switch AI provider (anthropic / openai / gemini / …)

  [bold]Interface[/bold]
    tui              Launch split-panel Textual TUI
    paper            Show paper-trading mode status

  [bold]Other[/bold]
    quit / exit      Exit the platform
""")


# ── Main REPL loop ────────────────────────────────────────────

def run_repl(broker: BrokerAPI) -> None:
    """Start the interactive command loop."""
    import os
    history_path = os.path.expanduser(HISTORY_FILE)
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    session: PromptSession = PromptSession(
        history    = FileHistory(history_path),
        completer  = WordCompleter(COMMANDS, ignore_case=True),
        style      = STYLE,
    )

    console.print(
        "\n[dim]Type [bold]help[/bold] for commands, "
        "[bold]quit[/bold] to exit.[/dim]"
    )
    if is_multi_broker():
        console.print(
            "[dim]Multiple brokers connected. "
            "Use [bold]portfolio[/bold] for combined view.[/dim]"
        )
    console.print()

    while True:
        try:
            raw = session.prompt("trade ❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Use 'quit' to exit.[/yellow]")
            continue

        if not raw:
            continue

        parts   = raw.split()
        command = parts[0].lower()
        args    = parts[1:]

        try:
            # ── Session ───────────────────────────────────────
            if command in ("quit", "exit", "q"):
                console.print("[dim]Goodbye.[/dim]")
                break

            elif command == "help":
                cmd_help()

            elif command == "login":
                broker = do_login()

            elif command == "connect":
                # Connect an additional broker
                choice = args[0] if args else None
                connect_broker(choice)

            elif command == "disconnect":
                choice = args[0] if args else None
                disconnect_broker(choice)

            elif command == "brokers":
                list_connected_brokers()

            elif command == "logout":
                do_logout()
                console.print("[yellow]You have been logged out.[/yellow]")
                break

            # ── Account ───────────────────────────────────────
            elif command == "profile":
                cmd_profile(broker)

            elif command == "funds":
                cmd_funds(broker)

            # ── Portfolio (single-broker raw views) ───────────
            elif command == "holdings":
                cmd_holdings(broker)

            elif command == "positions":
                cmd_positions(broker)

            elif command == "orders":
                cmd_orders(broker)

            # ── Portfolio (unified multi-broker view) ─────────
            elif command == "portfolio":
                from engine.portfolio import get_multi_broker_summary
                _cmd_portfolio(get_multi_broker_summary())

            # ── AI-powered commands ───────────────────────────
            elif command == "morning-brief":
                from app.commands.morning_brief import run as brief_run
                brief_run(use_agent=True)

            elif command == "analyze":
                symbol = args[0].upper() if args else ""
                if not symbol:
                    console.print("[red]Usage: analyze <SYMBOL>   e.g. analyze RELIANCE[/red]")
                else:
                    agent = get_agent()
                    agent.run_command("analyze", symbol=symbol)

            elif command == "ai":
                message = " ".join(args).strip()
                if not message:
                    console.print(
                        "[dim]Usage: ai <your message>    "
                        "e.g. ai What's the market doing today?[/dim]"
                    )
                else:
                    agent = get_agent()
                    agent.chat(message)

            elif command == "provider":
                if args:
                    new_provider = args[0].lower()
                    new_model    = args[1] if len(args) > 1 else None
                    if new_provider not in ALL_PROVIDERS:
                        console.print(
                            f"[red]Unknown provider '{new_provider}'.[/red] "
                            f"Valid: {', '.join(ALL_PROVIDERS)}"
                        )
                    else:
                        agent = get_agent()
                        agent.switch_provider(new_provider, new_model)
                else:
                    agent = get_agent()
                    agent.list_providers()

            elif command == "trade":
                sym  = args[0].upper() if args else None
                view = args[1].upper() if len(args) > 1 else None
                from app.commands.trade import run as trade_run
                trade_run(symbol=sym, view=view)

            elif command == "paper":
                _cmd_toggle_paper()

            elif command == "tui":
                console.print("[dim]Launching TUI...[/dim]")
                from ui.app import run_tui
                run_tui()
                console.print("[dim]Back in REPL mode.[/dim]")

            else:
                console.print(
                    f"[red]Unknown command:[/red] [bold]{command}[/bold]  "
                    f"(type [bold]help[/bold] for available commands)"
                )

        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
