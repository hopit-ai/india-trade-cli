"""
engine/trade_executor.py
────────────────────────
Execute trade plans against any connected broker — paper or live.

After `analyze RELIANCE` generates trade plans, the user runs:
    execute                  → neutral risk plan
    execute aggressive       → aggressive plan
    execute conservative     → conservative plan

Live mode (Fyers or any real broker connected):
  - Shows the full order before sending
  - Requires explicit "yes" confirmation
  - Respects TRADING_MODE=PAPER env override (refuses live execution)
  - Auto-creates SL and target alerts after execution

Paper mode (Mock/Demo broker):
  - No confirmation needed — no real money at stake
  - Same output format so behaviour is identical

Usage:
    from engine.trade_executor import execute_trade_plan

    execute_trade_plan(plan, broker)
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from brokers.base import BrokerAPI, OrderRequest

console = Console()


# ── Position sizing utilities ─────────────────────────────────


def get_trading_capital() -> float:
    """Read TRADING_CAPITAL from env. Default ₹1,00,000."""
    return float(os.environ.get("TRADING_CAPITAL", "100000"))


def parse_qty_or_pct(arg: str) -> tuple[float, bool]:
    """
    Parse a buy/sell quantity argument.

    Returns:
        (value, is_pct) where is_pct=True means value is a percentage (0–100),
        is_pct=False means value is a fixed quantity.

    Examples:
        "5%"  → (5.0, True)
        "100" → (100.0, False)
        "2.5%"→ (2.5, True)

    Raises:
        ValueError: if percentage is <= 0 or not a valid number
    """
    arg = arg.strip()
    if arg.endswith("%"):
        raw = float(arg[:-1])
        if raw <= 0:
            raise ValueError(f"Percentage must be > 0, got '{arg}'")
        return raw, True
    return float(arg), False


def size_by_pct(
    symbol: str,
    pct: float,
    capital: float,
    limit_price: float | None = None,
) -> int:
    """
    Compute share quantity from a percentage of capital.

    Args:
        symbol:      Stock symbol (used to fetch LTP if no limit_price)
        pct:         Percentage of capital (0.0–100.0)
        capital:     Total capital in INR
        limit_price: Price to size against. If None, fetches live LTP.

    Returns:
        Integer quantity (≥ 1)

    Raises:
        ValueError: if resulting quantity is 0 or pct exceeds MAX_POSITION_PCT
    """
    max_pct = float(os.environ.get("MAX_POSITION_PCT", "100"))
    if pct > max_pct:
        raise ValueError(
            f"Position size {pct:.1f}% exceeds MAX_POSITION_PCT={max_pct:.0f}%. "
            f"Set MAX_POSITION_PCT env var to allow larger positions."
        )

    if limit_price is None or limit_price <= 0:
        try:
            from market.quotes import get_ltp

            limit_price = get_ltp(f"NSE:{symbol.upper()}")
        except Exception:
            limit_price = None

    if not limit_price or limit_price <= 0:
        raise ValueError(f"Cannot compute quantity — no price available for {symbol}")

    allocation = capital * pct / 100.0
    qty = int(allocation / limit_price)

    if qty <= 0:
        raise ValueError(
            f"Position size too small: {pct:.1f}% of ₹{capital:,.0f} = ₹{allocation:,.0f} "
            f"is not enough to buy 1 share of {symbol} at ₹{limit_price:,.2f}. "
            f"Increase capital or reduce percentage."
        )

    return qty


# ── Mode detection ────────────────────────────────────────────


def _is_paper(broker: BrokerAPI) -> bool:
    """True when connected to a paper / mock / demo broker."""
    try:
        profile = broker.get_profile()
        return profile.broker.upper() in ("PAPER", "MOCK", "DEMO")
    except Exception:
        return True  # fail safe


def _trading_mode_override() -> str:
    """Read TRADING_MODE env var. Returns 'PAPER' or 'LIVE'."""
    return os.environ.get("TRADING_MODE", "PAPER").upper()


def is_live_execution_allowed(broker: BrokerAPI) -> bool:
    """
    Live execution is only allowed when:
      1. The broker is a real broker (not Mock/Paper/Demo), AND
      2. TRADING_MODE is not forced to PAPER via environment
    """
    if _is_paper(broker):
        return False
    if _trading_mode_override() == "PAPER":
        return False
    return True


# ── Confirmation prompt ────────────────────────────────────────


def _show_order_preview(plan, broker: BrokerAPI) -> None:
    """Print a clear summary of what is about to be sent to the broker."""
    try:
        profile = broker.get_profile()
        broker_name = profile.broker
    except Exception:
        broker_name = "Unknown"

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Leg")
    table.add_column("Action")
    table.add_column("Instrument")
    table.add_column("Qty", justify="right")
    table.add_column("Type")
    table.add_column("Price", justify="right")

    for i, leg in enumerate(plan.entry_orders, 1):
        price_str = f"₹{leg.price:,.2f}" if leg.price else "MARKET"
        table.add_row(
            str(i),
            f"[{'green' if leg.action == 'BUY' else 'red'}]{leg.action}[/]",
            leg.instrument,
            str(leg.quantity),
            leg.order_type,
            price_str,
        )

    ep = plan.exit_plan
    console.print()
    console.print(
        Panel(
            f"  Strategy : {plan.strategy_name}\n"
            f"  Symbol   : {plan.symbol}\n"
            f"  Broker   : [bold]{broker_name}[/bold]\n"
            f"  Orders   : {len(plan.entry_orders)}\n"
            + (
                f"  Stop-Loss: ₹{ep.stop_loss:,.2f} ({ep.stop_loss_pct:+.1f}%)\n"
                f"  Target 1 : ₹{ep.target_1:,.2f} ({ep.target_1_pct:+.1f}%)"
                if ep
                else ""
            ),
            title="[bold red]⚠  LIVE ORDER PREVIEW[/bold red]",
            border_style="red",
        )
    )
    console.print(table)
    console.print()


# ── Core executor ─────────────────────────────────────────────


def execute_trade_plan(
    plan,
    broker: BrokerAPI,
    skip_confirmation: bool = False,
) -> list[dict]:
    """
    Execute a TradePlan by placing orders with the broker.

    For live brokers: shows full order preview and requires explicit
    confirmation before sending anything to the exchange.

    For paper brokers: executes immediately with no confirmation.

    Args:
        plan:               TradePlan from engine/trader.py
        broker:             Connected BrokerAPI instance
        skip_confirmation:  True only for programmatic callers that have
                            already shown their own confirmation UI
                            (e.g. Telegram inline button).

    Returns:
        List of order results [{order_id, symbol, status, ...}]
    """
    if plan is None:
        console.print("[dim]No trade plan to execute (verdict was HOLD).[/dim]")
        return []

    live = is_live_execution_allowed(broker)

    # ── Live execution gate ───────────────────────────────────
    if live and not skip_confirmation:
        _show_order_preview(plan, broker)
        confirmed = Confirm.ask(
            "[bold red]Send these orders to the exchange? This uses real money.[/bold red]",
            default=False,
        )
        if not confirmed:
            console.print("[dim]Execution cancelled.[/dim]")
            return []

    # ── Paper override warning ────────────────────────────────
    if not live and not _is_paper(broker):
        console.print(
            "[yellow]  TRADING_MODE=PAPER is set — executing as paper trade "
            "even though a live broker is connected.[/yellow]"
        )

    mode_label = "LIVE" if live else "PAPER"
    mode_style = "bold red" if live else "bold green"

    console.print()
    console.print(
        Panel(
            f"  [{mode_style}]{mode_label}[/{mode_style}]  {plan.strategy_name} on {plan.symbol}\n"
            f"  Orders: {len(plan.entry_orders)}",
            title=f"[{mode_style}]Order Execution[/{mode_style}]",
            border_style="red" if live else "green",
        )
    )

    results = []
    for i, leg in enumerate(plan.entry_orders, 1):
        try:
            # ── Hard risk limit check ─────────────────────────
            try:
                from engine.risk_limits import risk_limits, RiskLimitError as _RLE

                risk_limits.check(
                    symbol=leg.instrument.split()[0],
                    action=leg.action,
                    quantity=leg.quantity,
                    price=leg.price or 0.0,
                )
            except _RLE as _rle:
                console.print(f"\n  [bold red]🛑 RISK LIMIT BLOCKED:[/bold red] {_rle}")
                results.append(
                    {
                        "symbol": leg.instrument,
                        "action": leg.action,
                        "quantity": leg.quantity,
                        "status": "BLOCKED",
                        "message": str(_rle),
                        "mode": mode_label,
                    }
                )
                continue

            order_req = OrderRequest(
                symbol=leg.instrument.split()[0],
                exchange=leg.exchange,
                transaction_type=leg.action,
                quantity=leg.quantity,
                order_type=leg.order_type,
                product=leg.product,
                price=leg.price,
                trigger_price=leg.trigger_price,
                tag=leg.tag or f"plan_{plan.symbol}",
            )

            response = broker.place_order(order_req)
            # Record trade for risk tracking
            try:
                from engine.risk_limits import risk_limits as _rl

                _rl.record_trade(
                    symbol=leg.instrument.split()[0],
                    action=leg.action,
                    quantity=leg.quantity,
                    price=leg.price or 0.0,
                )
            except Exception:
                pass
            status_style = "green" if response.status in ("COMPLETE", "OPEN") else "red"

            console.print(
                f"  [{i}] {leg.action} {leg.quantity} {leg.instrument} "
                f"({leg.order_type}) → [{status_style}]{response.status}[/{status_style}] "
                f"(ID: {response.order_id})"
            )

            results.append(
                {
                    "order_id": response.order_id,
                    "symbol": leg.instrument,
                    "action": leg.action,
                    "quantity": leg.quantity,
                    "status": response.status,
                    "message": response.message,
                    "mode": mode_label,
                }
            )

        except Exception as e:
            console.print(
                f"  [{i}] {leg.action} {leg.quantity} {leg.instrument} → [red]FAILED: {e}[/red]"
            )
            results.append(
                {
                    "symbol": leg.instrument,
                    "action": leg.action,
                    "quantity": leg.quantity,
                    "status": "FAILED",
                    "message": str(e),
                    "mode": mode_label,
                }
            )

    # ── Exit plan reminder + auto-alerts ─────────────────────
    if plan.exit_plan:
        ep = plan.exit_plan
        lines = [
            "\n  [bold]Exit Plan (set these as orders when appropriate):[/bold]",
            f"  Stop-Loss : ₹{ep.stop_loss:,.2f} ({ep.stop_loss_pct:+.1f}%)",
            f"  Target 1  : ₹{ep.target_1:,.2f} ({ep.target_1_pct:+.1f}%) → {ep.target_1_action}",
        ]
        if ep.target_2:
            lines.append(
                f"  Target 2  : ₹{ep.target_2:,.2f} ({ep.target_2_pct:+.1f}%) → {ep.target_2_action}"
            )
        console.print("\n".join(lines))

        try:
            from engine.alerts import alert_manager

            alert_manager.add_price_alert(plan.symbol, "BELOW", ep.stop_loss, plan.exchange)
            alert_manager.add_price_alert(plan.symbol, "ABOVE", ep.target_1, plan.exchange)
            console.print("[dim]  Auto-created price alerts for stop-loss and target.[/dim]")
        except Exception:
            pass

    console.print()
    return results
