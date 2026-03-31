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
    "ai", "alert", "alerts", "audit", "backtest", "clear",
    "deep-analyze", "drift",
    "earnings", "events", "flows", "greeks", "macro", "memory",
    "pairs", "patterns", "profile", "provider", "risk-report",
    "telegram", "tui", "walkforward", "web", "whatif",
    "credentials",
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
        host       = "0.0.0.0",
        port       = port,
        log_level  = "warning",   # quiet — the REPL already has UI
    )
    console.print("[dim]\nWeb server stopped. Back in REPL.[/dim]\n")


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
    clear            Clear AI conversation history (start fresh)
    provider         Show / switch AI provider (anthropic / openai / gemini / …)

  [bold]Alerts[/bold]
    alert SYMBOL above PRICE          Set a price alert (e.g. alert NIFTY above 22500)
    alert SYMBOL below PRICE          Set a price alert (e.g. alert RELIANCE below 2600)
    alert SYMBOL RSI above 70         Set a technical alert
    alert RELIANCE above 2800 AND RSI above 70   Conditional alert (AND)
    alert list / alerts               List all active alerts
    alert remove ID                   Remove an alert by ID
    greeks                            Portfolio Greeks (net Delta, Theta, Vega)

  [bold]India Intelligence[/bold]
    earnings [SYM...]                 Upcoming quarterly results calendar
    flows                             FII/DII flow analysis with signals
    events [days]                     Event-driven strategy recommendations

  [bold]Backtest & Simulation[/bold]
    backtest SYMBOL [strategy]        Backtest a strategy (rsi, ma, macd, bb)
    backtest RELIANCE rsi             RSI overbought/oversold (30/70)
    backtest RELIANCE ma 20 50        EMA crossover strategy
    whatif nifty -3                   What if NIFTY drops 3%?
    whatif RELIANCE -10               What if RELIANCE drops 10%?

  [bold]Memory & Patterns[/bold]
    memory                            Show recent trade analyses
    memory stats                      Performance statistics
    memory <SYMBOL>                   Past analyses for a symbol
    memory outcome <ID> WIN|LOSS [pnl]  Record trade outcome
    patterns                          Show active India market patterns

  [bold]Interface[/bold]
    tui              Launch split-panel Textual TUI
    web [PORT]       Start web UI server (browser-based broker login, default port 8765)
    paper            Show paper-trading mode status

  [bold]Setup[/bold]
    credentials           List which credentials are stored and their status
    credentials setup     Interactive wizard to configure all API keys
    credentials set KEY   Update a single credential
    credentials delete KEY Remove a key from the OS keychain

  [bold]Other[/bold]
    quit / exit      Exit the platform
""")


# ── Alert command handler ──────────────────────────────────────

def _handle_backtest_command(args: list[str]) -> None:
    """Handle: backtest SYMBOL [strategy] [args...] [--period 2y]"""
    if not args:
        console.print(
            "[red]Usage: backtest SYMBOL [strategy] [args][/red]\n"
            "[dim]  backtest RELIANCE rsi              RSI(30/70) strategy\n"
            "  backtest RELIANCE ma 20 50          EMA crossover\n"
            "  backtest RELIANCE macd              MACD signal crossover\n"
            "  backtest RELIANCE bb                Bollinger Bands\n"
            "  Strategies: rsi, ma, ema, macd, bb/bollinger[/dim]"
        )
        return

    from engine.backtest import run_backtest

    symbol = args[0].upper()
    strategy_name = args[1].lower() if len(args) > 1 else "rsi"
    strategy_args = args[2:] if len(args) > 2 else []

    # Check for --period flag
    period = "1y"
    if "--period" in args:
        idx = args.index("--period")
        if idx + 1 < len(args):
            period = args[idx + 1]
            strategy_args = [a for a in strategy_args if a not in ("--period", period)]

    console.print(f"\n[dim]Running backtest: {symbol} / {strategy_name} / {period}...[/dim]")

    try:
        result = run_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            strategy_args=strategy_args,
            period=period,
        )
        result.print_summary()
        result.print_trades(10)
    except Exception as e:
        console.print(f"[red]Backtest failed: {e}[/red]")


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
    """Handle memory commands: memory [stats|list|<symbol>|outcome <id> <result>]"""
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
                verdict_style = {"BUY": "green", "STRONG_BUY": "bold green",
                                 "SELL": "red", "STRONG_SELL": "bold red"}.get(r.verdict, "yellow")
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
            "BULLISH": "green", "BEARISH": "red",
            "VOLATILE": "yellow", "NEUTRAL": "white",
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
                conditions.append({
                    "condition_type": "TECHNICAL",
                    "indicator": tokens[0],
                    "condition": tokens[1],
                    "threshold": float(tokens[2]),
                })
            elif len(tokens) >= 2:
                # PRICE: above 2800
                cond = tokens[0] if tokens[0] in ("ABOVE", "BELOW") else tokens[0]
                conditions.append({
                    "condition_type": "PRICE",
                    "condition": cond,
                    "threshold": float(tokens[1] if tokens[0] in ("ABOVE", "BELOW") else tokens[-1]),
                })

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
            symbol, indicator, condition, threshold,
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
        history    = FileHistory(history_path),
        completer  = WordCompleter(COMMANDS, ignore_case=True),
        style      = STYLE,
    )

    # Start background alert poller (daemon thread, checks every 60s)
    from engine.alerts import alert_manager
    alert_manager.start_realtime()  # WebSocket ticks → instant alerts (falls back to 60s polling)

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
                # Clean up background threads
                try:
                    from market.websocket import ws_manager
                    ws_manager.stop()
                except Exception:
                    pass
                try:
                    from engine.alerts import alert_manager
                    alert_manager.stop_polling()
                except Exception:
                    pass
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
                try:
                    cmd_funds(broker)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]\n[dim]Fyers funds API may be slow. Try again during market hours.[/dim]")

            # ── Portfolio (single-broker raw views) ───────────
            elif command == "holdings":
                try:
                    cmd_holdings(broker)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

            elif command == "positions":
                try:
                    cmd_positions(broker)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

            elif command == "orders":
                try:
                    cmd_orders(broker)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

            # ── Portfolio (unified multi-broker view) ─────────
            elif command == "portfolio":
                try:
                    from engine.portfolio import get_multi_broker_summary
                    _cmd_portfolio(get_multi_broker_summary())
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

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
                    agent.run_multi_agent_analysis(symbol)

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

            elif command == "flows":
                from market.flow_intel import print_flow_report
                print_flow_report()

            elif command == "greeks":
                from engine.portfolio import print_portfolio_greeks
                print_portfolio_greeks()

            elif command == "macro":
                from market.macro import print_macro_snapshot
                sym = args[0].upper() if args else None
                print_macro_snapshot(sym)

            elif command == "risk-report":
                from engine.risk_metrics import print_risk_report
                print_risk_report()

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
                symbol = args[0].upper() if args else ""
                if not symbol:
                    console.print("[red]Usage: deep-analyze <SYMBOL>   e.g. deep-analyze RELIANCE[/red]")
                else:
                    agent = get_agent()
                    try:
                        from agent.deep_agent import DeepAnalyzer
                        deep = DeepAnalyzer(
                            registry=agent._registry,
                            llm_provider=agent._provider,
                        )
                        deep.analyze(symbol)
                    except Exception as e:
                        console.print(f"[red]Deep analysis failed: {e}[/red]")
                        console.print("[dim]Falling back to standard analysis...[/dim]")
                        agent.run_multi_agent_analysis(symbol)

            elif command == "telegram":
                # Pre-validate before starting background thread
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
                    console.print(f"[red]{e}[/red]")
                    continue
                try:
                    from bot.telegram_bot import run_bot_background
                    run_bot_background()
                    console.print(
                        "[green]Telegram bot started in background.[/green]\n"
                        "[dim]Send /start to your bot on Telegram to begin.[/dim]\n"
                        "[dim]Alerts will be pushed automatically.[/dim]"
                    )
                except Exception as e:
                    console.print(f"[red]Telegram bot failed: {e}[/red]")

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
                        console.print(f"[red]Walk-forward failed: {e}[/red]")

            elif command == "events":
                from engine.event_strategies import print_event_strategies
                days = int(args[0]) if args else 7
                print_event_strategies(days)

            elif command == "backtest":
                _handle_backtest_command(args)

            elif command == "whatif":
                _handle_whatif_command(args)

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

        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
