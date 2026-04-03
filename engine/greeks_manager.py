"""
engine/greeks_manager.py
────────────────────────
Greeks-based position management — delta hedging, roll suggestions,
theta/gamma monitoring with actionable warnings.

Commands:
  greeks          Enhanced dashboard with warnings + actions
  delta-hedge     Suggest trades to neutralize portfolio delta
  roll-options    Find positions expiring soon, suggest rolls

Uses existing portfolio Greeks from engine/portfolio.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ── Lightweight Greeks container (for testing without broker) ─


@dataclass
class _PortfolioGreeksLike:
    """Minimal Greeks container matching PortfolioGreeks interface."""

    net_delta: float = 0.0
    net_theta: float = 0.0
    net_vega: float = 0.0
    net_gamma: float = 0.0
    positions_with_greeks: list = field(default_factory=list)
    by_underlying: dict = field(default_factory=dict)


# ── Delta Hedge ──────────────────────────────────────────────


@dataclass
class DeltaHedgeSuggestion:
    current_delta: float
    target_delta: float
    gap: float  # how much delta to add (positive) or remove (negative)
    suggestions: list[dict]  # [{"action", "instrument", "lots", "delta_change"}]
    cost_estimate: float = 0.0


def compute_delta_hedge(
    net_delta: float,
    target_delta: float = 0.0,
    lot_size: int = 25,
    underlying: str = "NIFTY",
    tolerance: float = 10.0,
) -> DeltaHedgeSuggestion:
    """
    Compute trades needed to move portfolio delta toward target.

    Args:
        net_delta: current net portfolio delta
        target_delta: desired delta (0 = delta-neutral)
        lot_size: lot size for the hedging instrument
        underlying: index/stock for hedging
        tolerance: don't hedge if gap is within this range

    Returns:
        DeltaHedgeSuggestion with concrete trade suggestions.
    """
    gap = target_delta - net_delta  # positive = need to buy, negative = need to sell
    suggestions = []

    if abs(gap) <= tolerance:
        return DeltaHedgeSuggestion(
            current_delta=net_delta,
            target_delta=target_delta,
            gap=gap,
            suggestions=[],
        )

    # Futures hedge (delta ≈ 1.0 per lot × lot_size)
    delta_per_lot = lot_size  # 1 future lot = lot_size delta
    lots_needed = abs(gap) / delta_per_lot
    lots_rounded = math.ceil(lots_needed)

    if gap > 0:
        # Need positive delta: BUY futures
        suggestions.append(
            {
                "action": "BUY",
                "instrument": f"{underlying} FUT (nearest expiry)",
                "lots": lots_rounded,
                "delta_change": f"+{lots_rounded * delta_per_lot:.0f}",
                "note": f"Adds +{lots_rounded * delta_per_lot:.0f} delta",
            }
        )
    else:
        # Need negative delta: SELL futures
        suggestions.append(
            {
                "action": "SELL",
                "instrument": f"{underlying} FUT (nearest expiry)",
                "lots": lots_rounded,
                "delta_change": f"-{lots_rounded * delta_per_lot:.0f}",
                "note": f"Reduces delta by {lots_rounded * delta_per_lot:.0f}",
            }
        )

    # Also suggest options alternative
    if abs(gap) > 50:
        if gap > 0:
            suggestions.append(
                {
                    "action": "BUY",
                    "instrument": f"{underlying} ATM CE (alternative)",
                    "lots": lots_rounded * 2,  # delta ~0.5 per option
                    "delta_change": f"+{lots_rounded * delta_per_lot:.0f}",
                    "note": "Options: ~0.5 delta per lot, need 2x lots",
                }
            )
        else:
            suggestions.append(
                {
                    "action": "BUY",
                    "instrument": f"{underlying} ATM PE (alternative)",
                    "lots": lots_rounded * 2,
                    "delta_change": f"-{lots_rounded * delta_per_lot:.0f}",
                    "note": "Options: ~-0.5 delta per lot, need 2x lots",
                }
            )

    return DeltaHedgeSuggestion(
        current_delta=net_delta,
        target_delta=target_delta,
        gap=gap,
        suggestions=suggestions,
    )


# ── Roll Suggestions ─────────────────────────────────────────


@dataclass
class RollSuggestion:
    current_symbol: str
    current_expiry: str
    current_dte: int
    current_premium: float
    next_expiry: str
    next_premium: float
    roll_cost: float  # positive = credit, negative = debit
    recommendation: str  # "ROLL" | "LET EXPIRE" | "CLOSE"
    reason: str


def compute_roll_suggestions(
    positions: list[dict],
    dte_threshold: int = 3,
) -> list[RollSuggestion]:
    """
    Find F&O positions expiring soon and suggest rolls.

    Args:
        positions: list of position dicts with keys:
            symbol, underlying, expiry, strike, option_type, qty, ltp
        dte_threshold: suggest rolls for positions with DTE <= this

    Returns:
        List of RollSuggestion for positions needing attention.
    """
    today = date.today()
    suggestions = []

    for pos in positions:
        expiry_str = pos.get("expiry", "")
        if not expiry_str:
            continue

        try:
            expiry_date = date.fromisoformat(expiry_str[:10])
        except (ValueError, TypeError):
            continue

        dte = (expiry_date - today).days
        if dte > dte_threshold:
            continue

        ltp = pos.get("ltp", 0)

        # Next weekly expiry: current + 7 days (approximate)
        next_expiry = expiry_date + timedelta(days=7)
        # Rough estimate: next expiry premium ≈ current + time value bump
        next_premium_estimate = ltp * 1.5 if ltp > 0 else 0

        # Recommendation logic
        if dte <= 0:
            rec = "CLOSE"
            reason = "Already expired or expiring today"
        elif ltp < 5:
            rec = "LET EXPIRE"
            reason = f"Premium too low (₹{ltp:.1f}) — not worth rolling"
        else:
            rec = "ROLL"
            reason = f"Expiring in {dte}d with ₹{ltp:.1f} premium — roll to preserve position"

        roll_cost = next_premium_estimate - ltp if rec == "ROLL" else 0

        suggestions.append(
            RollSuggestion(
                current_symbol=pos.get("symbol", ""),
                current_expiry=expiry_str,
                current_dte=dte,
                current_premium=ltp,
                next_expiry=next_expiry.isoformat(),
                next_premium=round(next_premium_estimate, 2),
                roll_cost=round(roll_cost, 2),
                recommendation=rec,
                reason=reason,
            )
        )

    return suggestions


# ── Greeks Dashboard ─────────────────────────────────────────


@dataclass
class GreeksDashboard:
    net_delta: float
    net_theta: float
    net_vega: float
    net_gamma: float
    warnings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    risk_level: str = "LOW"


# Thresholds for warnings
DELTA_WARN = 200  # net delta above this = directionally exposed
THETA_WARN = -500  # daily theta below this = heavy time decay
GAMMA_WARN = 1.0  # gamma above this = high gamma risk
VEGA_WARN = 500  # vega above this = significant IV exposure


def build_dashboard(
    net_delta: float = 0,
    net_theta: float = 0,
    net_vega: float = 0,
    net_gamma: float = 0,
) -> GreeksDashboard:
    """
    Build a Greeks dashboard with warnings and action items.

    Args:
        net_delta/theta/vega/gamma: portfolio-level Greeks

    Returns:
        GreeksDashboard with risk classification, warnings, and actions.
    """
    warnings = []
    actions = []
    risk_score = 0

    # Delta check
    if abs(net_delta) > DELTA_WARN:
        direction = "LONG" if net_delta > 0 else "SHORT"
        warnings.append(
            f"High delta exposure: {net_delta:+.0f} ({direction}) — "
            f"portfolio is directionally exposed"
        )
        actions.append(
            f"Delta-hedge: {'sell' if net_delta > 0 else 'buy'} "
            f"~{abs(net_delta) / 25:.0f} NIFTY lots to neutralize"
        )
        risk_score += 2

    # Theta check
    if net_theta < THETA_WARN:
        warnings.append(
            f"Heavy theta decay: ₹{abs(net_theta):,.0f}/day — "
            f"losing ₹{abs(net_theta) * 5:,.0f}/week in time value"
        )
        actions.append("Close or roll short-dated positions to reduce theta bleed")
        risk_score += 2

    # Gamma check
    if abs(net_gamma) > GAMMA_WARN:
        warnings.append(
            f"High gamma: {net_gamma:+.2f} — delta will change rapidly with price moves"
        )
        actions.append("Reduce gamma exposure before expiry — close or roll near-expiry options")
        risk_score += 3

    # Vega check
    if abs(net_vega) > VEGA_WARN:
        warnings.append(
            f"Significant vega exposure: ₹{net_vega:,.0f} per 1% IV move — "
            f"{'long' if net_vega > 0 else 'short'} volatility"
        )
        actions.append(
            f"{'IV crush will hurt' if net_vega > 0 else 'IV spike will hurt'} — "
            "consider hedging with opposite vega position"
        )
        risk_score += 1

    # Risk level
    if risk_score >= 5:
        risk_level = "CRITICAL"
    elif risk_score >= 3:
        risk_level = "HIGH"
    elif risk_score >= 1:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return GreeksDashboard(
        net_delta=net_delta,
        net_theta=net_theta,
        net_vega=net_vega,
        net_gamma=net_gamma,
        warnings=warnings,
        actions=actions,
        risk_level=risk_level,
    )


# ── Display Functions ────────────────────────────────────────


def print_delta_hedge(suggestion: DeltaHedgeSuggestion) -> None:
    """Display delta hedge suggestions as Rich panel."""
    lines = [
        f"  Current Delta  : [bold]{suggestion.current_delta:+.1f}[/bold]",
        f"  Target Delta   : {suggestion.target_delta:+.1f}",
        f"  Gap            : {suggestion.gap:+.1f}",
    ]

    if not suggestion.suggestions:
        lines.append("\n  [green]Portfolio is within tolerance — no hedge needed.[/green]")
    else:
        lines.append("\n  [bold]Suggested Trades:[/bold]")
        for s in suggestion.suggestions:
            action_color = "red" if s["action"] == "SELL" else "green"
            lines.append(
                f"    [{action_color}]{s['action']:4s}[/{action_color}] "
                f"{s['instrument']}  ×{s['lots']}  ({s['delta_change']} delta)"
            )
            if s.get("note"):
                lines.append(f"    [dim]{s['note']}[/dim]")

    console.print(
        Panel(
            "\n".join(lines),
            title="[bold cyan]Delta Hedge Suggestion[/bold cyan]",
            border_style="cyan",
        )
    )


def print_roll_suggestions(suggestions: list[RollSuggestion]) -> None:
    """Display roll suggestions as Rich table."""
    if not suggestions:
        console.print("[dim]No positions need rolling at this time.[/dim]")
        return

    table = Table(title="Roll Suggestions", show_lines=True)
    table.add_column("Symbol", style="cyan")
    table.add_column("Expiry", width=12)
    table.add_column("DTE", justify="right", width=5)
    table.add_column("Premium", justify="right")
    table.add_column("Action", width=12)
    table.add_column("Reason")

    for s in suggestions:
        rec_color = {"ROLL": "yellow", "LET EXPIRE": "dim", "CLOSE": "red"}.get(
            s.recommendation, "white"
        )
        table.add_row(
            s.current_symbol[:20],
            s.current_expiry[:10],
            str(s.current_dte),
            f"₹{s.current_premium:,.1f}",
            f"[{rec_color}]{s.recommendation}[/{rec_color}]",
            s.reason[:50],
        )

    console.print(table)


def print_dashboard(dash: GreeksDashboard) -> None:
    """Display enhanced Greeks dashboard with warnings."""
    risk_colors = {"LOW": "green", "MODERATE": "yellow", "HIGH": "red", "CRITICAL": "bold red"}
    risk_color = risk_colors.get(dash.risk_level, "white")

    lines = [
        f"  Δ Delta  : [cyan]{dash.net_delta:+.1f}[/cyan]",
        f"  Θ Theta  : [red]₹{dash.net_theta:,.0f}/day[/red]",
        f"  ν Vega   : [yellow]₹{dash.net_vega:,.0f} per 1% IV[/yellow]",
        f"  Γ Gamma  : {dash.net_gamma:+.3f}",
        f"\n  Risk Level: [{risk_color}]{dash.risk_level}[/{risk_color}]",
    ]

    if dash.warnings:
        lines.append("\n  [bold]⚠  Warnings:[/bold]")
        for w in dash.warnings:
            lines.append(f"    [yellow]• {w}[/yellow]")

    if dash.actions:
        lines.append("\n  [bold]Actions:[/bold]")
        for a in dash.actions:
            lines.append(f"    → {a}")

    console.print(
        Panel(
            "\n".join(lines),
            title="[bold cyan]Greeks Dashboard[/bold cyan]",
            border_style="cyan",
        )
    )
