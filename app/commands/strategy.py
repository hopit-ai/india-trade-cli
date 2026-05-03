"""
app/commands/strategy.py
────────────────────────
Interactive strategy builder command.

Subcommands:
  strategy new [description] [--simple]                       — AI-guided strategy creation
  strategy list                                               — show saved strategies
  strategy backtest <name> [--period 2y]                      — re-backtest a saved strategy
  strategy run <name> [symbol] [--paper]                      — generate signal + paper trade
  strategy show <name>                                        — view code + metadata
  strategy delete <name>                                      — remove a saved strategy
  strategy library [category] [--type options|technical|all]  — browse strategy template library
  strategy learn <name>                                       — detailed explanation of a template
  strategy use <name> SYMBOL [--lots N] [--dte N]             — apply a template with live data
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.prompt import Confirm

console = Console()

# Tracks the last symbol the user explicitly worked with (set by quote/analyse/backtest commands)
_last_symbol: str = ""


def get_last_symbol() -> str:
    """Return the last symbol the user worked with, or empty string."""
    return _last_symbol


def set_last_symbol(symbol: str) -> None:
    """Record the most recently used symbol."""
    global _last_symbol
    if symbol:
        _last_symbol = symbol.upper()


def _resolve_symbol(from_payload: str | None = None, from_args: str | None = None) -> str:
    """
    Resolve which symbol to use, in priority order:
    1. Explicitly provided in args
    2. Symbol the LLM extracted from the conversation
    3. Last symbol the user worked with
    4. Prompt the user interactively
    """
    from rich.prompt import Prompt

    if from_args:
        return from_args.upper()
    if from_payload and from_payload.upper() not in ("", "TICKER_USER_MENTIONED", "SYMBOL"):
        return from_payload.upper()
    if _last_symbol:
        return _last_symbol
    return Prompt.ask("Which symbol should we backtest this on? (e.g. INFY, TCS)").upper()


def run(args: list[str]) -> None:
    """Main dispatcher for the strategy command."""
    sub = args[0].lower() if args else ""

    if sub == "new":
        _cmd_new(args[1:])
    elif sub == "list" or not sub:
        _cmd_list()
    elif sub == "backtest":
        _cmd_backtest(args[1:])
    elif sub == "run":
        _cmd_run(args[1:])
    elif sub == "show":
        _cmd_show(args[1:])
    elif sub == "delete":
        _cmd_delete(args[1:])
    elif sub == "library":
        _cmd_library(args[1:])
    elif sub == "learn":
        _cmd_learn(args[1:])
    elif sub == "use":
        _cmd_use(args[1:])
    elif sub == "export":
        _cmd_export(args[1:])
    else:
        console.print(
            "[dim]Usage:\n"
            "  strategy new [description] [--simple]                       Create a new strategy\n"
            "  strategy list                                                List saved strategies\n"
            "  strategy backtest <name> [--period 2y]                       Re-backtest\n"
            "  strategy run <name> [symbol] [--paper]                       Generate signal\n"
            "  strategy show <name>                                         View code\n"
            "  strategy delete <name>                                       Delete\n"
            "  strategy library [category] [--type options|technical|all]  Browse templates\n"
            "  strategy learn <name>                                        Explain a template\n"
            "  strategy use <name> SYMBOL [--lots N] [--dte N]              Apply template\n"
            "  strategy export <name> --pine                                Export to Pine Script[/dim]"
        )


def _force_generate(agent) -> str:
    """Send an explicit prompt that forces the LLM to output code, not call tools."""
    return agent.chat(
        "STOP calling tools. Do NOT fetch any more data. You have all the information you need.\n\n"
        "Generate the Python strategy code NOW and output it in this exact format:\n\n"
        "%%%STRATEGY_COMPLETE%%%\n"
        '{"code": "...python code...", "name": "snake_case_name", '
        '"description": "one line", "symbol": "SYMBOL", "parameters": {}}\n\n'
        "The code must:\n"
        "- Subclass Strategy from engine.backtest\n"
        "- For SINGLE-SYMBOL: generate_signals returns pd.Series of -1/0/1\n"
        "- For PAIRS/MULTI-SYMBOL: generate_signals returns pd.DataFrame with one column per symbol\n"
        "  Values: 1=LONG, -1=SHORT, 0=FLAT. Use `from market.history import get_ohlcv` for other symbol data.\n"
        "- Use signals[mask] = 1 (boolean indexing), NOT signals = 1\n"
        "- Have default values for all __init__ parameters\n\n"
        "Output the %%%STRATEGY_COMPLETE%%% block right now."
    )


# ── strategy new ─────────────────────────────────────────────


def _cmd_new(args: list[str]) -> None:
    """AI-guided interview -> code generation -> backtest -> save."""
    from agent.core import get_agent
    from agent.prompts import STRATEGY_BUILDER_PROMPT, STRATEGY_BUILDER_SIMPLE_PROMPT
    from engine.strategy_builder import (
        extract_strategy_payload,
        build_and_test,
        strategy_store,
        validate_strategy_code,
        COMPLETION_MARKER,
    )
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory

    simple_mode = "--simple" in args
    clean_args = [a for a in args if a != "--simple"]
    initial_desc = " ".join(clean_args).strip()

    prompt_text = STRATEGY_BUILDER_SIMPLE_PROMPT if simple_mode else STRATEGY_BUILDER_PROMPT

    console.print("\n[bold cyan]━━━ Strategy Builder ━━━[/bold cyan]")
    if simple_mode:
        console.print("[dim]Simple mode: everything explained in plain language[/dim]")
    console.print(
        "[dim]Describe your strategy idea and the AI will guide you through building it.[/dim]"
    )
    console.print(
        "[dim]Type [bold]done[/bold] to finish early, [bold]cancel[/bold] to abort.[/dim]\n"
    )

    agent = get_agent()

    # Isolate the strategy builder in a clean conversation context.
    # Save the main conversation history and restore it when done.
    _saved_history = list(agent._history)
    agent._history = []

    # Inject the strategy builder system prompt as the first message
    first_message = prompt_text + "\n\n"
    if initial_desc:
        first_message += (
            f"The user wants to build this strategy: {initial_desc}\n\n"
            "IMPORTANT: Do NOT call any tools yet. First confirm the strategy type and ask which "
            "symbol/stock they want to trade. Only fetch data once the user has named a symbol."
        )
    else:
        first_message += (
            "The user wants to build a custom strategy.\n\n"
            "IMPORTANT: Do NOT call any tools yet. Start by asking:\n"
            "1. What kind of strategy they have in mind (momentum, mean reversion, pairs, etc.)\n"
            "2. Which stock or index they want to trade\n"
            "Only begin fetching market data AFTER the user has named a specific symbol."
        )

    # Run the multi-turn interview
    interview_session = PromptSession(history=InMemoryHistory())
    max_turns = 20
    strategy_payload = None

    consecutive_no_marker = 0  # track turns where LLM should have generated but didn't

    for turn in range(max_turns):
        if turn == 0:
            response = agent.chat(first_message)
        else:
            try:
                user_input = interview_session.prompt("you ❯ ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Strategy builder cancelled.[/yellow]")
                agent._history = _saved_history
                return

            if not user_input:
                continue
            if user_input.lower() == "cancel":
                console.print("[yellow]Strategy builder cancelled.[/yellow]")
                agent._history = _saved_history
                return
            if user_input.lower() in ("done", "generate", "build", "build it", "go"):
                response = _force_generate(agent)
            else:
                # Wrap the user input so the agent knows it MUST ask a follow-up question.
                # This prevents the agent from treating a tool call as a complete response.
                wrapped = (
                    f"User says: {user_input!r}\n\n"
                    "Use any tools you need to look up data for what the user mentioned. "
                    "If the symbol is not found or returns no data, tell the user clearly and ask "
                    "them to pick a different symbol (suggest NIFTY50 stocks like INFY, TCS, HDFC). "
                    "Do NOT retry a failed symbol. "
                    "After fetching data (or if no tool call is needed), ALWAYS end your response "
                    "with the next interview question to keep the conversation moving."
                )
                response = agent.chat(wrapped)

        # Check if the LLM signaled completion
        payload = extract_strategy_payload(response)
        if payload:
            strategy_payload = payload
            break

        # Detect if the LLM seems stuck (asking for quotes, not progressing)
        # After turn 6+, if the response doesn't contain a question mark, nudge it
        if turn >= 6:
            consecutive_no_marker += 1
            if consecutive_no_marker >= 2:
                console.print("\n[dim]Nudging AI to generate code...[/dim]")
                response = _force_generate(agent)
                payload = extract_strategy_payload(response)
                if payload:
                    strategy_payload = payload
                    break
                consecutive_no_marker = 0  # reset after one nudge attempt

    if not strategy_payload:
        # Last resort: one final hard push
        console.print("\n[dim]Final attempt to generate strategy...[/dim]")
        response = _force_generate(agent)
        strategy_payload = extract_strategy_payload(response)

    if not strategy_payload:
        agent._history = _saved_history
        console.print(
            "[yellow]Could not generate strategy code. Try again with [bold]strategy new[/bold].[/yellow]"
        )
        return

    # ── Validate and backtest ────────────────────────────────
    code = strategy_payload.get("code", "")
    name = strategy_payload.get("name", "custom_strategy")
    description = strategy_payload.get("description", "")
    symbol = _resolve_symbol(from_payload=strategy_payload.get("symbol"))
    parameters = strategy_payload.get("parameters", {})

    console.print(f"\n[bold]Generated strategy: [cyan]{name}[/cyan][/bold]")
    console.print(f"[dim]{description}[/dim]")

    # Validate with retry loop
    max_retries = 3
    for attempt in range(max_retries):
        ok, error = validate_strategy_code(code)
        if ok:
            break
        console.print(
            f"[yellow]Code validation failed (attempt {attempt + 1}/{max_retries}): {error}[/yellow]"
        )
        if attempt < max_retries - 1:
            console.print("[dim]Asking AI to fix...[/dim]")
            fix_response = agent.chat(
                f"The generated strategy code has an error:\n{error}\n\n"
                f"Please fix the code and output it again with the {COMPLETION_MARKER} marker."
            )
            fixed = extract_strategy_payload(fix_response)
            if fixed and fixed.get("code"):
                code = fixed["code"]
                name = fixed.get("name", name)
            else:
                # Try extracting code from markdown
                import re

                code_match = re.search(r"```python\s*\n(.*?)```", fix_response, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
    else:
        console.print("[red]Could not generate valid strategy code after 3 attempts.[/red]")
        console.print("[dim]Try again with a simpler strategy or more specific instructions.[/dim]")
        return

    # Run backtest
    console.print(f"\n[bold]Running backtest on {symbol} (1 year)...[/bold]")
    try:
        strategy_obj, result = build_and_test(code, symbol=symbol, period="1y")
        result.print_summary()
        if result.trades:
            result.print_trades(10)
    except Exception as e:
        console.print(f"[red]Backtest failed: {e}[/red]")
        console.print("[dim]The strategy code might need adjustment.[/dim]")
        agent._history = _saved_history
        return

    # ── Save prompt ──────────────────────────────────────────
    console.print()
    if Confirm.ask(f"Save strategy [cyan]{name}[/cyan]?", default=True):
        metadata = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "default_symbol": symbol,
            "simple_mode": simple_mode,
            "last_backtest": {
                "symbol": symbol,
                "period": "1y",
                "total_return": round(result.total_return, 2),
                "sharpe": round(result.sharpe_ratio, 2),
                "win_rate": round(result.win_rate, 1),
                "max_drawdown": round(result.max_drawdown, 2),
                "total_trades": result.total_trades,
                "date": result.end_date,
            },
        }
        path = strategy_store.save_strategy(name, code, metadata)
        console.print(f"[green]Strategy saved![/green] {path}")
        console.print(f"[dim]Run: strategy backtest {name} --period 2y[/dim]")
        console.print(f"[dim]Run: strategy run {name} {symbol} --paper[/dim]")
    else:
        console.print("[dim]Strategy not saved.[/dim]")

    # Restore main conversation history
    agent._history = _saved_history


# ── strategy list ────────────────────────────────────────────


def _cmd_list() -> None:
    """List all saved strategies."""
    from engine.strategy_builder import strategy_store, print_strategy_list

    strategies = strategy_store.list_strategies()
    print_strategy_list(strategies)


# ── strategy backtest ────────────────────────────────────────


def _cmd_backtest(args: list[str]) -> None:
    """Re-backtest a saved strategy."""
    if not args:
        console.print("[red]Usage: strategy backtest <name> [--period 2y][/red]")
        return

    from engine.strategy_builder import strategy_store
    from engine.backtest import Backtester

    name = args[0]
    period = "1y"
    for i, a in enumerate(args):
        if a == "--period" and i + 1 < len(args):
            period = args[i + 1]

    # Load symbol from metadata or prompt
    meta = strategy_store.get_metadata(name)
    explicit = args[1].upper() if len(args) > 1 and not args[1].startswith("-") else None
    saved = meta.get("default_symbol") if meta else None
    symbol = _resolve_symbol(from_payload=saved, from_args=explicit)

    try:
        strategy = strategy_store.load_strategy(name)
    except FileNotFoundError:
        console.print(
            f"[red]Strategy '{name}' not found. Run [bold]strategy list[/bold] to see available.[/red]"
        )
        return
    except Exception as e:
        console.print(f"[red]Failed to load strategy: {e}[/red]")
        return

    console.print(f"[dim]Backtesting {name} on {symbol} ({period})...[/dim]")

    try:
        bt = Backtester(symbol=symbol, period=period)
        result = bt.run(strategy)
        result.print_summary()
        result.print_trades(10)

        # Update metadata with latest backtest
        strategy_store.update_metadata(
            name,
            {
                "last_backtest": {
                    "symbol": symbol,
                    "period": period,
                    "total_return": round(result.total_return, 2),
                    "sharpe": round(result.sharpe_ratio, 2),
                    "win_rate": round(result.win_rate, 1),
                    "max_drawdown": round(result.max_drawdown, 2),
                    "total_trades": result.total_trades,
                    "date": result.end_date,
                }
            },
        )
    except Exception as e:
        console.print(f"[red]Backtest failed: {e}[/red]")


# ── strategy run ─────────────────────────────────────────────


def _cmd_run(args: list[str]) -> None:
    """Load strategy, generate latest signal, optionally paper-trade."""
    if not args:
        console.print("[red]Usage: strategy run <name> [symbol] [--paper][/red]")
        return

    from engine.strategy_builder import strategy_store
    from market.history import get_ohlcv

    name = args[0]
    paper_mode = "--paper" in args
    clean_args = [a for a in args[1:] if a != "--paper"]

    meta = strategy_store.get_metadata(name)
    explicit = clean_args[0].upper() if clean_args else None
    saved = meta.get("default_symbol") if meta else None
    symbol = _resolve_symbol(from_payload=saved, from_args=explicit)

    try:
        strategy = strategy_store.load_strategy(name)
    except FileNotFoundError:
        console.print(f"[red]Strategy '{name}' not found.[/red]")
        return
    except Exception as e:
        console.print(f"[red]Failed to load: {e}[/red]")
        return

    # Fetch recent data and generate signals
    console.print(f"[dim]Running {name} on {symbol}...[/dim]")
    try:
        df = get_ohlcv(symbol, days=90)
        if df.empty:
            console.print(f"[red]No data for {symbol}[/red]")
            return

        signals = strategy.generate_signals(df)
        latest_signal = int(signals.iloc[-1]) if len(signals) > 0 else 0
        prev_signal = int(signals.iloc[-2]) if len(signals) > 1 else 0
        latest_price = float(df["close"].iloc[-1])
        latest_date = (
            str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1])
        )

        signal_map = {
            1: "[green bold]BUY[/green bold]",
            -1: "[red bold]SELL[/red bold]",
            0: "[dim]HOLD[/dim]",
        }
        console.print(f"\n  {symbol} @ Rs.{latest_price:,.2f} ({latest_date})")
        console.print(f"  Signal: {signal_map.get(latest_signal, 'HOLD')}")

        if latest_signal != prev_signal and latest_signal != 0:
            console.print(
                f"  [yellow]Signal changed![/yellow] Previous: {signal_map.get(prev_signal, 'HOLD')}"
            )

        # Show recent signal history
        recent = signals.tail(10)
        signal_str = " ".join(
            "[green]+[/green]" if s == 1 else "[red]-[/red]" if s == -1 else "[dim].[/dim]"
            for s in recent
        )
        console.print(f"  Last 10 days: {signal_str}")

        # Paper trade if requested
        if paper_mode and latest_signal == 1:
            console.print(f"\n[bold]Paper trading: BUY {symbol}[/bold]")
            try:
                from brokers.session import get_broker
                from brokers.base import OrderRequest

                broker = get_broker()
                if broker:
                    capital = float(os.environ.get("TOTAL_CAPITAL", "200000"))
                    risk_pct = float(os.environ.get("DEFAULT_RISK_PCT", "2"))
                    quantity = max(1, int((capital * risk_pct / 100) / latest_price))

                    req = OrderRequest(
                        symbol=f"NSE:{symbol}-EQ",
                        exchange="NSE",
                        transaction_type="BUY",
                        quantity=quantity,
                        order_type="MARKET",
                        product="CNC",
                        tag=f"strategy:{name}",
                    )
                    resp = broker.place_order(req)
                    console.print(
                        f"  [green]Order placed:[/green] {resp.status} | Qty: {quantity} | ID: {resp.order_id}"
                    )
                else:
                    console.print("[dim]No broker connected. Use [bold]login[/bold] first.[/dim]")
            except Exception as e:
                console.print(f"[red]Paper trade failed: {e}[/red]")

        elif paper_mode and latest_signal == -1:
            console.print(
                f"\n[bold yellow]Signal is SELL — check your positions for {symbol}[/bold yellow]"
            )
        elif paper_mode:
            console.print("\n[dim]Signal is HOLD — no action taken.[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ── strategy show ────────────────────────────────────────────


def _cmd_show(args: list[str]) -> None:
    """Display strategy code and metadata."""
    if not args:
        console.print("[red]Usage: strategy show <name>[/red]")
        return

    from engine.strategy_builder import strategy_store, print_strategy_code

    name = args[0]
    code = strategy_store.get_code(name)
    if not code:
        console.print(f"[red]Strategy '{name}' not found.[/red]")
        return

    meta = strategy_store.get_metadata(name)
    print_strategy_code(name, code, meta)


# ── strategy delete ──────────────────────────────────────────


def _cmd_delete(args: list[str]) -> None:
    """Delete a saved strategy."""
    if not args:
        console.print("[red]Usage: strategy delete <name>[/red]")
        return

    from engine.strategy_builder import strategy_store

    name = args[0]
    meta = strategy_store.get_metadata(name)
    if not meta and not strategy_store.get_code(name):
        console.print(f"[red]Strategy '{name}' not found.[/red]")
        return

    if Confirm.ask(f"Delete strategy [cyan]{name}[/cyan]?", default=False):
        strategy_store.delete_strategy(name)
        console.print(f"[dim]Strategy '{name}' deleted.[/dim]")
    else:
        console.print("[dim]Cancelled.[/dim]")


# ── strategy export ──────────────────────────────────────────


def _cmd_export(args: list[str]) -> None:
    """Export a saved strategy to Pine Script (.pine file)."""
    if not args:
        console.print("[red]Usage: strategy export <name> --pine[/red]")
        return

    from pathlib import Path
    from engine.strategy_builder import strategy_store
    from engine.export.pinescript import strategy_to_pinescript, save_pinescript

    name = args[0]
    pine_mode = "--pine" in args

    if not pine_mode:
        console.print(
            "[red]Only --pine export is supported. Usage: strategy export <name> --pine[/red]"
        )
        return

    code = strategy_store.get_code(name)
    if not code:
        console.print(f"[red]Strategy '{name}' not found. Run [bold]strategy list[/bold].[/red]")
        return

    meta = strategy_store.get_metadata(name) or {}
    pine = strategy_to_pinescript(name=name, python_code=code, metadata=meta)

    output_path = Path(f"{name}.pine")
    save_pinescript(pine, output_path)
    console.print(f"[green]Pine Script exported:[/green] {output_path.resolve()}")
    console.print("[dim]Paste the file contents into TradingView's Pine Editor.[/dim]")


# ── strategy library ─────────────────────────────────────────


def _cmd_library(args: list[str]) -> None:
    """Browse the curated strategy template library (options and/or technical)."""
    from engine.strategy_library import strategy_library, CATEGORIES
    from engine.technical_library import tech_library, TECH_CATEGORIES

    # Parse --type flag
    lib_type = "all"
    clean: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            lib_type = args[i + 1].lower()
            i += 2
        else:
            clean.append(args[i])
            i += 1

    if lib_type not in ("options", "technical", "all"):
        console.print(f"[red]Unknown --type '{lib_type}'. Use: options, technical, or all[/red]")
        return

    category = clean[0].lower() if clean else ""

    all_cats = tuple(CATEGORIES) + tuple(TECH_CATEGORIES)
    options_cats = tuple(CATEGORIES)
    technical_cats = tuple(TECH_CATEGORIES)

    if category:
        # Route to correct library by category membership
        if category in options_cats and lib_type != "technical":
            templates = strategy_library.list_by_category(category)
            console.print(
                f"\n[bold cyan]Options Library — {category.title()}[/bold cyan] "
                f"[dim]({len(templates)} strategies)[/dim]\n"
            )
            _print_library_table(templates)
        elif category in technical_cats and lib_type != "options":
            templates = tech_library.list_by_category(category)
            console.print(
                f"\n[bold cyan]Technical Library — {category.title()}[/bold cyan] "
                f"[dim]({len(templates)} strategies)[/dim]\n"
            )
            _print_technical_table(templates)
        elif category not in all_cats:
            # Try search across both libraries
            opt_matches = strategy_library.search(category)
            tech_matches = tech_library.search(category)
            if opt_matches or tech_matches:
                console.print(
                    f"[yellow]Unknown category '{category}'. Showing search results:[/yellow]\n"
                )
                if opt_matches:
                    console.print("[bold]Options strategies:[/bold]")
                    _print_library_table(opt_matches)
                if tech_matches:
                    console.print("\n[bold]Technical strategies:[/bold]")
                    _print_technical_table(tech_matches)
            else:
                console.print(
                    f"[red]Unknown category '{category}'.[/red] "
                    f"Options: {', '.join(options_cats)} | "
                    f"Technical: {', '.join(technical_cats)}"
                )
        return

    # No category filter — show based on --type
    if lib_type == "options":
        templates = strategy_library.list_all()
        console.print(
            f"\n[bold cyan]Options Strategy Library[/bold cyan] "
            f"[dim]({len(templates)} strategies)[/dim]\n"
        )
        _print_library_table(templates)

    elif lib_type == "technical":
        templates = tech_library.list_all()
        console.print(
            f"\n[bold cyan]Technical Strategy Library[/bold cyan] "
            f"[dim]({len(templates)} strategies)[/dim]\n"
        )
        _print_technical_table(templates)

    else:  # all
        opt_templates = strategy_library.list_all()
        tech_templates = tech_library.list_all()
        console.print(
            f"\n[bold cyan]Options Strategy Library[/bold cyan] "
            f"[dim]({len(opt_templates)} strategies)[/dim]\n"
        )
        _print_library_table(opt_templates)
        console.print(
            f"\n[bold cyan]Technical Strategy Library[/bold cyan] "
            f"[dim]({len(tech_templates)} strategies)[/dim]\n"
        )
        _print_technical_table(tech_templates)

    console.print("\n[dim]Run: [bold]strategy learn <id>[/bold]  to see full explanation[/dim]")
    console.print(
        "[dim]Run: [bold]strategy use <id> SYMBOL[/bold]  to apply with live data[/dim]\n"
    )


def _print_technical_table(templates) -> None:
    """Render a Rich table of technical strategy templates."""
    from rich.table import Table

    current_cat = None
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("ID", style="cyan", width=28)
    table.add_column("Name", width=26)
    table.add_column("Category", width=14)
    table.add_column("Timeframes", width=16)
    table.add_column("Complexity", width=14)
    table.add_column("Backtestable", width=12)

    for t in templates:
        if t.category != current_cat:
            if current_cat is not None:
                table.add_section()
            current_cat = t.category

        complexity_color = {
            "beginner": "green",
            "intermediate": "yellow",
            "advanced": "red",
        }.get(t.complexity, "white")
        backtest_str = "[green]✓[/green]" if t.backtest_key else "[dim]—[/dim]"
        tf_str = ", ".join(t.timeframes[:3])

        table.add_row(
            t.id,
            t.name,
            t.category,
            tf_str,
            f"[{complexity_color}]{t.complexity}[/{complexity_color}]",
            backtest_str,
        )

    console.print(table)


def _print_library_table(templates) -> None:
    """Render a Rich table of strategy templates."""
    from rich.table import Table

    current_cat = None

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("ID", style="cyan", width=28)
    table.add_column("Name", width=24)
    table.add_column("Category", width=12)
    table.add_column("View", width=12)
    table.add_column("IV", width=6)
    table.add_column("DTE", width=10)
    table.add_column("Complexity", width=14)

    for t in templates:
        if t.category != current_cat:
            if current_cat is not None:
                table.add_section()
            current_cat = t.category

        view_str = "/".join(v[:4] for v in t.views)
        dte_str = f"{t.ideal_dte[0]}–{t.ideal_dte[1]}d"
        complexity_color = {
            "beginner": "green",
            "intermediate": "yellow",
            "advanced": "red",
        }.get(t.complexity, "white")

        table.add_row(
            t.id,
            t.name,
            t.category,
            view_str,
            t.ideal_iv,
            dte_str,
            f"[{complexity_color}]{t.complexity}[/{complexity_color}]",
        )

    console.print(table)


# ── Leg formatter helpers ─────────────────────────────────────

# Hypothetical spot used for concrete examples throughout the learn panel.
# ₹24,000 is close to NIFTY and a round number that's easy to reason about.
_EXAMPLE_SPOT = 24_000


def _example_strike(leg) -> int:
    """Compute the example strike from _EXAMPLE_SPOT and the leg's offset."""
    if leg.option_type == "STOCK":
        return _EXAMPLE_SPOT
    raw = _EXAMPLE_SPOT * (1 + leg.strike_offset_pct)
    return int(round(raw / 100) * 100)  # round to nearest 100 (Indian index convention)


def _leg_strike_plain(leg) -> str:
    """Human-readable strike location: 'at current price', '3% above current price', etc."""
    pct = leg.strike_offset_pct
    if leg.option_type == "STOCK":
        return "at current market price"
    if pct == 0.0:
        return "at current price (ATM — at-the-money)"
    if pct > 0:
        return f"{pct * 100:.0f}% above current price (OTM — out-of-the-money)"
    return f"{abs(pct) * 100:.0f}% below current price (OTM — out-of-the-money)"


def _leg_plain_description(leg) -> str:
    """One sentence explaining what each leg means for the trader."""
    action = leg.action
    otype = leg.option_type
    multi = leg.lots_multiplier
    multi_note = f" (×{multi} contracts)" if multi > 1 else ""

    if otype == "STOCK":
        if action == "BUY":
            return "Own the actual shares — full upside, but also full downside if the stock falls."
        return "Short-sell the shares — profit if price falls, unlimited loss if it rises."

    if otype == "CE":
        if action == "BUY":
            return (
                f"Pay a premium{multi_note} for the right to profit if the stock rises above this level. "
                "Loss is limited to the premium paid."
            )
        return (
            f"Collect premium{multi_note} now; in return you're obligated to sell if the "
            "stock rises past this level. Acts as a profit ceiling or a hedge."
        )

    # PE
    if action == "BUY":
        return (
            f"Pay a premium{multi_note} for the right to profit if the stock falls below this level. "
            "Loss is limited to the premium paid."
        )
    return (
        f"Collect premium{multi_note} now; in return you're obligated to buy if the "
        "stock falls past this level. Acts as a floor or a hedge."
    )


def _leg_scenarios(leg, strike: int) -> tuple[str, str]:
    """
    Return (good_scenario, bad_scenario) as plain-English strings for a leg.
    Uses the concrete example strike so the user can picture real numbers.
    """
    action = leg.action
    otype = leg.option_type
    s = f"₹{strike:,}"

    if otype == "STOCK":
        if action == "BUY":
            return (
                f"Stock rises above {s} → you profit ₹1 for every ₹1 it goes up",
                f"Stock falls below {s} → you lose ₹1 for every ₹1 it goes down",
            )
        return (
            f"Stock falls below {s} → you profit as price drops",
            f"Stock rises above {s} → unlimited loss",
        )

    if otype == "CE":
        if action == "BUY":
            return (
                f"Stock closes above {s} at expiry → your call gains value, you profit",
                f"Stock closes at or below {s} → call expires worthless, you lose only the premium paid",
            )
        return (
            f"Stock stays below {s} at expiry → call expires worthless, you keep the full premium",
            f"Stock rises above {s} → you're obligated to sell at {s}; loss grows the higher it goes",
        )

    # PE
    if action == "BUY":
        return (
            f"Stock closes below {s} at expiry → your put gains value, you profit",
            f"Stock closes at or above {s} → put expires worthless, you lose only the premium paid",
        )
    return (
        f"Stock stays above {s} at expiry → put expires worthless, you keep the full premium",
        f"Stock falls below {s} → you're obligated to buy at {s}; loss grows the lower it goes",
    )


def _format_legs(legs) -> str:
    """
    Format each leg with: location, plain description, and concrete example scenarios.

    Example (one Iron Condor leg):
      SELL  CE  3% above current price (OTM)
               → Collect premium; obligated to sell if stock rises past this.
               Example if stock is at ₹24,000 → this strike is ₹24,700
                 ✓ Stock stays below ₹24,700: call expires worthless, you keep the full premium
                 ✗ Stock rises above ₹24,700: you're obligated to sell; loss grows the higher it goes
    """
    lines = []
    for leg in legs:
        action = leg.action
        otype = leg.option_type
        strike = _example_strike(leg)
        strike_loc = _leg_strike_plain(leg)
        description = _leg_plain_description(leg)
        good, bad = _leg_scenarios(leg, strike)
        multi = f" ×{leg.lots_multiplier}" if leg.lots_multiplier > 1 else ""

        action_color = "green" if action == "BUY" else "red"
        lines.append(
            f"  [{action_color}]{action:<5}[/{action_color}] {otype}{multi}  "
            f"[dim]{strike_loc}[/dim]\n"
            f"         [dim]→ {description}[/dim]\n"
            f"         [dim]Example (stock @ ₹{_EXAMPLE_SPOT:,}): this strike = ₹{strike:,}[/dim]\n"
            f"           [green]✓[/green] [dim]{good}[/dim]\n"
            f"           [red]✗[/red] [dim]{bad}[/dim]"
        )
    return "\n\n".join(lines)


# ── strategy learn ────────────────────────────────────────────


def _cmd_learn(args: list[str]) -> None:
    """Show a detailed explanation panel for a strategy template (options or technical)."""
    from engine.strategy_library import strategy_library
    from engine.technical_library import tech_library

    if not args:
        console.print("[red]Usage: strategy learn <strategy_id>[/red]")
        console.print("[dim]Run 'strategy library' to see all available strategy IDs.[/dim]")
        return

    name = args[0].lower()

    # Try options library first, then technical library
    t = None
    is_technical = False
    try:
        t = strategy_library.get(name)
    except KeyError:
        try:
            t = tech_library.get(name)
            is_technical = True
        except KeyError:
            pass

    if t is None:
        # Search both libraries for suggestions
        opt_matches = strategy_library.search(name)
        tech_matches = tech_library.search(name)
        all_matches = opt_matches + tech_matches
        if all_matches:
            console.print(f"[yellow]Strategy '{name}' not found. Did you mean:[/yellow]")
            for m in all_matches[:4]:
                console.print(f"  [cyan]{m.id}[/cyan] — {m.name}")
        else:
            console.print(
                f"[red]Strategy '{name}' not found.[/red] "
                "Run [bold]strategy library[/bold] to see all."
            )
        return

    if is_technical:
        _learn_technical(t)
    else:
        _learn_options(t)


def _learn_options(t) -> None:
    """Render the learn panel for an options strategy template."""
    from rich.panel import Panel

    complexity_colors = {"beginner": "green", "intermediate": "yellow", "advanced": "red"}
    comp_color = complexity_colors.get(t.complexity, "white")

    content = (
        f"[dim]{t.category.upper()} · [{comp_color}]{t.complexity}[/{comp_color}] · "
        f"Ideal IV: {t.ideal_iv} · DTE: {t.ideal_dte[0]}–{t.ideal_dte[1]} days · "
        f"Capital: {t.capital_type}[/dim]\n\n"
        f"[bold yellow]IN PLAIN ENGLISH[/bold yellow]\n{t.layman_explanation}\n\n"
        f"[bold]LEGS[/bold]  [dim](what you actually trade)[/dim]\n"
        + _format_legs(t.legs)
        + f"\n\n[bold]HOW IT WORKS[/bold]\n{t.explanation}\n\n"
        f"[bold]WHEN TO USE[/bold]\n{t.when_to_use}\n\n"
        f"[bold]WHEN NOT TO USE[/bold]\n{t.when_not_to_use}\n\n"
        f"[bold]MAX PROFIT[/bold]  {t.max_profit}\n"
        f"[bold]MAX LOSS[/bold]    {t.max_loss}\n\n"
        f"[bold]RISKS[/bold]\n"
        + "\n".join(f"  • {r}" for r in t.risks)
        + f"\n\n[dim]Tags: {' '.join(t.tags)}[/dim]"
    )

    console.print(
        Panel(
            content,
            title=f"[bold]{t.name}[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(f"\n[dim]Apply with live data: [bold]strategy use {t.id} SYMBOL[/bold][/dim]\n")


def _learn_technical(t) -> None:
    """Render the learn panel for a technical strategy template."""
    from rich.panel import Panel

    complexity_colors = {"beginner": "green", "intermediate": "yellow", "advanced": "red"}
    comp_color = complexity_colors.get(t.complexity, "white")

    # Format signal rules
    signal_lines = []
    for rule in t.signal_rules:
        sig = rule.get("signal", "")
        cond = rule.get("condition", "")
        example = rule.get("example", "")
        sig_color = "green" if sig == "BUY" else "red" if sig == "SELL" else "yellow"
        signal_lines.append(
            f"  [{sig_color}]{sig:<5}[/{sig_color}] [dim]{cond}[/dim]\n"
            f"         [dim]e.g. {example}[/dim]"
        )
    signals_str = "\n\n".join(signal_lines)

    # Format parameters
    param_lines = []
    for pname, pdef in t.parameters.items():
        ptype = pdef.get("type", "")
        default = pdef.get("default", "")
        desc = pdef.get("description", "")
        param_lines.append(
            f"  [cyan]{pname}[/cyan] ({ptype}, default={default})  [dim]{desc}[/dim]"
        )
    params_str = "\n".join(param_lines) if param_lines else "  [dim]None[/dim]"

    # Load cached backtest result if available
    cached: dict | None = None
    if t.backtest_key:
        try:
            from engine.backtest_cache import load_result as _cache_load

            cached = _cache_load(t.backtest_key)
        except Exception:
            pass

    if t.backtest_key:
        if cached:
            ret = cached["total_return"]
            ret_color = "green" if ret >= 0 else "red"
            sharpe = cached["sharpe"]
            sharpe_color = "green" if sharpe >= 1 else "yellow" if sharpe >= 0 else "red"
            dd = abs(cached["max_drawdown"])
            backtest_str = (
                f"[dim]Last run: {cached['symbol']} · {cached['period']} "
                f"· {cached['run_date']}[/dim]\n"
                f"  Return      [{ret_color}]{ret:+.1f}%[/{ret_color}]   "
                f"Sharpe [{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]   "
                f"Max DD [red]-{dd:.1f}%[/red]\n"
                f"  Win Rate    {cached['win_rate']:.0f}%   "
                f"Trades {cached['total_trades']}   "
                f"Avg Hold {cached['avg_hold']:.0f}d\n"
                f"  [dim]Re-run: [bold]strategy use {t.id} SYMBOL[/bold][/dim]"
            )
        else:
            backtest_str = (
                f"[green]✓ Supported.[/green]  "
                f"[dim]Run [bold]strategy use {t.id} SYMBOL[/bold] to see results.[/dim]"
            )
    else:
        backtest_str = "[dim]Not yet available (requires intraday/multi-asset data)[/dim]"

    tf_str = ", ".join(t.timeframes)
    inst_str = ", ".join(t.instruments)

    content = (
        f"[dim]{t.category.upper()} · [{comp_color}]{t.complexity}[/{comp_color}] · "
        f"Timeframes: {tf_str} · Instruments: {inst_str}[/dim]\n\n"
        f"[bold yellow]IN PLAIN ENGLISH[/bold yellow]\n{t.layman_explanation}\n\n"
        f"[bold]SIGNALS[/bold]  [dim](when this strategy says BUY or SELL)[/dim]\n"
        + signals_str
        + f"\n\n[bold]HOW IT WORKS[/bold]\n{t.explanation}\n\n"
        f"[bold]WHEN TO USE[/bold]\n{t.when_to_use}\n\n"
        f"[bold]WHEN NOT TO USE[/bold]\n{t.when_not_to_use}\n\n"
        f"[bold]PARAMETERS[/bold]\n{params_str}\n\n"
        f"[bold]RISKS[/bold]\n"
        + "\n".join(f"  • {r}" for r in t.risks)
        + f"\n\n[bold]BACKTEST[/bold]\n  {backtest_str}"
        + f"\n\n[dim]Tags: {' '.join(t.tags)}[/dim]"
    )

    console.print(
        Panel(
            content,
            title=f"[bold]{t.name}[/bold]",
            border_style="green",
            padding=(1, 2),
        )
    )
    if t.backtest_key:
        console.print(f"\n[dim]Run backtest: [bold]strategy use {t.id} SYMBOL[/bold][/dim]\n")
    else:
        console.print(
            "\n[dim]This strategy is documented for learning. "
            "Backtest support coming in a future release.[/dim]\n"
        )


# ── strategy use ──────────────────────────────────────────────


def _cmd_use(args: list[str]) -> None:
    """Apply a strategy template to a real symbol (options: live ATM data; technical: backtest)."""
    from engine.strategy_library import strategy_library, apply_template
    from engine.technical_library import tech_library
    from engine.strategy import get_atm_data
    from rich.panel import Panel
    from rich.table import Table

    strategy_id, symbol, lots, dte = _parse_use_args(args)

    if not strategy_id:
        console.print("[red]Usage: strategy use <strategy_id> SYMBOL [--lots N] [--dte N][/red]")
        console.print("[dim]Run 'strategy library' to see all strategy IDs.[/dim]")
        return

    if not symbol:
        console.print("[red]Usage: strategy use <strategy_id> SYMBOL [--lots N] [--dte N][/red]")
        return

    # Look up in options library first, then technical library
    template = None
    is_technical = False
    try:
        template = strategy_library.get(strategy_id)
    except KeyError:
        try:
            template = tech_library.get(strategy_id)
            is_technical = True
        except KeyError:
            pass

    if template is None:
        opt_matches = strategy_library.search(strategy_id)
        tech_matches = tech_library.search(strategy_id)
        all_matches = opt_matches + tech_matches
        if all_matches:
            console.print(f"[yellow]Strategy '{strategy_id}' not found. Did you mean:[/yellow]")
            for m in all_matches[:3]:
                console.print(f"  [cyan]{m.id}[/cyan] — {m.name}")
        else:
            console.print(
                f"[red]Strategy '{strategy_id}' not found.[/red] "
                "Run [bold]strategy library[/bold] to see all."
            )
        return

    if is_technical:
        _use_technical(template, symbol, args)
        return

    # Warn if stock-leg strategy applied to index
    indices = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"}
    if template.capital_type == "stock" and symbol.upper() in indices:
        console.print(
            f"[yellow]Note: '{template.name}' involves a stock leg. "
            f"Applying to an index ({symbol}) gives approximate results.[/yellow]"
        )

    # Fetch spot price
    spot = None
    try:
        from market.quotes import get_ltp

        ltp = get_ltp(f"NSE:{symbol}")
        if ltp and ltp > 0:
            spot = float(ltp)
    except Exception:
        pass

    if not spot:
        try:
            from rich.prompt import FloatPrompt

            spot = FloatPrompt.ask(f"Enter current spot price for {symbol}")
        except Exception:
            console.print(
                f"[red]Could not fetch spot price for {symbol}. Provide it manually.[/red]"
            )
            return

    # Fetch ATM data
    console.print(f"[dim]Fetching ATM data for {symbol} @ ₹{spot:,.0f}...[/dim]")
    try:
        atm_ce_prem, atm_pe_prem, atm_strike, lot_size = get_atm_data(symbol, spot)
    except Exception as e:
        console.print(f"[red]Could not fetch ATM data: {e}[/red]")
        return

    # Apply the template
    result = apply_template(
        template=template,
        symbol=symbol,
        spot=spot,
        atm_ce_prem=atm_ce_prem,
        atm_pe_prem=atm_pe_prem,
        atm_strike=atm_strike,
        lot_size=lot_size,
        lots=lots,
        dte=dte,
    )

    # Display result
    console.print(f"\n[bold cyan]{result.name}[/bold cyan] — {symbol} @ ₹{spot:,.0f}\n")

    # Legs table
    leg_table = Table(show_header=True, header_style="bold dim", box=None, pad_edge=False)
    leg_table.add_column("Action", width=8)
    leg_table.add_column("Type", width=8)
    leg_table.add_column("Strike", justify="right", width=10)
    leg_table.add_column("Premium", justify="right", width=10)
    leg_table.add_column("Lots", justify="right", width=6)

    for leg in result.legs:
        action_color = "green" if leg["action"] == "BUY" else "red"
        leg_table.add_row(
            f"[{action_color}]{leg['action']}[/{action_color}]",
            leg.get("type", "STOCK"),
            f"₹{leg.get('strike', 0):,.0f}",
            f"₹{leg.get('premium', 0):.0f}" if "premium" in leg else "—",
            str(leg.get("lots", lots)),
        )

    console.print(leg_table)

    # P&L summary panel
    mp_str = f"₹{result.max_profit:,.0f}" if result.max_profit < 1e9 else "Unlimited"
    ml_str = f"₹{abs(result.max_loss):,.0f}" if result.max_loss > -1e9 else "Unlimited"
    be_str = " / ".join(f"₹{b:,.0f}" for b in result.breakeven)

    summary = (
        f"  Capital Needed : [bold]₹{result.capital_needed:,.0f}[/bold]\n"
        f"  Max Profit     : [green]↑ {mp_str}[/green]\n"
        f"  Max Loss       : [red]↓ {ml_str}[/red]\n"
        f"  Breakeven      : {be_str}\n"
        f"  R:R Ratio      : {result.rr_ratio}×\n"
        f"  Best for       : [dim]{result.best_for}[/dim]\n"
        f"  Risks          : [dim]{result.risks}[/dim]"
    )
    console.print(Panel(summary, title="P&L Summary", border_style="dim", padding=(0, 2)))
    console.print(
        f"\n[dim]For placement: [bold]trade {symbol} {' / '.join(template.views)}[/bold][/dim]\n"
    )


def _use_technical(template, symbol: str, raw_args: list[str]) -> None:
    """Run a technical strategy template: backtest if available, else show info."""
    from rich.panel import Panel

    if not template.backtest_key:
        console.print(
            f"\n[bold cyan]{template.name}[/bold cyan]\n"
            f"[yellow]This strategy cannot be backtested yet.[/yellow]\n"
            f"[dim]It requires {', '.join(template.instruments)} data that is not yet wired up "
            f"(intraday, multi-asset, or specialised feeds).[/dim]\n\n"
            f"[dim]Run [bold]strategy learn {template.id}[/bold] to explore the strategy.[/dim]\n"
        )
        return

    # Parse optional --period flag
    period = "1y"
    i = 0
    while i < len(raw_args):
        if raw_args[i] == "--period" and i + 1 < len(raw_args):
            period = raw_args[i + 1]
            i += 2
        else:
            i += 1

    console.print(
        f"\n[dim]Running backtest: [bold]{template.name}[/bold] on {symbol} ({period})...[/dim]"
    )

    try:
        from engine.backtest import Backtester, STRATEGIES

        from engine.backtest_cache import save_result as _cache_save

        strategy_cls = STRATEGIES[template.backtest_key]
        strategy = strategy_cls([])
        bt = Backtester(symbol=symbol, period=period)
        result = bt.run(strategy)
        result.print_summary()

        # Persist so 'strategy learn' can show it without re-running
        try:
            _cache_save(template.backtest_key, result, symbol, period)
        except Exception:
            pass

        # Show last 10 signals in a mini timeline
        try:
            from market.history import get_ohlcv

            df = get_ohlcv(symbol, days=90)
            if not df.empty:
                signals = strategy.generate_signals(df)
                latest = int(signals.iloc[-1]) if len(signals) else 0
                latest_price = float(df["close"].iloc[-1])
                latest_date = (
                    str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1])
                )
                signal_map = {1: "[green]BUY[/green]", -1: "[red]SELL[/red]", 0: "[dim]HOLD[/dim]"}
                recent = signals.tail(10)
                sig_str = " ".join(
                    "[green]+[/green]" if s == 1 else "[red]-[/red]" if s == -1 else "[dim].[/dim]"
                    for s in recent
                )
                console.print(
                    Panel(
                        f"  Symbol : [bold]{symbol}[/bold] @ ₹{latest_price:,.2f} ({latest_date})\n"
                        f"  Signal : {signal_map.get(latest, '[dim]HOLD[/dim]')}\n"
                        f"  Last 10: {sig_str}",
                        title="Current Signal",
                        border_style="green",
                        padding=(0, 2),
                    )
                )
        except Exception:
            pass  # signal panel is best-effort

    except Exception as e:
        console.print(f"[red]Backtest failed: {e}[/red]")


def _parse_use_args(args: list[str]) -> tuple[str, str, int, int]:
    """Parse args for 'strategy use'. Returns (strategy_id, symbol, lots, dte)."""
    lots = 1
    dte = 30
    clean: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--lots" and i + 1 < len(args):
            try:
                lots = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--dte" and i + 1 < len(args):
            try:
                dte = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            clean.append(args[i])
            i += 1

    strategy_id = clean[0].lower() if len(clean) > 0 else ""
    symbol = clean[1].upper() if len(clean) > 1 else ""
    return strategy_id, symbol, lots, dte
