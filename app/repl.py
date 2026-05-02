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
  quote <SYM>      Live price, OHLC, volume, and change
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

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.table import Table

from brokers.base import BrokerAPI
from brokers.session import (
    login as do_login,
    logout as do_logout,
    connect_broker,
    disconnect_broker,
    list_connected_brokers,
    is_multi_broker,
)
from agent.core import get_agent, ALL_PROVIDERS

console = Console()

HISTORY_FILE = "~/.trading_platform/.repl_history"

COMMANDS = [
    "login",
    "connect",
    "disconnect",
    "brokers",
    "logout",
    "profile",
    "funds",
    "holdings",
    "positions",
    "orders",
    "morning-brief",
    "analyze",
    "quick",
    "trade",
    "portfolio",
    "paper",
    "mode",
    "buy",
    "sell",
    "cancel",
    "ai",
    "alert",
    "alerts",
    "audit",
    "backtest",
    "persona",
    "debate",
    "clear",
    "debate",
    "deep-analyze",
    "drift",
    "active",
    "persona",
    "bulk-deals",
    "dcf",
    "deals",
    "delta-hedge",
    "earnings",
    "events",
    "exports",
    "flows",
    "gex",
    "greeks",
    "iv-smile",
    "macro",
    "memory",
    "most-active",
    "oi",
    "oi-profile",
    "quote",
    "scan",
    "search",
    "smile",
    "roll-options",
    "strategy",
    "mtf",
    "pairs",
    "patterns",
    "profile",
    "provider",
    "risk-report",
    "risk-status",
    "execute",
    "harness",
    "save-pdf",
    "explain",
    "explain-save",
    "telegram",
    "tui",
    "walkforward",
    "web",
    "whatif",
    "credentials",
    "help",
    "quit",
    "exit",
]

STYLE = Style.from_dict(
    {
        "prompt": "bold ansicyan",
    }
)


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
    table.add_row("Used Margin", f"[yellow]₹{f.used_margin:,.2f}[/yellow]")
    table.add_row("Total Balance", f"[white]₹{f.total_balance:,.2f}[/white]")
    console.print()
    console.print(table)
    console.print()


def cmd_holdings(broker: BrokerAPI) -> None:
    holdings = broker.get_holdings()
    if not holdings:
        console.print("[dim]No holdings found.[/dim]")
        return

    table = Table(title="Holdings", show_header=True, header_style="bold cyan")
    table.add_column("Symbol", style="bold white")
    table.add_column("Qty", justify="right")
    table.add_column("Avg", justify="right")
    table.add_column("LTP", justify="right")
    table.add_column("Today P&L", justify="right")
    table.add_column("Today %", justify="right")
    table.add_column("Overall P&L", justify="right")
    table.add_column("Overall %", justify="right")

    for h in holdings:
        pnl_style = "green" if h.pnl >= 0 else "red"
        day_chg = getattr(h, "day_change", 0) or 0
        day_pct = getattr(h, "day_change_pct", 0) or 0
        day_total = day_chg * h.quantity if day_chg else 0
        day_style = "green" if day_total >= 0 else "red"
        table.add_row(
            h.symbol,
            str(h.quantity),
            f"₹{h.avg_price:,.2f}",
            f"₹{h.last_price:,.2f}",
            f"[{day_style}]₹{day_total:,.0f}[/{day_style}]",
            f"[{day_style}]{day_pct:+.2f}%[/{day_style}]",
            f"[{pnl_style}]₹{h.pnl:,.2f}[/{pnl_style}]",
            f"[{pnl_style}]{h.pnl_pct:+.2f}%[/{pnl_style}]",
        )

    console.print()
    console.print(table)

    total_invested = sum(h.avg_price * h.quantity for h in holdings)
    total_pnl = sum(h.pnl for h in holdings)
    total_day = sum((getattr(h, "day_change", 0) or 0) * h.quantity for h in holdings)
    overall_pct = (total_pnl / total_invested * 100) if total_invested else 0
    pnl_style = "green" if total_pnl >= 0 else "red"
    day_style = "green" if total_day >= 0 else "red"
    console.print(
        f"\n  Invested: ₹{total_invested:,.0f}"
        f"  │  Today: [{day_style}]₹{total_day:,.0f}[/{day_style}]"
        f"  │  Overall: [{pnl_style}]₹{total_pnl:,.0f} ({overall_pct:+.2f}%)[/{pnl_style}]\n"
    )


def cmd_positions(broker: BrokerAPI) -> None:
    positions = broker.get_positions()
    if not positions:
        console.print("[dim]No open positions.[/dim]")
        return

    table = Table(title="Open Positions", show_header=True, header_style="bold cyan")
    table.add_column("Symbol", style="bold white")
    table.add_column("Product", style="dim")
    table.add_column("Qty", justify="right")
    table.add_column("Avg", justify="right")
    table.add_column("LTP", justify="right")
    table.add_column("P&L", justify="right")

    for p in positions:
        pnl_style = "green" if p.pnl >= 0 else "red"
        qty_str = f"+{p.quantity}" if p.quantity > 0 else str(p.quantity)
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
    table.add_column("Symbol", style="bold white")
    table.add_column("Type")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status")

    status_colors = {
        "COMPLETE": "green",
        "OPEN": "cyan",
        "REJECTED": "red",
        "CANCELLED": "yellow",
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


def cmd_quote(symbols: list[str]) -> None:
    """
    Display live quotes for one or more NSE/BSE symbols.

    Fetches via WebSocket cache → broker REST → yfinance fallback.
    """
    from market.quotes import get_quote

    instruments = []
    for sym in symbols:
        upper = sym.upper()
        if ":" in upper:
            instruments.append(upper)
        elif upper.endswith("-INDEX") or upper.endswith("-EQ"):
            instruments.append(f"NSE:{upper}")
        else:
            instruments.append(f"NSE:{upper}-EQ")

    quotes = get_quote(instruments)

    if not quotes:
        console.print(
            f"[red]No data found for {', '.join(symbols)}.[/red]\n"
            "[dim]Check the symbol name or try during market hours.[/dim]"
        )
        return

    single = len(quotes) == 1

    if single:
        key = next(iter(quotes))
        q = quotes[key]
        chg_style = "green" if q.change >= 0 else "red"
        arrow = "▲" if q.change >= 0 else "▼"

        console.print()
        console.print(f"  [bold white]{q.symbol}[/bold white]  [dim]{key}[/dim]")
        console.print(
            f"  [bold]{arrow} ₹{q.last_price:,.2f}[/bold]  "
            f"[{chg_style}]{q.change:+,.2f} ({q.change_pct:+.2f}%)[/{chg_style}]"
        )
        console.print()

        detail = Table(show_header=False, box=None, padding=(0, 2))
        detail.add_column(style="dim")
        detail.add_column(justify="right", style="bold")
        detail.add_row("Open", f"₹{q.open:,.2f}")
        detail.add_row("High", f"[green]₹{q.high:,.2f}[/green]")
        detail.add_row("Low", f"[red]₹{q.low:,.2f}[/red]")
        detail.add_row("Prev Close", f"₹{q.close:,.2f}")
        detail.add_row("Volume", f"{q.volume:,}")
        if q.bid is not None and q.ask is not None:
            detail.add_row("Bid / Ask", f"₹{q.bid:,.2f} / ₹{q.ask:,.2f}")
        if q.oi is not None:
            detail.add_row("Open Interest", f"{q.oi:,}")
        console.print(detail)
        console.print()
    else:
        table = Table(title="Live Quotes", show_header=True, header_style="bold cyan")
        table.add_column("Symbol", style="bold white")
        table.add_column("LTP", justify="right")
        table.add_column("Change", justify="right")
        table.add_column("% Change", justify="right")
        table.add_column("Open", justify="right")
        table.add_column("High", justify="right")
        table.add_column("Low", justify="right")
        table.add_column("Volume", justify="right")

        for key, q in quotes.items():
            chg_style = "green" if q.change >= 0 else "red"
            table.add_row(
                q.symbol,
                f"₹{q.last_price:,.2f}",
                f"[{chg_style}]{q.change:+,.2f}[/{chg_style}]",
                f"[{chg_style}]{q.change_pct:+.2f}%[/{chg_style}]",
                f"₹{q.open:,.2f}",
                f"₹{q.high:,.2f}",
                f"₹{q.low:,.2f}",
                f"{q.volume:,}",
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
                    ht.add_row(*[""] * len(cols))  # blank separator row
                prev_broker = h.broker

            c = "green" if h.pnl >= 0 else "red"
            row = [
                h.symbol,
                str(h.qty),
                f"₹{h.avg_price:,.2f}",
                f"₹{h.ltp:,.2f}",
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
                p.symbol,
                str(p.qty),
                f"₹{p.avg_price:,.2f}",
                f"₹{p.ltp:,.2f}",
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
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "orange3",
        "DANGER": "bold red",
    }.get(r.risk_rating, "white")

    bar_len = 20
    filled = int(r.deployment_pct / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

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
        if r.total_capital > 0
        else f"  Max loss estimate: [red]₹{r.max_loss_estimate:,.0f}[/red]\n"
    )


def _cmd_toggle_paper(args: list[str] | None = None) -> None:
    """Show or switch paper / live trading mode.

    Usage:
        mode           — show current mode
        mode paper     — switch to paper trading
        mode live      — switch to live trading (real money)
    """
    import os

    current = os.environ.get("TRADING_MODE", "PAPER").upper()

    if not args:
        # Just show current mode
        if current == "PAPER":
            console.print(
                "\n[bold green]✓  Currently in PAPER mode.[/bold green]\n"
                "  All orders simulate fills without real money.\n"
                "  Use [bold]mode live[/bold] to switch to live trading.\n"
            )
        else:
            console.print(
                "\n[bold yellow]⚠  Currently in LIVE mode.[/bold yellow]\n"
                "  [red]Real money is at risk.[/red]\n"
                "  Use [bold]mode paper[/bold] to switch to paper trading.\n"
            )
        return

    target = args[0].upper()
    if target not in ("PAPER", "LIVE"):
        console.print("[red]Usage: mode paper | mode live[/red]")
        return

    if target == current:
        console.print(f"[dim]Already in {current} mode.[/dim]")
        return

    os.environ["TRADING_MODE"] = target

    if target == "LIVE":
        console.print(
            "\n[bold yellow]⚠  Switched to LIVE mode.[/bold yellow]\n"
            "  [red]Orders will be placed with real money.[/red]\n"
            "  Use [bold]mode paper[/bold] to switch back.\n"
        )
    else:
        console.print(
            "\n[bold green]✓  Switched to PAPER mode.[/bold green]\n"
            "  Orders will simulate fills without real money.\n"
        )


def _cmd_web(port: int = 8765) -> None:
    """
    Start the FastAPI web server (broker login + portfolio API) and open the browser.

    Usage:
        web           — start on default port 8765
        web 9000      — start on custom port
    """
    import threading
    import webbrowser

    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]uvicorn not installed.[/red]  Run: [bold]pip install uvicorn[standard][/bold]"
        )
        return

    url = f"http://localhost:{port}"
    console.print(f"\n[bold cyan]🌐 Starting web server on {url}[/bold cyan]")
    console.print("[dim]  Zerodha, Groww, Angel One, Upstox and Fyers login available.[/dim]")
    console.print("[dim]  Press Ctrl+C in this terminal to stop the server.[/dim]\n")

    # Open browser slightly after server starts
    def _open():
        import time as _time

        _time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()

    # Run uvicorn (blocks until Ctrl+C)
    uvicorn.run(
        "web.api:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",  # quiet — the REPL already has UI
    )
    console.print("[dim]\nWeb server stopped. Back in REPL.[/dim]\n")


def _warn_if_mock(broker: BrokerAPI) -> None:
    """Show a warning if the broker is mock/demo — data is simulated."""
    try:
        profile = broker.get_profile()
        if profile.broker.upper() in ("MOCK", "PAPER", "DEMO"):
            console.print(
                "[yellow dim]  (Demo mode — data below is simulated. Run 'login' to connect a real broker.)[/yellow dim]"
            )
    except Exception:
        pass


def cmd_help() -> None:
    from rich.panel import Panel

    sections = {
        "Analysis (AI-powered)": [
            ("analyze <SYM>", "Multi-agent analysis (7 analysts + debate + trade plan)"),
            ("deep-analyze <SYM>", "Full LLM mode (11 calls — every analyst uses AI)"),
            ("ai <message>", "Chat with AI — follow-ups keep context"),
            ("strategy new [--simple]", "Build a strategy from plain English"),
            ("strategy list", "List saved strategies"),
            ("morning-brief", "Daily market context + AI narrative"),
        ],
        "Market Data": [
            ("quote <SYM> [SYM...]", "Live price, OHLC, volume, and change"),
            ("earnings [SYM...]", "Upcoming quarterly results calendar"),
            ("flows", "FII/DII flow intelligence with signals"),
            ("events [days]", "Event-driven strategy recommendations"),
            ("patterns", "Active India-specific market patterns"),
            ("macro [SYM]", "USD/INR, crude, gold + stock linkages"),
        ],
        "Backtest & Simulation": [
            ("backtest SYM rsi", "RSI strategy backtest"),
            ("backtest SYM ma 20 50", "EMA crossover backtest"),
            ("backtest SYM macd|bb", "MACD or Bollinger backtest"),
            ("backtest NIFTY straddle", "Options: ATM straddle before expiry"),
            ("backtest NIFTY iron-condor", "Options: sell iron condor"),
            ("walkforward SYM rsi", "Walk-forward test (rolling windows)"),
            ("whatif nifty -3", "What if NIFTY drops 3%? (real beta)"),
            ("whatif SYM -10", "Single stock scenario"),
            ("pairs [A B]", "Pair trading scan or specific pair"),
        ],
        "Risk & Portfolio": [
            ("funds", "Cash and margin"),
            ("holdings", "Delivery holdings"),
            ("positions", "Open intraday / F&O positions"),
            ("portfolio", "Combined view: all brokers + risk"),
            ("greeks", "Portfolio Greeks with warnings + actions"),
            ("delta-hedge", "Suggest trades to neutralize delta"),
            ("roll-options", "Find expiring positions, suggest rolls"),
            ("risk-report", "VaR/CVaR portfolio risk analysis"),
            ("risk-status", "Daily P&L, trade counts, hard limit usage"),
            ("orders", "Today's orders"),
        ],
        "Memory & Learning": [
            ("memory", "Recent trade analyses"),
            ("memory stats", "Performance statistics"),
            ("memory <SYM>", "Past analyses for a symbol"),
            ("memory outcome ID WIN [pnl]", "Record trade outcome"),
            ("profile", "Your personal trading style"),
            ("drift", "Model drift detection"),
            ("audit <ID>", "Post-mortem on a specific trade"),
        ],
        "Alerts": [
            ("alert SYM above 2800", "Price alert"),
            ("alert SYM RSI above 70", "Technical alert"),
            ("alert SYM above 2800 AND RSI above 70", "Conditional (AND)"),
            ("alerts", "List active alerts"),
            ("alert remove <ID>", "Remove an alert"),
        ],
        "Output & Exports": [
            ("save-pdf", "Save previous output as PDF"),
            ("explain", "Explain previous output simply"),
            ("explain-save", "Explain + save as PDF"),
            ("--pdf", "Flag: append to any command"),
            ("--explain", "Flag: append to any command"),
            ("exports", "List all saved PDF exports"),
            ("exports open <file>", "Open a saved export"),
            ("exports clear --older-than 30d", "Delete old exports"),
        ],
        "Session": [
            ("login", "Connect to a broker"),
            ("provider [name|setup]", "Show/switch AI provider, or run setup wizard"),
            ("telegram [setup]", "Start bot / run guided setup wizard"),
            ("clear", "Start fresh AI conversation (reset context)"),
            ("credentials", "Manage API keys"),
            ("quit / exit", "Exit"),
        ],
    }

    for section, commands in sections.items():
        lines = []
        for cmd, desc in commands:
            lines.append(f"  [cyan]{cmd:34s}[/cyan] {desc}")
        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold]{section}[/bold]",
                border_style="dim",
                padding=(0, 1),
            )
        )


# ── Alert command handler ──────────────────────────────────────


def _handle_backtest_command(args: list[str]) -> None:
    """Handle: backtest SYMBOL [strategy] [args...] [--period 2y] [--pdf] [--explain] [--html] [--compare] [--fast]"""
    from engine.output import parse_output_flags, handle_output_flags

    wants_html = "--html" in args
    wants_compare = "--compare" in args
    wants_fast = "--fast" in args
    clean_args, wants_pdf, wants_explain, _ = parse_output_flags(
        [a for a in args if a not in ("--html", "--compare", "--fast")]
    )
    if not clean_args:
        console.print(
            "[red]Usage: backtest SYMBOL [strategy] [--pdf] [--explain] [--html] [--compare] [--fast][/red]\n"
            "[dim]  backtest RELIANCE rsi              RSI(30/70) strategy (event-driven)\n"
            "  backtest RELIANCE rsi --fast        Vectorized, <1s (no slippage sim)\n"
            "  backtest RELIANCE ma 20 50          EMA crossover\n"
            "  backtest RELIANCE macd --pdf         Export to PDF\n"
            "  backtest RELIANCE bb --explain       Add simple explanation\n"
            "  backtest RELIANCE rsi macd bb --compare --html  Compare + HTML report\n"
            "  Strategies: rsi, ma, ema, macd, bb/bollinger[/dim]"
        )
        return

    if wants_fast:
        from engine.backtest_vectorized import run_vectorized_backtest as run_backtest
    else:
        from engine.backtest import run_backtest

    symbol = clean_args[0].upper()
    # Track last symbol so strategy builder can pick it up
    try:
        from app.commands.strategy import set_last_symbol

        set_last_symbol(symbol)
    except Exception:
        pass
    strategy_name = clean_args[1].lower() if len(clean_args) > 1 else "rsi"
    strategy_args = clean_args[2:] if len(clean_args) > 2 else []

    # Check for --period and --trades flags
    period = "1y"
    num_trades = 10
    if "--period" in clean_args:
        idx = clean_args.index("--period")
        if idx + 1 < len(clean_args):
            period = clean_args[idx + 1]
            strategy_args = [a for a in strategy_args if a not in ("--period", period)]
    if "--trades" in clean_args:
        idx = clean_args.index("--trades")
        if idx + 1 < len(clean_args):
            try:
                num_trades = int(clean_args[idx + 1])
            except ValueError:
                pass
            strategy_args = [a for a in strategy_args if a not in ("--trades", clean_args[idx + 1])]

    # ── Multi-strategy compare mode ──────────────────────────
    if wants_compare or (wants_html and len(clean_args) > 2):
        # All positional args after the symbol are strategy names
        strategies = [a for a in clean_args[1:] if not a.startswith("--")] or ["rsi"]
        all_results = []
        for strat in strategies:
            console.print(f"[dim]Running {strat} on {symbol} ({period})...[/dim]")
            try:
                r = run_backtest(symbol=symbol, strategy_name=strat, period=period)
                all_results.append(r)
                ret_color = "green" if r.total_return >= 0 else "red"
                console.print(
                    f"  [bold]{strat:12s}[/bold] [{ret_color}]{r.total_return:+.2f}%[/{ret_color}]"
                    f"  Sharpe {r.sharpe_ratio:.2f}"
                )
            except Exception as e:
                console.print(f"  [red]{strat}[/red] failed: {e}")

        if all_results and wants_html:
            from engine.backtest_report import generate_html_report

            report_path = generate_html_report(all_results)
            console.print(f"\n[green]HTML report saved:[/green] {report_path}")
        return

    console.print(f"\n[dim]Running backtest: {symbol} / {strategy_name} / {period}...[/dim]")

    try:
        result = run_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            period=period,
        )
        result.print_summary()
        result.print_trades(num_trades)
        # Capture for post-processing — handle both equity and options results
        result_symbol = getattr(result, "symbol", None) or getattr(result, "underlying", symbol)
        buy_hold = getattr(result, "buy_hold_return", None)
        profit_factor = getattr(result, "profit_factor", None)
        total_pnl = getattr(result, "total_pnl", None)

        lines = [f"Backtest: {result.strategy_name} on {result_symbol}"]
        lines.append(f"Period: {result.start_date} to {result.end_date}")
        lines.append(f"Return: {result.total_return:+.2f}%")
        if buy_hold is not None:
            lines.append(f"Buy & Hold: {buy_hold:+.2f}%")
        if total_pnl is not None:
            lines.append(f"Total P&L: Rs.{total_pnl:,.0f}")
        lines.append(f"Sharpe: {result.sharpe_ratio:.2f}, Max DD: {result.max_drawdown:.2f}%")
        lines.append(f"Trades: {result.total_trades}, Win Rate: {result.win_rate:.1f}%")
        if profit_factor is not None:
            lines.append(f"Profit Factor: {profit_factor:.2f}")

        _bt_summary = "\n".join(lines)
        _last_output = _bt_summary
        _last_command = f"Backtest {symbol} {strategy_name}"
        if wants_html:
            from engine.backtest_report import generate_html_report

            report_path = generate_html_report([result])
            console.print(f"\n[green]HTML report saved:[/green] {report_path}")
        if wants_pdf or wants_explain:
            handle_output_flags(
                _bt_summary, f"Backtest {symbol} {strategy_name}", wants_pdf, wants_explain
            )
    except Exception as e:
        console.print(f"[red]Backtest failed:[/red] {e}")
        console.print(
            "[dim]Check that the symbol exists and you have market data access (broker login or yfinance).[/dim]"
        )


def _handle_whatif_command(args: list[str]) -> None:
    """Handle: whatif nifty -3 | whatif RELIANCE -10 | whatif RELIANCE -5 HDFCBANK 3"""
    if not args:
        console.print(
            "[red]Usage: whatif <scenario>[/red]\n"
            "[dim]  whatif nifty -3              NIFTY drops 3%\n"
            "  whatif RELIANCE -10           RELIANCE drops 10%\n"
            "  whatif RELIANCE -5 TCS 3      Multiple stocks move[/dim]"
        )
        return

    from engine.simulator import Simulator

    sim = Simulator()

    first = args[0].upper()

    if first in ("NIFTY", "MARKET", "NIFTY50"):
        if len(args) < 2:
            console.print("[red]Usage: whatif nifty -3[/red]")
            return
        pct = float(args[1])
        result = sim.scenario_market_move(pct)

    elif len(args) >= 4 and len(args) % 2 == 0:
        # Multiple: whatif RELIANCE -5 HDFCBANK 3
        moves = {}
        for i in range(0, len(args), 2):
            moves[args[i].upper()] = float(args[i + 1])
        result = sim.scenario_custom(moves)

    elif len(args) >= 2:
        # Single stock: whatif RELIANCE -10
        result = sim.scenario_stock_move(first, float(args[1]))

    else:
        console.print("[red]Invalid scenario format.[/red]")
        return

    result.print_summary()


def _handle_memory_command(args: list[str]) -> None:
    """Handle memory commands: memory [stats|list|reflect <id>|<symbol>|outcome <id> <result>]"""
    from engine.memory import trade_memory

    sub = args[0].lower() if args else "list"

    if sub == "stats":
        trade_memory.print_stats()

    elif sub == "list":
        n = int(args[1]) if len(args) > 1 else 10
        trade_memory.print_recent(n)

    elif sub == "outcome":
        if len(args) < 3:
            console.print("[red]Usage: memory outcome <trade_id> WIN|LOSS [pnl] [notes][/red]")
            return
        trade_id = args[1]
        outcome = args[2].upper()
        pnl = float(args[3]) if len(args) > 3 else None
        notes = " ".join(args[4:]) if len(args) > 4 else ""
        if trade_memory.record_outcome(trade_id, outcome=outcome, actual_pnl=pnl, notes=notes):
            console.print(f"[green]Recorded outcome for {trade_id}: {outcome}[/green]")
        else:
            console.print(f"[red]Trade ID {trade_id} not found.[/red]")

    elif sub == "reflect":
        if len(args) < 2:
            console.print("[red]Usage: memory reflect <trade_id>[/red]")
            return
        trade_id = args[1]
        # Optionally use the active LLM provider for richer reflection
        llm_provider = None
        try:
            from agent.core import ToolRegistry, get_fast_provider, get_deep_provider

            llm_provider = get_fast_provider(
                ToolRegistry(), deep_provider=get_deep_provider(ToolRegistry())
            )
        except Exception:
            pass
        console.print(f"[dim]Reflecting on trade {trade_id}...[/dim]")
        lesson = trade_memory.reflect_and_remember(trade_id, llm_provider=llm_provider)
        if not lesson:
            console.print(f"[red]Trade ID {trade_id} not found.[/red]")
        else:
            console.print(f"\n[bold]Lesson:[/bold] {lesson}\n")

    elif sub == "clear":
        console.print("[yellow]This will delete all trade memory. Type 'yes' to confirm:[/yellow]")
        from rich.prompt import Prompt

        if Prompt.ask("[bold]Confirm[/bold]", default="no") == "yes":
            from pathlib import Path

            p = Path.home() / ".trading_platform" / "trade_memory.json"
            if p.exists():
                p.unlink()
            trade_memory._records = []
            console.print("[green]Trade memory cleared.[/green]")

    else:
        # Treat as symbol lookup
        symbol = sub.upper()
        records = trade_memory.query(symbol=symbol)
        if records:
            console.print(f"\n[bold]Past analyses for {symbol}:[/bold]")
            for r in records:
                verdict_style = {
                    "BUY": "green",
                    "STRONG_BUY": "bold green",
                    "SELL": "red",
                    "STRONG_SELL": "bold red",
                }.get(r.verdict, "yellow")
                outcome_str = f" → {r.outcome}" if r.outcome else ""
                console.print(
                    f"  [{r.id}] {r.timestamp[:10]}  "
                    f"[{verdict_style}]{r.verdict}[/{verdict_style}] "
                    f"(conf: {r.confidence}%) {r.strategy or ''}{outcome_str}"
                )
            console.print()
        else:
            console.print(f"[dim]No analyses found for {symbol}.[/dim]")


def _handle_patterns_command() -> None:
    """Display active India-specific market patterns."""
    from engine.patterns import get_active_patterns

    patterns = get_active_patterns()
    if not patterns:
        console.print("[dim]No specific patterns active today.[/dim]")
        return

    console.print(f"\n[bold]Active Market Patterns ({len(patterns)}):[/bold]\n")
    for p in patterns:
        impact_style = {
            "BULLISH": "green",
            "BEARISH": "red",
            "VOLATILE": "yellow",
            "NEUTRAL": "white",
        }.get(p.impact, "white")

        console.print(
            f"  [{impact_style}]{p.impact:9s}[/{impact_style}] "
            f"[bold]{p.name}[/bold] (confidence: {p.confidence}%)"
        )
        console.print(f"             {p.description[:100]}")
        console.print(f"             [cyan]Action:[/cyan] {p.action}")
        console.print()


def _handle_alert_command(args: list[str]) -> None:
    """
    Handle alert / alerts commands.

    Usage:
        alert RELIANCE above 2800          → price alert
        alert NIFTY below 22000            → price alert
        alert RELIANCE RSI above 70        → technical alert
        alert list  /  alerts              → list all active alerts
        alert remove <id>                  → remove an alert
    """
    from engine.alerts import alert_manager

    if not args or args[0].lower() == "list":
        alert_manager.print_alerts()
        return

    # Support "alert add SYMBOL ..." as alias for "alert SYMBOL ..."
    if args[0].lower() == "add":
        args = args[1:]

    # Map operator aliases: > → above, < → below, >= → above, <= → below
    args = [
        "above" if a == ">" or a == ">=" else "below" if a == "<" or a == "<=" else a for a in args
    ]

    if args[0].lower() == "remove" and len(args) >= 2:
        removed = alert_manager.remove_alert(args[1])
        if removed:
            console.print(f"[green]Alert {args[1]} removed.[/green]")
        else:
            console.print(f"[red]Alert {args[1]} not found.[/red]")
        return

    # Parse: SYMBOL [INDICATOR] ABOVE/BELOW THRESHOLD
    # Conditional: SYMBOL price above 2800 AND RSI above 70
    if len(args) < 3:
        console.print(
            "[dim]Usage:\n"
            "  alert RELIANCE above 2800                     (price alert)\n"
            "  alert RELIANCE RSI above 70                   (technical alert)\n"
            "  alert RELIANCE above 2800 AND RSI above 70    (conditional: AND)\n"
            "  alert list                                    (show active alerts)\n"
            "  alert remove <id>                             (remove alert)[/dim]"
        )
        return

    symbol = args[0].upper()
    indicators = {"RSI", "MACD", "ADX", "ATR"}

    # Check for AND — conditional alert
    remaining = " ".join(args[1:])
    if " AND " in remaining.upper():
        # Parse conditional: "above 2800 AND RSI above 70"
        parts = remaining.upper().split(" AND ")
        conditions = []
        for part in parts:
            tokens = part.strip().split()
            if len(tokens) >= 3 and tokens[0] in indicators:
                # TECHNICAL: RSI above 70
                conditions.append(
                    {
                        "condition_type": "TECHNICAL",
                        "indicator": tokens[0],
                        "condition": tokens[1],
                        "threshold": float(tokens[2]),
                    }
                )
            elif len(tokens) >= 2:
                # PRICE: above 2800
                cond = tokens[0] if tokens[0] in ("ABOVE", "BELOW") else tokens[0]
                conditions.append(
                    {
                        "condition_type": "PRICE",
                        "condition": cond,
                        "threshold": float(
                            tokens[1] if tokens[0] in ("ABOVE", "BELOW") else tokens[-1]
                        ),
                    }
                )

        if conditions:
            alert = alert_manager.add_conditional_alert(symbol, conditions)
            console.print(
                f"[green]✓ Conditional alert created:[/green] [bold]{alert.describe()}[/bold]"
                f"  [dim](ID: {alert.id})[/dim]"
            )
        else:
            console.print("[red]Could not parse conditional alert.[/red]")
        return

    if len(args) >= 4 and args[1].upper() in indicators:
        # Technical alert: SYMBOL INDICATOR CONDITION THRESHOLD
        indicator = args[1].upper()
        condition = args[2].upper()
        try:
            threshold = float(args[3])
        except ValueError:
            console.print("[red]Invalid threshold value.[/red]")
            return
        alert = alert_manager.add_technical_alert(
            symbol,
            indicator,
            condition,
            threshold,
        )
    else:
        # Price alert: SYMBOL CONDITION THRESHOLD
        condition = args[1].upper()
        if condition == "CROSSES":
            condition = "ABOVE"
        try:
            threshold = float(args[2])
        except ValueError:
            console.print("[red]Invalid threshold value.[/red]")
            return
        alert = alert_manager.add_price_alert(symbol, condition, threshold)

    console.print(
        f"[green]✓ Alert created:[/green] [bold]{alert.describe()}[/bold]"
        f"  [dim](ID: {alert.id})[/dim]"
    )


# ── Main REPL loop ────────────────────────────────────────────


def run_repl(broker: BrokerAPI) -> None:
    """Start the interactive command loop."""
    import os

    history_path = os.path.expanduser(HISTORY_FILE)
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    session: PromptSession = PromptSession(
        history=FileHistory(history_path),
        completer=WordCompleter(COMMANDS, ignore_case=True),
        style=STYLE,
    )

    # Start background alert poller (daemon thread, checks every 60s)
    from engine.alerts import alert_manager

    alert_manager.start_realtime()  # WebSocket ticks → instant alerts (falls back to 60s polling)

    console.print("\n[dim]Type [bold]help[/bold] for commands, [bold]quit[/bold] to exit.[/dim]")
    if is_multi_broker():
        console.print(
            "[dim]Multiple brokers connected. Use [bold]portfolio[/bold] for combined view.[/dim]"
        )
    console.print()

    # Auto-discover and register skill plugins from skills/ directory (#187)
    try:
        from engine.skill_loader import auto_register_skills
        from agent.tools import build_registry as _build_skill_registry

        _skill_registry = _build_skill_registry()
        _registered = auto_register_skills(_skill_registry)
        if _registered:
            console.print(f"[dim]Skills loaded: {', '.join(_registered)}[/dim]")
    except Exception:
        pass  # skill loading is best-effort — never block startup

    # Buffer for post-processing commands (save-pdf, explain, explain-save)
    _last_output: str = ""
    _last_command: str = ""
    _last_trade_plans: dict = {}  # from analyze → 3 risk persona plans

    def _build_prompt():
        """Dynamic prompt — shows 📩 badge when Telegram commands are in-flight."""
        try:
            from bot.status import get_badge

            badge = get_badge()
        except Exception:
            badge = ""
        if badge:
            return HTML(f'<b>trade</b><style fg="orange">{badge}</style> ❯ ')
        return "trade ❯ "

    def _build_toolbar():
        """Status bar: WebSocket connection state + alerts mode."""
        parts = []
        try:
            from market.websocket import ws_manager

            if ws_manager.connected:
                parts.append("ws:live")
            else:
                parts.append("ws:delayed")
        except Exception:
            parts.append("ws:delayed")
        try:
            from engine.alerts import alert_manager

            if alert_manager.active_count() > 0:
                parts.append(f"{alert_manager.active_count()} alert(s)")
        except Exception:
            pass
        return " · ".join(parts)

    while True:
        try:
            raw = session.prompt(
                _build_prompt, bottom_toolbar=_build_toolbar, refresh_interval=1.0
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Use 'quit' to exit.[/yellow]")
            continue

        if not raw:
            continue

        parts = raw.split()
        command = parts[0].lower()
        args = parts[1:]

        # ── Global --pdf / --save-pdf flag ─────────────────────
        # Strip the flag before any command sees it, so every
        # command gets PDF support automatically.
        _global_pdf = "--pdf" in args or "--save-pdf" in args
        if _global_pdf:
            args = [a for a in args if a not in ("--pdf", "--save-pdf")]
            _pre_pdf_output = _last_output  # snapshot before command

        try:
            # ── Session ───────────────────────────────────────
            if command in ("quit", "exit", "q"):
                console.print("[dim]Goodbye.[/dim]")
                # Force-exit immediately. Background threads (Telegram bot,
                # websocket, executor pool) are non-daemon and would keep the
                # process alive indefinitely.  os._exit() is the only reliable
                # way to terminate without waiting for them.
                import os as _os

                _os._exit(0)

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

            elif command == "data-broker":
                from brokers.session import set_data_broker

                if not args:
                    console.print("[red]Usage: data-broker <broker_name>[/red]")
                else:
                    set_data_broker(args[0])

            elif command == "exec-broker":
                from brokers.session import set_exec_broker

                if not args:
                    console.print("[red]Usage: exec-broker <broker_name>[/red]")
                else:
                    set_exec_broker(args[0])

            elif command == "logout":
                do_logout()
                console.print("[yellow]You have been logged out.[/yellow]")
                break

            # ── Account ───────────────────────────────────────
            elif command == "profile":
                _warn_if_mock(broker)
                cmd_profile(broker)

            elif command == "funds":
                _warn_if_mock(broker)
                try:
                    cmd_funds(broker)
                except Exception as e:
                    console.print(
                        f"[red]Error: {e}[/red]\n[dim]Broker API may be slow. Try again during market hours.[/dim]"
                    )

            # ── Portfolio (single-broker raw views) ───────────
            elif command == "holdings":
                _warn_if_mock(broker)
                try:
                    cmd_holdings(broker)
                except Exception as e:
                    console.print(f"[red]Holdings fetch failed:[/red] {e}")
                    console.print(
                        "[dim]Your broker session may have expired. Try: logout → login[/dim]"
                    )

            elif command == "positions":
                _warn_if_mock(broker)
                try:
                    cmd_positions(broker)
                except Exception as e:
                    console.print(f"[red]Positions fetch failed:[/red] {e}")
                    console.print(
                        "[dim]Your broker session may have expired. Try: logout → login[/dim]"
                    )

            elif command == "orders":
                _warn_if_mock(broker)
                try:
                    cmd_orders(broker)
                except Exception as e:
                    console.print(f"[red]Orders fetch failed:[/red] {e}")
                    console.print(
                        "[dim]Your broker session may have expired. Try: logout → login[/dim]"
                    )

            elif command == "quote":
                if not args:
                    console.print(
                        "[red]Usage: quote <SYMBOL> [SYMBOL ...][/red]\n"
                        "[dim]  quote RELIANCE            single stock\n"
                        "  quote TCS INFY WIPRO       multiple stocks\n"
                        "  quote NSE:NIFTY50-INDEX    index quote\n"
                        "  quote NIFTY BANKNIFTY      shorthand for indices[/dim]"
                    )
                else:
                    idx_aliases = {
                        "NIFTY": "NSE:NIFTY50-INDEX",
                        "NIFTY50": "NSE:NIFTY50-INDEX",
                        "BANKNIFTY": "NSE:NIFTYBANK-INDEX",
                        "NIFTYBANK": "NSE:NIFTYBANK-INDEX",
                        "SENSEX": "BSE:SENSEX-INDEX",
                        "VIX": "NSE:INDIAVIX-INDEX",
                        "INDIAVIX": "NSE:INDIAVIX-INDEX",
                        "FINNIFTY": "NSE:FINNIFTY-INDEX",
                    }
                    resolved = [idx_aliases.get(a.upper(), a) for a in args]
                    # Track last plain stock symbol (not index aliases)
                    plain = [a.upper() for a in args if a.upper() not in idx_aliases]
                    if plain:
                        try:
                            from app.commands.strategy import set_last_symbol

                            set_last_symbol(plain[-1])
                        except Exception:
                            pass
                    cmd_quote(resolved)

            # ── Portfolio (unified multi-broker view) ─────────
            elif command == "portfolio":
                _warn_if_mock(broker)
                try:
                    from engine.portfolio import get_multi_broker_summary

                    _cmd_portfolio(get_multi_broker_summary())
                except Exception as e:
                    console.print(f"[red]Portfolio fetch failed:[/red] {e}")
                    console.print(
                        "[dim]One or more broker sessions may have expired. Try: logout → login[/dim]"
                    )

            # ── AI-powered commands ───────────────────────────
            elif command == "morning-brief":
                from app.commands.morning_brief import run as brief_run

                brief_run(use_agent=True)

            elif command == "analyze":
                from engine.output import parse_output_flags, handle_output_flags

                clean_args, wants_pdf, wants_explain, _ = parse_output_flags(args)
                wants_risk_debate = "--risk-debate" in clean_args
                clean_args = [a for a in clean_args if a != "--risk-debate"]
                symbol = clean_args[0].upper() if clean_args else ""
                # Everything after the symbol is treated as inline synthesis context.
                # e.g. "analyze INFY focus on AI revenue" — no mid-run interruption.
                inline_context = " ".join(clean_args[1:]).strip() or None
                if not symbol:
                    console.print(
                        "[red]Usage: analyze <SYMBOL> [context hints] [--risk-debate] [--pdf] [--explain][/red]"
                    )
                else:
                    try:
                        from app.commands.strategy import set_last_symbol

                        set_last_symbol(symbol)
                    except Exception:
                        pass
                    agent = get_agent()

                    if inline_context:
                        console.print(f"[dim]  ◆ Context: {inline_context}[/dim]")

                    # Pass context inline — never block mid-analysis for input.
                    def _make_context_cb(_ctx):
                        def _cb():
                            return _ctx

                        return _cb

                    from agent.multi_agent import MultiAgentAnalyzer

                    _analyzer = MultiAgentAnalyzer(
                        registry=agent._registry,
                        llm_provider=agent._provider,
                        parallel=True,
                        verbose=True,
                        risk_debate=wants_risk_debate,
                        context_prompt_callback=_make_context_cb(inline_context),
                    )
                    output = _analyzer.analyze(symbol, "NSE")
                    agent._last_trade_plans = getattr(_analyzer, "last_trade_plans", {})

                    _last_output = output or ""
                    _last_command = f"Analysis {symbol}"
                    _last_trade_plans = getattr(agent, "_last_trade_plans", {})
                    if wants_pdf or wants_explain:
                        handle_output_flags(
                            output or "",
                            f"Analysis {symbol}",
                            wants_pdf,
                            wants_explain,
                            llm_provider=agent._provider if wants_explain else None,
                        )

            elif command == "clear":
                agent = get_agent()
                agent.clear_history()

            elif command in ("alert", "alerts"):
                _handle_alert_command(args)

            elif command == "memory":
                _handle_memory_command(args)

            elif command == "patterns":
                _handle_patterns_command()

            elif command == "earnings":
                from market.earnings import print_earnings_calendar

                syms = [a.upper() for a in args] if args else None
                print_earnings_calendar(syms)

            elif command in ("most-active", "active"):
                from market.active_stocks import print_most_active

                by = "value" if "--value" in args else "volume"
                print_most_active(by=by)

            elif command in ("bulk-deals", "block-deals", "deals"):
                from market.bulk_deals import print_deals

                sym = args[0].upper() if args and not args[0].startswith("-") else None
                print_deals(symbol=sym)

            elif command in ("oi-profile", "oi"):
                from market.oi_profile import print_oi_profile

                sym = args[0].upper() if args else "NIFTY"
                print_oi_profile(sym)

            elif command in ("iv-smile", "smile"):
                from analysis.volatility_surface import print_iv_smile

                sym = args[0].upper() if args else "NIFTY"
                print_iv_smile(sym)

            elif command == "gex":
                from analysis.gex import print_gex

                sym = args[0].upper() if args else "NIFTY"
                print_gex(sym)

            elif command == "scan":
                from market.options_scanner import print_scan_results

                quick = "--quick" in args
                syms = [a.upper() for a in args if not a.startswith("-")] or None
                print_scan_results(symbols=syms, quick=quick)

            elif command == "dcf":
                if not args:
                    console.print("[red]Usage: dcf SYMBOL [--growth 15] [--wacc 12][/red]")
                else:
                    from analysis.dcf import print_dcf

                    sym = args[0].upper()
                    growth = None
                    wacc_val = None
                    if "--growth" in args:
                        idx = args.index("--growth")
                        if idx + 1 < len(args):
                            try:
                                growth = float(args[idx + 1])
                            except ValueError:
                                pass
                    if "--wacc" in args:
                        idx = args.index("--wacc")
                        if idx + 1 < len(args):
                            try:
                                wacc_val = float(args[idx + 1])
                            except ValueError:
                                pass
                    print_dcf(sym, growth_rate=growth, wacc=wacc_val)

            elif command == "flows":
                from market.flow_intel import print_flow_report

                print_flow_report()

            elif command == "greeks":
                from engine.portfolio import print_portfolio_greeks, get_position_greeks
                from engine.greeks_manager import build_dashboard, print_dashboard

                print_portfolio_greeks()
                # Enhanced dashboard with warnings
                pg = get_position_greeks()
                dash = build_dashboard(pg.net_delta, pg.net_theta, pg.net_vega, pg.net_gamma)
                if dash.warnings:
                    print_dashboard(dash)

            elif command == "delta-hedge":
                from engine.portfolio import get_position_greeks
                from engine.greeks_manager import compute_delta_hedge, print_delta_hedge

                pg = get_position_greeks()
                target = (
                    float(args[0])
                    if args and args[0].replace("-", "").replace("+", "").isdigit()
                    else 0.0
                )
                suggestion = compute_delta_hedge(pg.net_delta, target_delta=target)
                print_delta_hedge(suggestion)

            elif command == "roll-options":
                from engine.portfolio import get_position_greeks
                from engine.greeks_manager import compute_roll_suggestions, print_roll_suggestions

                pg = get_position_greeks()
                dte = 3
                if "--dte" in args:
                    idx = args.index("--dte")
                    if idx + 1 < len(args):
                        try:
                            dte = int(args[idx + 1])
                        except ValueError:
                            pass
                suggestions = compute_roll_suggestions(pg.positions_with_greeks, dte_threshold=dte)
                print_roll_suggestions(suggestions)

            elif command == "macro":
                from market.macro import print_macro_snapshot

                sym = args[0].upper() if args else None
                print_macro_snapshot(sym)

            elif command == "risk-report":
                from engine.risk_metrics import print_risk_report

                print_risk_report()

            elif command == "risk-status":
                from engine.risk_limits import risk_limits

                status = risk_limits.get_status()
                table = Table(
                    title="Risk Limits Status",
                    show_header=False,
                    box=None,
                    padding=(0, 2),
                )
                table.add_column(style="dim")
                table.add_column(style="bold")

                daily_loss = status["daily_loss"]
                loss_style = "red" if daily_loss < 0 else "green"
                table.add_row(
                    "Daily P&L",
                    f"[{loss_style}]₹{daily_loss:,.0f}[/{loss_style}]",
                )
                table.add_row(
                    "Daily Loss Cap",
                    f"₹{status['max_daily_loss']:,.0f}",
                )
                room = status["remaining_loss_room"]
                room_style = "green" if room > 0 else "red"
                table.add_row(
                    "Remaining Loss Room",
                    f"[{room_style}]₹{room:,.0f}[/{room_style}]",
                )
                table.add_row(
                    "Trades Today",
                    f"{status['trades_today']} / {status['max_daily_trades']}",
                )
                table.add_row(
                    "Remaining Trades",
                    f"{status['remaining_trades']}",
                )
                table.add_row(
                    "Max Trades per Symbol",
                    f"{status['max_trades_per_symbol']}",
                )
                limits_hit = status["limits_hit"]
                limits_style = "bold red" if limits_hit else "bold green"
                table.add_row(
                    "Limits Hit",
                    f"[{limits_style}]{'YES' if limits_hit else 'NO'}[/{limits_style}]",
                )
                console.print()
                console.print(table)
                console.print()

            elif command == "drift":
                from engine.drift import print_drift_report

                print_drift_report()

            elif command == "pairs":
                from engine.pairs import print_pairs_scan, analyze_pair

                if len(args) >= 2:
                    result = analyze_pair(args[0].upper(), args[1].upper())
                    result.print_analysis()
                else:
                    syms = [a.upper() for a in args] if args else None
                    print_pairs_scan(syms)

            elif command == "audit":
                if not args:
                    console.print("[red]Usage: audit <trade_id>[/red]")
                else:
                    from engine.audit import print_audit

                    print_audit(args[0])

            elif command == "profile":
                from engine.profile import print_profile

                print_profile()

            elif command == "deep-analyze":
                from engine.output import parse_output_flags, handle_output_flags

                clean_args, wants_pdf, wants_explain, _ = parse_output_flags(args)
                wants_risk_debate = "--risk-debate" in clean_args
                clean_args = [a for a in clean_args if a != "--risk-debate"]
                symbol = clean_args[0].upper() if clean_args else ""
                inline_context = " ".join(clean_args[1:]).strip() or None
                if not symbol:
                    console.print(
                        "[red]Usage: deep-analyze <SYMBOL> [context hints] [--risk-debate] [--pdf] [--explain][/red]"
                    )
                else:
                    agent = get_agent()
                    if inline_context:
                        console.print(f"[dim]  ◆ Context: {inline_context}[/dim]")
                    try:
                        from agent.deep_agent import DeepAnalyzer

                        deep = DeepAnalyzer(
                            registry=agent._registry,
                            llm_provider=agent._provider,
                            risk_debate=wants_risk_debate,
                            context=inline_context,
                        )
                        output = deep.analyze(symbol)
                        _last_output = output or ""
                        _last_command = f"Deep Analysis {symbol}"
                        if wants_pdf or wants_explain:
                            handle_output_flags(
                                output or "",
                                f"Deep Analysis {symbol}",
                                wants_pdf,
                                wants_explain,
                                llm_provider=agent._provider if wants_explain else None,
                            )
                    except Exception as e:
                        console.print(f"[red]Deep analysis failed:[/red] {e}")
                        console.print(
                            "[dim]This usually means the AI provider hit a rate limit or the symbol wasn't found.[/dim]"
                        )
                        console.print("[dim]Falling back to standard analysis...[/dim]")
                        agent.run_multi_agent_analysis(symbol)

            elif command == "persona":
                from app.commands.persona import run as persona_run

                agent = get_agent()
                persona_run(
                    args=args,
                    registry=getattr(agent, "_registry", None),
                    llm_provider=getattr(agent, "_provider", None),
                )

            elif command == "debate":
                from app.commands.persona import run_debate_command

                agent = get_agent()
                run_debate_command(
                    args=args,
                    registry=getattr(agent, "_registry", None),
                    llm_provider=getattr(agent, "_provider", None),
                )

            elif command == "quick":
                # Quick scan: single-agent, 1 LLM call, 3-5s
                # Usage: quick SYMBOL [SYMBOL2 ...]

                if not args:
                    console.print("[dim]Usage: quick <SYMBOL> [SYMBOL2 ...][/dim]")
                    console.print("[dim]  quick INFY          → fast BUY/SELL/HOLD[/dim]")
                    console.print("[dim]  quick INFY TCS HDFC → scan multiple symbols[/dim]")
                else:
                    from agent.quick_scan import QuickScanner
                    from rich.table import Table

                    agent = get_agent()
                    scanner = QuickScanner(
                        provider=getattr(agent, "_provider", None),
                        registry=getattr(agent, "_registry", None),
                    )

                    symbols = [a.upper() for a in args if not a.startswith("-")]
                    if len(symbols) == 1:
                        # Single symbol — rich output
                        sym = symbols[0]
                        console.print(f"\n  [dim]Scanning {sym}...[/dim]")
                        result = scanner.scan(sym)
                        if result.error:
                            console.print(f"  [red]Error:[/red] {result.error}")
                        else:
                            v_style = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(
                                result.verdict, "white"
                            )
                            console.print(
                                f"\n  [bold]{result.symbol}[/bold] · "
                                f"[{v_style}]{result.verdict}[/{v_style}] "
                                f"({result.confidence}%) · ₹{result.ltp:,.2f}"
                            )
                            for reason in result.reasons:
                                console.print(f"    • {reason}")
                            if result.entry:
                                console.print(
                                    f"\n  Entry: ₹{result.entry:,.2f}  "
                                    f"SL: ₹{result.sl:,.2f}  "
                                    f"Target: ₹{result.target:,.2f}"
                                    if result.sl and result.target
                                    else f"\n  Entry: ₹{result.entry:,.2f}"
                                )
                            console.print(f"  [dim]⏱ {result.elapsed_ms}ms · 1 LLM call[/dim]\n")
                    else:
                        # Multi-symbol — table output
                        console.print(f"\n  [dim]Quick-scanning {len(symbols)} symbols...[/dim]")
                        table = Table(show_header=True, header_style="bold cyan", box=None)
                        table.add_column("Symbol", style="bold", width=10)
                        table.add_column("Price", justify="right", width=10)
                        table.add_column("Verdict", width=8)
                        table.add_column("Conf", justify="right", width=6)
                        table.add_column("Top Reason", width=50)
                        table.add_column("⏱", justify="right", width=6)

                        for sym in symbols:
                            result = scanner.scan(sym)
                            v_style = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(
                                result.verdict, "white"
                            )
                            table.add_row(
                                result.symbol,
                                f"₹{result.ltp:,.0f}" if result.ltp else "-",
                                f"[{v_style}]{result.verdict}[/{v_style}]",
                                f"{result.confidence}%",
                                result.reasons[0] if result.reasons else "-",
                                f"{result.elapsed_ms}ms",
                            )
                        console.print(table)
                        console.print()

            elif command == "telegram":
                sub = args[0].lower() if args else ""

                # ── telegram setup — full guided wizard ──────
                if sub == "setup":
                    try:
                        from bot.telegram_bot import run_setup_wizard

                        run_setup_wizard()
                    except Exception as e:
                        console.print(f"[red]Telegram setup failed:[/red] {e}")
                        console.print(
                            "[dim]Make sure you have a bot token from @BotFather on Telegram.[/dim]"
                        )
                        console.print("[dim]Run: credentials set TELEGRAM_BOT_TOKEN[/dim]")
                    continue

                # ── telegram — start bot in background ───────
                try:
                    import telegram as _tg_check  # noqa: F401
                except ImportError:
                    console.print(
                        "[red]python-telegram-bot not installed.[/red]\n"
                        "[dim]Run: pip install python-telegram-bot[/dim]"
                    )
                    continue

                try:
                    from bot.telegram_bot import _get_bot_token

                    _get_bot_token()
                except RuntimeError as e:
                    console.print(
                        f"[red]{e}[/red]\n"
                        "[dim]Run [bold]telegram setup[/bold] for step-by-step guided setup.[/dim]"
                    )
                    continue

                try:
                    from bot.telegram_bot import run_bot_background, _load_chat_id

                    run_bot_background()
                    chat_id = _load_chat_id()
                    if not chat_id:
                        console.print(
                            "[green]Telegram bot started.[/green]\n"
                            "[yellow]⚠  No chat connected yet.[/yellow]\n"
                            "[dim]Send /start to your bot on Telegram to enable push notifications.\n"
                            "Or run [bold]telegram setup[/bold] for the full guided flow.[/dim]"
                        )
                    else:
                        console.print(
                            "[green]✓ Telegram bot started.[/green]\n"
                            "[dim]Alerts and signals will be pushed automatically.[/dim]"
                        )
                except Exception as e:
                    console.print(f"[red]Telegram bot failed:[/red] {e}")
                    console.print(
                        "[dim]Run 'telegram setup' for guided configuration, or check your bot token.[/dim]"
                    )

            # ── Trade execution (live or paper, auto-detected) ───
            elif command in ("execute", "paper-execute"):
                if not _last_trade_plans:
                    console.print(
                        "[dim]No trade plans available. Run 'analyze <SYMBOL>' first.[/dim]"
                    )
                else:
                    profile_name = args[0].lower() if args else "neutral"
                    if profile_name not in ("aggressive", "neutral", "conservative"):
                        console.print("[red]Usage: execute [aggressive|neutral|conservative][/red]")
                    else:
                        plan = _last_trade_plans.get(profile_name)
                        if plan:
                            from engine.trade_executor import execute_trade_plan

                            execute_trade_plan(plan, broker)
                        else:
                            console.print(
                                f"[dim]No {profile_name} plan available (verdict may be HOLD).[/dim]"
                            )

            # ── Exports management ────────────────────────────────
            elif command == "exports":
                from engine.output import list_exports, open_export, clear_exports

                sub = args[0].lower() if args else ""

                if sub == "open" and len(args) >= 2:
                    fname = args[1]
                    if open_export(fname):
                        console.print(f"[green]Opened:[/green] {fname}")
                    else:
                        console.print(f"[red]File not found:[/red] {fname}")

                elif sub == "clear":
                    days = 30
                    for i, a in enumerate(args):
                        if a == "--older-than" and i + 1 < len(args):
                            raw = args[i + 1].rstrip("d")
                            try:
                                days = int(raw)
                            except ValueError:
                                pass
                    deleted = clear_exports(days)
                    console.print(f"[dim]Deleted {deleted} export(s) older than {days} days.[/dim]")

                else:
                    exports = list_exports()
                    if not exports:
                        console.print("[dim]No saved exports yet. Use --pdf on any command.[/dim]")
                    else:
                        from rich.table import Table as RichTable

                        tbl = RichTable(
                            title="Saved Exports",
                            caption="~/.trading_platform/exports/",
                            show_lines=False,
                        )
                        tbl.add_column("File", style="cyan")
                        tbl.add_column("Size", justify="right")
                        tbl.add_column("Date", style="dim")

                        total_kb = 0.0
                        for ex in exports:
                            total_kb += ex["size_kb"]
                            size_str = (
                                f"{ex['size_kb']:.0f} KB"
                                if ex["size_kb"] < 1024
                                else f"{ex['size_kb'] / 1024:.1f} MB"
                            )
                            date_str = ex["modified"].strftime("%d %b %Y, %I:%M %p")
                            tbl.add_row(ex["name"], size_str, date_str)

                        total_str = (
                            f"{total_kb:.0f} KB" if total_kb < 1024 else f"{total_kb / 1024:.1f} MB"
                        )
                        tbl.caption = f"{len(exports)} files | {total_str} total | ~/.trading_platform/exports/"
                        console.print(tbl)

            # ── Post-processing commands (operate on previous output) ──
            elif command == "save-pdf":
                if not _last_output:
                    console.print("[dim]No previous output to save. Run a command first.[/dim]")
                else:
                    from engine.output import export_to_pdf, _archive_filename

                    _pdf_title = _last_command or "Trade CLI Output"
                    filepath = export_to_pdf(_last_output, title=_pdf_title)
                    if filepath:
                        console.print(f"[green]PDF saved:[/green] {filepath}")
                        console.print(
                            f"[dim]Archived:[/dim] ~/.trading_platform/exports/{_archive_filename(_pdf_title)}"
                        )

            elif command == "explain":
                if not _last_output:
                    console.print("[dim]No previous output to explain. Run a command first.[/dim]")
                else:
                    from engine.output import explain_simply

                    console.print()
                    console.rule("[bold green]Simple Explanation[/bold green]", style="green")
                    try:
                        agent = get_agent()
                        explanation = explain_simply(_last_output, llm_provider=agent._provider)
                    except Exception:
                        explanation = explain_simply(_last_output)
                        console.print(explanation, highlight=False)
                    console.rule(style="green")
                    _last_output = _last_output + "\n\n" + explanation

            elif command == "explain-save":
                if not _last_output:
                    console.print("[dim]No previous output. Run a command first.[/dim]")
                else:
                    from engine.output import explain_simply, export_to_pdf, _archive_filename

                    # Step 1: Explain
                    console.print()
                    console.rule("[bold green]Simple Explanation[/bold green]", style="green")
                    try:
                        agent = get_agent()
                        explanation = explain_simply(_last_output, llm_provider=agent._provider)
                    except Exception:
                        explanation = explain_simply(_last_output)
                        console.print(explanation, highlight=False)
                    console.rule(style="green")
                    # Step 2: Combine and save PDF
                    combined = _last_output + "\n\n--- SIMPLE EXPLANATION ---\n\n" + explanation
                    _pdf_title = _last_command or "Trade CLI Report"
                    filepath = export_to_pdf(combined, title=_pdf_title)
                    if filepath:
                        console.print(f"\n[green]PDF saved (with explanation):[/green] {filepath}")
                        console.print(
                            f"[dim]Archived:[/dim] ~/.trading_platform/exports/{_archive_filename(_pdf_title)}"
                        )
                    _last_output = combined

            elif command == "mtf":
                if not args:
                    console.print("[red]Usage: mtf <SYMBOL>   e.g. mtf RELIANCE[/red]")
                else:
                    from analysis.multi_timeframe import multi_timeframe_analysis

                    result = multi_timeframe_analysis(args[0].upper())
                    result.print_analysis()

            elif command == "walkforward":
                if not args:
                    console.print("[red]Usage: walkforward SYMBOL [strategy] [--period 3y][/red]")
                else:
                    from engine.backtest import walk_forward_test

                    sym = args[0].upper()
                    strat = args[1].lower() if len(args) > 1 else "rsi"
                    period = "3y"
                    if "--period" in args:
                        idx = args.index("--period")
                        if idx + 1 < len(args):
                            period = args[idx + 1]
                    console.print(f"[dim]Running walk-forward: {sym} / {strat} / {period}...[/dim]")
                    try:
                        result = walk_forward_test(sym, strat, total_period=period)
                        result.print_summary()
                    except Exception as e:
                        console.print(f"[red]Walk-forward failed:[/red] {e}")
                        console.print(
                            "[dim]Ensure the symbol has enough historical data for the requested period.[/dim]"
                        )

            elif command == "events":
                from engine.event_strategies import print_event_strategies

                days = int(args[0]) if args else 7
                print_event_strategies(days)

            elif command == "backtest":
                _handle_backtest_command(args)

            elif command == "strategy":
                from app.commands.strategy import run as strategy_run

                strategy_run(args)

            elif command == "persona":
                from app.commands.persona import run as persona_run
                from agent.tools import build_registry
                from agent.core import get_provider

                _persona_registry = build_registry()
                _persona_provider = get_provider(registry=_persona_registry)
                persona_run(
                    args,
                    registry=_persona_registry,
                    llm_provider=_persona_provider,
                )

            elif command == "debate":
                from app.commands.persona import run_debate_command
                from agent.tools import build_registry
                from agent.core import get_provider

                _debate_registry = build_registry()
                _debate_provider = get_provider(registry=_debate_registry)
                run_debate_command(
                    args,
                    registry=_debate_registry,
                    llm_provider=_debate_provider,
                )

            elif command == "search":
                query = " ".join(args).strip()
                if not query:
                    console.print(
                        "[dim]Usage: search <query>\n"
                        "  Examples:\n"
                        "    search RELIANCE BUY\n"
                        '    search "iron condor"\n'
                        "    search verdict:STRONG_BUY[/dim]"
                    )
                else:
                    from engine.search import analysis_search, print_search_results

                    analysis_search.index_from_memory()
                    results = analysis_search.search(query)
                    print_search_results(results, query)

            elif command == "whatif":
                _handle_whatif_command(args)

            elif command == "ai":
                from engine.output import parse_output_flags, handle_output_flags

                clean_args, wants_pdf, wants_explain, _ = parse_output_flags(args)
                message = " ".join(clean_args).strip()
                if not message:
                    console.print(
                        "[dim]Usage: ai <your message> [--pdf] [--explain]\n"
                        "  Follow-ups remember context. Use [bold]clear[/bold] to start fresh.[/dim]"
                    )
                else:
                    agent = get_agent()
                    output = agent.chat(message)
                    _last_output = output or ""
                    _last_command = f"AI: {message[:40]}"
                    if wants_pdf or wants_explain:
                        handle_output_flags(
                            output or "",
                            "AI Chat",
                            wants_pdf,
                            wants_explain,
                            llm_provider=agent._provider if wants_explain else None,
                        )

            # ── Trading harness (free-form agentic loop) ──────────
            elif command == "harness":
                query = " ".join(args).strip()
                if not query:
                    console.print(
                        "[dim]Usage: harness <your question>\n"
                        "  Examples:\n"
                        "    harness Should I buy RELIANCE? I have ₹2L\n"
                        "    harness What's the market doing today?\n"
                        "    harness Check my portfolio Greeks and suggest hedges[/dim]"
                    )
                else:
                    from agent.harness import run as harness_run

                    output = harness_run(query, broker=broker)
                    _last_output = output or ""
                    _last_command = f"Harness: {query[:40]}"

            elif command == "provider":
                if args and args[0].lower() == "setup":
                    # Re-run the full interactive AI provider wizard
                    agent = get_agent()
                    agent.run_setup_wizard()
                elif args:
                    new_provider = args[0].lower()
                    new_model = args[1] if len(args) > 1 else None
                    if new_provider not in ALL_PROVIDERS:
                        console.print(
                            f"[red]Unknown provider '{new_provider}'.[/red] "
                            f"Valid: {', '.join(ALL_PROVIDERS)}\n"
                            f"  Or run [cyan]provider setup[/cyan] for the guided wizard."
                        )
                    else:
                        agent = get_agent()
                        agent.switch_provider(new_provider, new_model)
                else:
                    agent = get_agent()
                    agent.list_providers()

            elif command == "cancel":
                # cancel ORDER_ID  |  cancel all  |  cancel (shows open orders to pick)
                if not broker:
                    console.print("[red]No broker connected. Run: broker connect[/red]")
                else:
                    try:
                        _orders = broker.get_orders()
                        _open = [
                            o
                            for o in _orders
                            if o.status.upper()
                            in ("OPEN", "PENDING", "TRIGGER PENDING", "OPEN PENDING")
                        ]
                        if not _open:
                            console.print("[dim]No open orders to cancel.[/dim]")
                        elif args and args[0].lower() == "all":
                            from rich.prompt import Confirm as _Confirm

                            console.print(
                                f"  [yellow]Cancel all {len(_open)} open orders?[/yellow]"
                            )
                            if _Confirm.ask("  Confirm?", default=False):
                                for _o in _open:
                                    try:
                                        broker.cancel_order(_o.order_id)
                                        console.print(
                                            f"  [green]✓[/green] Cancelled {_o.symbol} {_o.order_id}"
                                        )
                                    except Exception as _e:
                                        console.print(f"  [red]✗[/red] Failed {_o.order_id}: {_e}")
                        elif args:
                            _oid = args[0]
                            try:
                                broker.cancel_order(_oid)
                                console.print(f"  [green]✓ Cancelled order {_oid}[/green]")
                            except Exception as _e:
                                console.print(f"  [red]Cancel failed:[/red] {_e}")
                        else:
                            # Show open orders and let user pick
                            for _i, _o in enumerate(_open, 1):
                                _side_color = "green" if _o.transaction_type == "BUY" else "red"
                                console.print(
                                    f"  {_i}. [{_side_color}]{_o.transaction_type}[/{_side_color}]"
                                    f" {_o.quantity}× {_o.symbol} @ ₹{_o.price or 'MKT'}"
                                    f"  [dim]{_o.order_id}[/dim]"
                                )
                            from rich.prompt import Prompt as _Prompt

                            _pick = _Prompt.ask("  Cancel which? [number/all/0]", default="0")
                            if _pick == "0":
                                console.print("  [dim]Cancelled.[/dim]")
                            elif _pick.lower() == "all":
                                for _o in _open:
                                    try:
                                        broker.cancel_order(_o.order_id)
                                        console.print(f"  [green]✓[/green] Cancelled {_o.symbol}")
                                    except Exception as _e:
                                        console.print(f"  [red]✗[/red] {_e}")
                            else:
                                try:
                                    _idx = int(_pick) - 1
                                    _o = _open[_idx]
                                    broker.cancel_order(_o.order_id)
                                    console.print(
                                        f"  [green]✓ Cancelled {_o.symbol} {_o.order_id}[/green]"
                                    )
                                except (ValueError, IndexError):
                                    console.print("[red]Invalid selection.[/red]")
                                except Exception as _e:
                                    console.print(f"  [red]Cancel failed:[/red] {_e}")
                    except Exception as e:
                        console.print(f"[red]Error:[/red] {e}")

            elif command in ("buy", "sell"):
                # Quick order: buy YESBANK 1 15 | sell RELIANCE 5 | buy INFY 5% | buy INFY 5% 1400
                # Format: buy SYMBOL QTY|PCT% [LIMIT_PRICE]
                import os as _os

                if not args:
                    console.print(f"[dim]Usage: {command} SYMBOL QTY [LIMIT_PRICE][/dim]")
                    console.print(f"[dim]  {command} YESBANK 1 15   → limit order at ₹15[/dim]")
                    console.print(f"[dim]  {command} YESBANK 1      → market order[/dim]")
                    console.print(
                        f"[dim]  {command} INFY 5%        → 5% of capital at market[/dim]"
                    )
                    console.print(
                        f"[dim]  {command} INFY 5% 1400   → 5% of capital, limit ₹1400[/dim]"
                    )
                elif not broker:
                    console.print("[red]No broker connected. Run: broker connect[/red]")
                else:
                    _sym = args[0].upper()
                    _raw_qty = args[1] if len(args) > 1 else "1"
                    _limit = float(args[2]) if len(args) > 2 else None
                    # Resolve percentage sizing
                    try:
                        from engine.trade_executor import (
                            parse_qty_or_pct,
                            size_by_pct,
                            get_trading_capital,
                        )

                        _qty_val, _is_pct = parse_qty_or_pct(_raw_qty)
                        if _is_pct:
                            _capital = get_trading_capital()
                            _qty = size_by_pct(_sym, _qty_val, _capital, limit_price=_limit)
                            console.print(
                                f"  [dim]{_qty_val:.1f}% of ₹{_capital:,.0f} → [bold]{_qty}[/bold] shares[/dim]"
                            )
                        else:
                            _qty = int(_qty_val)
                    except ValueError as _e:
                        console.print(f"[red]Sizing error:[/red] {_e}")
                        continue
                    _mode = _os.environ.get("TRADING_MODE", "PAPER")
                    _side = "BUY" if command == "buy" else "SELL"
                    _otype = "LIMIT" if _limit else "MARKET"
                    _price_str = f"₹{_limit}" if _limit else "MARKET"

                    console.print(
                        f"\n  [bold]{_side} {_qty} × {_sym}[/bold] @ {_price_str}"
                        f"  [{'bold red' if _mode == 'LIVE' else 'green'}]({_mode})[/{'bold red' if _mode == 'LIVE' else 'green'}]"
                    )

                    from rich.prompt import Confirm as _Confirm

                    if _mode == "LIVE":
                        console.print(
                            "  [red]⚠  This will place a REAL order with real money.[/red]"
                        )
                    if _Confirm.ask("  Confirm?", default=False):
                        try:
                            from brokers.base import OrderRequest as _OR

                            _req = _OR(
                                symbol=_sym,
                                exchange="NSE",
                                transaction_type=_side,
                                quantity=_qty,
                                order_type=_otype,
                                price=_limit,
                                product="CNC",
                            )
                            _resp = broker.place_order(_req)
                            if _resp.status in ("OPEN", "COMPLETE", "PUT ORDER REQ RECEIVED"):
                                console.print(
                                    f"  [green]✓ Order placed![/green]  ID: {_resp.order_id}  Status: {_resp.status}"
                                )
                                if _resp.message:
                                    console.print(f"    {_resp.message}")
                            else:
                                console.print(
                                    f"  [red]✗ Order {_resp.status}:[/red] {_resp.message}"
                                )
                        except Exception as e:
                            console.print(f"  [red]Order error:[/red] {e}")
                    else:
                        console.print("  [dim]Cancelled.[/dim]")

            elif command == "trade":
                sym = args[0].upper() if args else None
                view = args[1].upper() if len(args) > 1 else None
                try:
                    from app.commands.trade import run as trade_run

                    trade_run(symbol=sym, view=view)
                except KeyboardInterrupt:
                    console.print("\n[dim]Trade cancelled.[/dim]")
                except Exception as e:
                    console.print(f"[red]Trade builder error:[/red] {e}")
                    console.print(
                        "[dim]Make sure you're logged in to a broker. Try: logout → login[/dim]"
                    )

            elif command in ("paper", "mode"):
                _cmd_toggle_paper(args)

            elif command == "tui":
                console.print("[dim]Launching TUI...[/dim]")
                from ui.app import run_tui

                run_tui()
                console.print("[dim]Back in REPL mode.[/dim]")

            elif command == "web":
                port = int(args[0]) if args and args[0].isdigit() else 8765
                _cmd_web(port)

            elif command == "credentials":
                from config.credentials import cmd_credentials

                cmd_credentials(args)

            else:
                console.print(
                    f"[red]Unknown command:[/red] [bold]{command}[/bold]  "
                    f"(type [bold]help[/bold] for available commands)"
                )

        except KeyboardInterrupt:
            console.print("\n[dim]Command interrupted.[/dim]")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            console.print(
                "[dim]If this keeps happening, try: logout → login, or run with DEBUG=1 for details.[/dim]"
            )
            import os

            if os.environ.get("DEBUG"):
                import traceback

                console.print(f"[dim]{traceback.format_exc()}[/dim]")

        # ── Global PDF export (runs after every command) ─────
        if _global_pdf:
            pdf_content = ""
            _pdf_title = _last_command or f"{command} {' '.join(args)}".strip()

            if _last_output and _last_output != _pre_pdf_output:
                # Command updated _last_output (analyze, deep-analyze, ai, backtest)
                pdf_content = _last_output
            else:
                # Command only did console.print() — re-capture with Rich
                try:
                    with console.capture() as _cap:
                        exec_parts = raw.replace("--pdf", "").replace("--save-pdf", "").split()
                        exec_cmd = exec_parts[0].lower() if exec_parts else ""
                        exec_args = exec_parts[1:]
                        if exec_cmd == "funds" and broker:
                            cmd_funds(broker)
                        elif exec_cmd == "holdings" and broker:
                            cmd_holdings(broker)
                        elif exec_cmd == "positions" and broker:
                            cmd_positions(broker)
                        elif exec_cmd == "orders" and broker:
                            cmd_orders(broker)
                        elif exec_cmd in ("alerts",) or (
                            exec_cmd == "alert" and (not exec_args or exec_args[0] == "list")
                        ):
                            from engine.alerts import alert_manager

                            alert_manager.list_alerts()
                        elif exec_cmd == "memory":
                            from engine.memory import trade_memory

                            if not exec_args:
                                trade_memory.print_recent()
                            elif exec_args[0] == "stats":
                                trade_memory.print_stats()
                        elif exec_cmd == "flows":
                            from market.flow_intel import get_flow_intel

                            get_flow_intel()
                        elif exec_cmd == "macro":
                            from market.macro import print_macro_snapshot

                            if exec_args:
                                print_macro_snapshot(exec_args[0].upper())
                            else:
                                print_macro_snapshot()
                    pdf_content = _cap.get()
                    _pdf_title = _pdf_title or f"{exec_cmd} output"
                except Exception:
                    pdf_content = ""

            if pdf_content.strip():
                from engine.output import export_to_pdf, _archive_filename

                filepath = export_to_pdf(pdf_content, title=_pdf_title)
                if filepath:
                    console.print(f"\n[green]PDF saved:[/green] {filepath}")
                    console.print(
                        f"[dim]Archived:[/dim] ~/.trading_platform/exports/{_archive_filename(_pdf_title)}"
                    )
            else:
                console.print("[dim]No output to save as PDF.[/dim]")
