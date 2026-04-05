"""
app/commands/strategy.py
────────────────────────
Interactive strategy builder command.

Subcommands:
  strategy new [description] [--simple]             — AI-guided strategy creation
  strategy list                                     — show saved strategies
  strategy backtest <name> [--period 2y]            — re-backtest a saved strategy
  strategy run <name> [symbol] [--paper]            — generate signal + paper trade
  strategy show <name>                              — view code + metadata
  strategy delete <name>                            — remove a saved strategy
  strategy library [category]                       — browse the strategy template library
  strategy learn <name>                             — detailed explanation of a template
  strategy use <name> SYMBOL [--lots N] [--dte N]  — apply a template with live market data
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.prompt import Confirm

console = Console()


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
    else:
        console.print(
            "[dim]Usage:\n"
            "  strategy new [description] [--simple]             Create a new strategy\n"
            "  strategy list                                     List saved strategies\n"
            "  strategy backtest <name> [--period 2y]            Re-backtest\n"
            "  strategy run <name> [symbol] [--paper]            Generate signal\n"
            "  strategy show <name>                              View code\n"
            "  strategy delete <name>                            Delete\n"
            "  strategy library [category]                       Browse strategy templates\n"
            "  strategy learn <name>                             Explain a template\n"
            "  strategy use <name> SYMBOL [--lots N] [--dte N]  Apply template with live data[/dim]"
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

    # Inject the strategy builder system prompt as the first message
    first_message = prompt_text + "\n\n"
    if initial_desc:
        first_message += (
            f"The user wants to build this strategy: {initial_desc}\n\nStart the interview."
        )
    else:
        first_message += "The user wants to build a custom strategy. Start by asking what kind of strategy they have in mind."

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
                return

            if not user_input:
                continue
            if user_input.lower() == "cancel":
                console.print("[yellow]Strategy builder cancelled.[/yellow]")
                return
            if user_input.lower() in ("done", "generate", "build", "build it", "go"):
                response = _force_generate(agent)
            else:
                response = agent.chat(user_input)

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
        console.print(
            "[yellow]Could not generate strategy code. Try again with [bold]strategy new[/bold].[/yellow]"
        )
        return

    # ── Validate and backtest ────────────────────────────────
    code = strategy_payload.get("code", "")
    name = strategy_payload.get("name", "custom_strategy")
    description = strategy_payload.get("description", "")
    symbol = strategy_payload.get("symbol", "RELIANCE")
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
    symbol = meta.get("default_symbol", "RELIANCE") if meta else "RELIANCE"

    # Check if symbol was provided as second arg
    if len(args) > 1 and not args[1].startswith("-"):
        symbol = args[1].upper()

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
    symbol = (
        clean_args[0].upper()
        if clean_args
        else (meta.get("default_symbol", "RELIANCE") if meta else "RELIANCE")
    )

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


# ── strategy library ─────────────────────────────────────────


def _cmd_library(args: list[str]) -> None:
    """Browse the curated options strategy template library."""
    from engine.strategy_library import strategy_library, CATEGORIES

    category = args[0].lower() if args else ""

    if category and category not in CATEGORIES:
        # Try it as a search query
        matches = strategy_library.search(category)
        if matches:
            console.print(
                f"[yellow]Unknown category '{category}'. Showing search results instead:[/yellow]\n"
            )
            _print_library_table(matches)
        else:
            console.print(
                f"[red]Unknown category '{category}'.[/red] Valid: {', '.join(CATEGORIES)}"
            )
        return

    templates = (
        strategy_library.list_by_category(category) if category else strategy_library.list_all()
    )

    title = f"Strategy Library — {category.title()}" if category else "Strategy Library"
    console.print(f"\n[bold cyan]{title}[/bold cyan] [dim]({len(templates)} strategies)[/dim]\n")
    _print_library_table(templates)
    console.print("\n[dim]Run: [bold]strategy learn <id>[/bold]  to see full explanation[/dim]")
    console.print(
        "[dim]Run: [bold]strategy use <id> SYMBOL[/bold]  to apply with live data[/dim]\n"
    )


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


# ── strategy learn ────────────────────────────────────────────


def _cmd_learn(args: list[str]) -> None:
    """Show a detailed explanation panel for a strategy template."""
    from engine.strategy_library import strategy_library
    from rich.panel import Panel

    if not args:
        console.print("[red]Usage: strategy learn <strategy_id>[/red]")
        console.print("[dim]Run 'strategy library' to see all available strategy IDs.[/dim]")
        return

    name = args[0].lower()
    try:
        t = strategy_library.get(name)
    except KeyError:
        matches = strategy_library.search(name)
        if matches:
            console.print(f"[yellow]Strategy '{name}' not found. Did you mean:[/yellow]")
            for m in matches[:3]:
                console.print(f"  [cyan]{m.id}[/cyan] — {m.name}")
        else:
            console.print(
                f"[red]Strategy '{name}' not found.[/red] "
                "Run [bold]strategy library[/bold] to see all."
            )
        return

    # Build legs description
    leg_lines = []
    for leg in t.legs:
        offset_desc = ""
        if leg.strike_offset_pct == 0.0:
            offset_desc = "ATM"
        elif leg.strike_offset_pct > 0:
            offset_desc = f"+{leg.strike_offset_pct * 100:.0f}% OTM"
        else:
            offset_desc = f"{leg.strike_offset_pct * 100:.0f}% OTM"
        multi = f" ×{leg.lots_multiplier}" if leg.lots_multiplier > 1 else ""
        leg_lines.append(f"  {leg.action:<5} {leg.option_type} ({offset_desc}){multi}")

    complexity_colors = {"beginner": "green", "intermediate": "yellow", "advanced": "red"}
    comp_color = complexity_colors.get(t.complexity, "white")

    content = (
        f"[dim]{t.category.upper()} · [{comp_color}]{t.complexity}[/{comp_color}] · "
        f"Ideal IV: {t.ideal_iv} · DTE: {t.ideal_dte[0]}–{t.ideal_dte[1]} days · "
        f"Capital: {t.capital_type}[/dim]\n\n"
        f"[bold]LEGS[/bold]\n"
        + "\n".join(leg_lines)
        + f"\n\n[bold]WHAT IT IS[/bold]\n{t.explanation}\n\n"
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


# ── strategy use ──────────────────────────────────────────────


def _cmd_use(args: list[str]) -> None:
    """Apply a strategy template to a real symbol using live ATM data."""
    from engine.strategy_library import strategy_library, apply_template
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

    try:
        template = strategy_library.get(strategy_id)
    except KeyError:
        matches = strategy_library.search(strategy_id)
        if matches:
            console.print(f"[yellow]Strategy '{strategy_id}' not found. Did you mean:[/yellow]")
            for m in matches[:3]:
                console.print(f"  [cyan]{m.id}[/cyan] — {m.name}")
        else:
            console.print(
                f"[red]Strategy '{strategy_id}' not found.[/red] "
                "Run [bold]strategy library[/bold] to see all."
            )
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
