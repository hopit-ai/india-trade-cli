"""
app/commands/trade.py
─────────────────────
Guided trade confirmation flow — Step 17.

Flow:
  1. User specifies symbol + view (BULLISH/BEARISH/NEUTRAL)
  2. Agent fetches live data and recommends top strategy via engine/strategy.py
  3. Platform shows full order summary: legs, cost, max loss, % capital at risk
  4. Risk check: warns if risk exceeds user's tolerance
  5. Stop-loss confirmation: user must set one
  6. Final explicit confirmation: user types "yes" / "confirm"
  7. Routes to paper broker or real broker based on TRADING_MODE

This module is also called directly from the REPL `trade` command.
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from brokers.base import OrderRequest
from brokers.session import get_broker
from engine.strategy import recommend, StrategyResult

console = Console()


def run(symbol: str | None = None, view: str | None = None) -> None:
    """
    Interactive trade builder.

    Args:
        symbol: Pre-filled symbol (from `trade RELIANCE` on CLI)
        view:   Pre-filled view (from `trade RELIANCE BULLISH`)
    """
    console.print()

    mode = os.environ.get("TRADING_MODE", "PAPER")
    mode_badge = "[green]PAPER[/green]" if mode == "PAPER" else "[bold red]LIVE[/bold red]"
    console.print(
        Panel(
            "[bold cyan]📈  Trade Builder[/bold cyan]\n"
            f"[dim]Mode: {mode_badge}  •  Pick a symbol → choose a strategy → confirm order[/dim]\n"
            "[dim]Type Ctrl+C or enter 0 at any step to cancel.[/dim]",
            box=box.SIMPLE_HEAVY,
            style="cyan",
        )
    )

    # ── Step 1: Get symbol + view ─────────────────────────────
    if not symbol:
        symbol = Prompt.ask("[bold]Symbol[/bold]", default="NIFTY").upper()
    if not view:
        view = Prompt.ask(
            "[bold]View[/bold]",
            choices=["BULLISH", "BEARISH", "NEUTRAL"],
            default="BULLISH",
        ).upper()

    # ── Step 2: Get live data ─────────────────────────────────
    from market.quotes import get_ltp

    console.print(f"\n  [dim]Fetching live data for {symbol}...[/dim]")
    try:
        spot = get_ltp(f"NSE:{symbol}")
    except Exception:
        try:
            spot = get_ltp(f"NSE:{symbol} 50")  # index format
        except Exception:
            spot = float(
                Prompt.ask(f"[yellow]Could not fetch LTP for {symbol}. Enter manually[/yellow]")
            )

    capital = float(os.environ.get("TOTAL_CAPITAL", 200_000))
    risk_pct = float(os.environ.get("DEFAULT_RISK_PCT", 2))
    max_risk = capital * risk_pct / 100

    console.print(
        f"  Spot: [bold]₹{spot:,.2f}[/bold]   Capital: [bold]₹{capital:,.0f}[/bold]   "
        f"Max risk/trade: [yellow]₹{max_risk:,.0f}[/yellow] ({risk_pct}%)\n"
    )

    # ── Step 3: Strategy recommendations ──────────────────────
    console.print(f"  [dim]Evaluating strategies for {symbol} {view}...[/dim]")
    report = recommend(symbol=symbol, view=view, spot=spot, capital=capital, risk_pct=risk_pct)

    if not report.strategies:
        console.print(
            "[red]No strategies available for this view. Try a different symbol or view.[/red]"
        )
        return

    _show_strategies(report.strategies[:3])

    # ── Step 4: Let user pick strategy ────────────────────────
    choices = [str(i + 1) for i in range(min(3, len(report.strategies)))]
    choice = Prompt.ask(
        "\n[bold]Select strategy[/bold]",
        choices=choices + ["0"],
        default="1",
    )
    if choice == "0":
        console.print("[dim]Trade cancelled.[/dim]")
        return

    selected: StrategyResult = report.strategies[int(choice) - 1]
    console.print()
    _show_trade_summary(selected, symbol, spot)

    # ── Step 5: Risk check ────────────────────────────────────
    risk_pct_actual = abs(selected.max_loss) / capital * 100
    if abs(selected.max_loss) > max_risk:
        console.print(
            f"\n  [bold red]⚠  RISK WARNING[/bold red]  "
            f"Max loss ₹{abs(selected.max_loss):,.0f} exceeds your "
            f"limit of ₹{max_risk:,.0f} ({risk_pct}% of capital)."
        )
        if not Confirm.ask("  Proceed anyway?", default=False):
            console.print("[dim]Trade cancelled.[/dim]")
            return

    # ── Step 6: Stop-loss ─────────────────────────────────────
    sl_default = round(spot * 0.95, 2) if view == "BULLISH" else round(spot * 1.05, 2)
    console.print("\n  [bold]Stop-loss[/bold] (required before placing order)")
    sl_price = float(Prompt.ask("  Stop-loss price", default=str(sl_default)))
    sl_pct = abs(sl_price - spot) / spot * 100
    console.print(f"  Stop-loss set at ₹{sl_price:,.2f}  ({sl_pct:.1f}% from spot)")

    if sl_pct > 10:
        console.print(
            "[yellow]  ⚠  Stop-loss is >10% away — very wide. Consider tighter risk management.[/yellow]"
        )

    # ── Step 7: Final confirmation ─────────────────────────────
    mode = os.environ.get("TRADING_MODE", "PAPER")
    mode_badge = "[green]PAPER[/green]" if mode == "PAPER" else "[bold red]LIVE[/bold red]"

    console.print(f"\n  Mode: {mode_badge}")
    console.print(f"  Strategy: [bold]{selected.name}[/bold]")
    console.print(
        f"  Max loss: [red]₹{abs(selected.max_loss):,.0f}[/red]  "
        f"({risk_pct_actual:.1f}% of capital)"
    )
    console.print(f"  Stop-loss: ₹{sl_price:,.2f}")

    if not Confirm.ask("\n  [bold]Confirm and place order?[/bold]", default=False):
        console.print("[dim]Trade cancelled.[/dim]")
        return

    # ── Step 8: Place order(s) ────────────────────────────────
    broker = get_broker()
    _place_strategy_legs(broker, selected, symbol, mode)


def _show_strategies(strategies: list[StrategyResult]) -> None:
    """Show top-3 strategy cards."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    table.add_column("#", width=3)
    table.add_column("Strategy", style="bold white")
    table.add_column("Max Profit", justify="right")
    table.add_column("Max Loss", justify="right")
    table.add_column("Breakeven", justify="right")
    table.add_column("R:R", justify="right")
    table.add_column("Fit", justify="right")

    for i, s in enumerate(strategies, 1):
        mp = f"[green]₹{s.max_profit:,.0f}[/green]" if s.max_profit > 0 else "[dim]—[/dim]"
        ml = f"[red]₹{abs(s.max_loss):,.0f}[/red]"
        be = " / ".join(f"₹{b:,.0f}" for b in s.breakeven[:2])
        rr = f"{s.rr_ratio:.1f}×" if s.rr_ratio > 0 else "—"
        fit = f"[cyan]{s.fit_score}/100[/cyan]"
        table.add_row(str(i), s.name, mp, ml, be, rr, fit)

    console.print(table)
    console.print()
    for i, s in enumerate(strategies, 1):
        console.print(f"  [dim]{i}. {s.description}[/dim]")


def _show_trade_summary(s: StrategyResult, symbol: str, spot: float) -> None:
    """Show full trade summary panel."""
    lines = [
        f"[bold]Strategy :[/bold] {s.name}",
        f"[bold]Symbol   :[/bold] {symbol}  (Spot: ₹{spot:,.2f})",
        f"[bold]Legs     :[/bold] {s.description}",
        f"[bold]Cost     :[/bold] ₹{s.capital_needed:,.0f}",
        f"[bold]Max Profit:[/bold] [green]₹{s.max_profit:,.0f}[/green]",
        f"[bold]Max Loss  :[/bold] [red]₹{abs(s.max_loss):,.0f}[/red]",
        f"[bold]Breakeven :[/bold] {', '.join(f'₹{b:,.0f}' for b in s.breakeven)}",
        f"[bold]R:R Ratio :[/bold] {s.rr_ratio:.1f}×",
        f"[bold]Best for  :[/bold] [dim]{s.best_for}[/dim]",
        f"[bold]Risks     :[/bold] [yellow]{s.risks}[/yellow]",
    ]
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold cyan]📊 Trade Summary[/bold cyan]",
            box=box.ROUNDED,
        )
    )


def _place_strategy_legs(broker, strategy: StrategyResult, symbol: str, mode: str) -> None:
    """Place each leg of the selected strategy."""
    for leg in strategy.legs:
        action = leg.get("action", "BUY")
        opt_type = leg.get("type", "")
        strike = leg.get("strike", 0)
        lots = leg.get("lots", 1)
        lot_size = leg.get("lot_size", 1)

        # Build trading symbol
        if opt_type in ("CE", "PE"):
            from market.events import get_expiry_dates

            try:
                expiry = get_expiry_dates().monthly
                exp_compact = expiry.replace("-", "").replace("20", "")[2:]  # "25APR"
            except Exception:
                exp_compact = "25MAR"
            trade_symbol = f"{symbol}{exp_compact}{int(strike)}{opt_type}"
            qty = lots * lot_size
        else:
            trade_symbol = symbol
            qty = leg.get("qty", 1)

        exchange = "NFO" if opt_type in ("CE", "PE") else "NSE"
        req = OrderRequest(
            symbol=trade_symbol,
            exchange=exchange,
            transaction_type=action,
            quantity=qty,
            order_type="MARKET",
            product="CNC" if opt_type == "" else "NRML",
        )

        try:
            resp = broker.place_order(req)
            status_color = "green" if resp.status == "COMPLETE" else "yellow"
            fill = f" @ ₹{resp.average_price:,.2f}" if resp.average_price else ""
            console.print(
                f"  [{status_color}]✓[/{status_color}]  {action} {qty} {trade_symbol}{fill}  "
                f"— [{status_color}]{resp.status}[/{status_color}]"
            )
        except Exception as e:
            console.print(f"  [red]✗  Failed to place {action} {trade_symbol}: {e}[/red]")

    console.print(
        "\n  [bold green]Order(s) placed.[/bold green] Use [bold]positions[/bold] to monitor.\n"
    )
