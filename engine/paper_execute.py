"""
engine/paper_execute.py
───────────────────────
Execute trade plans in paper trading mode.

After `analyze RELIANCE` generates a trade plan, the user can run:
    paper-execute          → execute the neutral risk plan
    paper-execute aggressive  → execute the aggressive plan
    paper-execute conservative → execute the conservative plan

This places paper orders using the PaperBroker (or mock broker),
simulating real execution without risk.

Usage:
    from engine.paper_execute import execute_trade_plan

    execute_trade_plan(trade_plan, broker)
"""

from __future__ import annotations


from rich.console import Console
from rich.panel import Panel

from brokers.base import OrderRequest, BrokerAPI

console = Console()


def execute_trade_plan(plan, broker: BrokerAPI) -> list[dict]:
    """
    Execute a TradePlan by placing paper orders.

    Args:
        plan: TradePlan from engine/trader.py
        broker: BrokerAPI instance (paper or real)

    Returns:
        List of order results [{order_id, symbol, status, ...}]
    """
    if plan is None:
        console.print("[dim]No trade plan to execute (verdict was HOLD).[/dim]")
        return []

    results = []
    console.print()
    console.print(
        Panel(
            f"  Executing: [bold]{plan.strategy_name}[/bold] on {plan.symbol}\n"
            f"  Mode: {'PAPER' if _is_paper(broker) else 'LIVE'}\n"
            f"  Orders: {len(plan.entry_orders)}",
            title="[bold yellow]Order Execution[/bold yellow]",
            border_style="yellow",
        )
    )

    for i, leg in enumerate(plan.entry_orders, 1):
        try:
            order_req = OrderRequest(
                symbol=leg.instrument.split()[0],  # "RELIANCE" from "RELIANCE ATM CE"
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
                }
            )

    # Show exit plan reminder
    if plan.exit_plan:
        ep = plan.exit_plan
        console.print(
            f"\n  [bold]Exit Plan (set these manually or as alerts):[/bold]\n"
            f"  Stop-Loss : {ep.stop_loss:,.2f} ({ep.stop_loss_pct:+.1f}%)\n"
            f"  Target 1  : {ep.target_1:,.2f} ({ep.target_1_pct:+.1f}%) → {ep.target_1_action}\n"
            f"  Target 2  : {ep.target_2:,.2f} ({ep.target_2_pct:+.1f}%) → {ep.target_2_action}"
            if ep.target_2
            else ""
        )

        # Auto-create alerts for SL and targets
        try:
            from engine.alerts import alert_manager

            alert_manager.add_price_alert(
                plan.symbol,
                "BELOW",
                ep.stop_loss,
                plan.exchange,
            )
            alert_manager.add_price_alert(
                plan.symbol,
                "ABOVE",
                ep.target_1,
                plan.exchange,
            )
            console.print("[dim]  Auto-created alerts for SL and Target 1.[/dim]")
        except Exception:
            pass

    console.print()
    return results


def _is_paper(broker: BrokerAPI) -> bool:
    """Check if the broker is a paper/mock broker."""
    try:
        profile = broker.get_profile()
        return profile.broker.upper() in ("PAPER", "MOCK", "DEMO")
    except Exception:
        return True
