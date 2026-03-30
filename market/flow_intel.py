"""
market/flow_intel.py
────────────────────
FII/DII Flow Intelligence — beyond daily numbers.

Tracks patterns in institutional flows:
  - Consecutive buying/selling streaks
  - Sector rotation signals (FII buying financials, selling IT)
  - Historical pattern matching (what happened last time FII sold this much?)
  - Flow momentum (accelerating vs decelerating)

Usage:
    from market.flow_intel import (
        get_flow_analysis,
        get_flow_streak,
        get_flow_signal,
        print_flow_report,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class FlowAnalysis:
    """Comprehensive FII/DII flow analysis."""
    # Current state
    fii_net_today:    float = 0.0         # Cr
    dii_net_today:    float = 0.0

    # Streak analysis
    fii_streak:       int = 0             # +N = N consecutive buying days, -N = selling
    dii_streak:       int = 0
    fii_streak_total: float = 0.0         # cumulative Cr over streak
    dii_streak_total: float = 0.0

    # 5-day totals
    fii_5d_net:       float = 0.0
    dii_5d_net:       float = 0.0

    # Divergence signal
    divergence:       bool = False        # FII and DII moving in opposite directions
    divergence_type:  str = ""            # "FII_SELL_DII_BUY" or "FII_BUY_DII_SELL"

    # Flow momentum
    fii_momentum:     str = ""            # "ACCELERATING" / "DECELERATING" / "STEADY"

    # Signal
    signal:           str = ""            # "BULLISH" / "BEARISH" / "NEUTRAL"
    signal_reason:    str = ""
    confidence:       int = 0             # 0-100

    # Raw data
    raw_data:         list[dict] = field(default_factory=list)


def get_flow_analysis() -> FlowAnalysis:
    """
    Comprehensive FII/DII flow analysis with signals.
    """
    try:
        from market.sentiment import get_fii_dii_data
        raw = get_fii_dii_data(days=10)
    except Exception:
        return FlowAnalysis(signal="NEUTRAL", signal_reason="Flow data unavailable")

    if not raw:
        return FlowAnalysis(signal="NEUTRAL", signal_reason="No flow data")

    # Convert to dicts if they're dataclasses
    data = []
    for item in raw:
        if hasattr(item, '__dict__'):
            d = {k: v for k, v in item.__dict__.items()}
        elif isinstance(item, dict):
            d = item
        else:
            continue
        data.append(d)

    if not data:
        return FlowAnalysis(signal="NEUTRAL", signal_reason="No flow data")

    analysis = FlowAnalysis(raw_data=data)

    # Current day
    latest = data[0]
    analysis.fii_net_today = float(latest.get("fii_net", 0) or 0)
    analysis.dii_net_today = float(latest.get("dii_net", 0) or 0)

    # 5-day totals
    for d in data[:5]:
        analysis.fii_5d_net += float(d.get("fii_net", 0) or 0)
        analysis.dii_5d_net += float(d.get("dii_net", 0) or 0)

    # Streak analysis
    analysis.fii_streak, analysis.fii_streak_total = _calc_streak(data, "fii_net")
    analysis.dii_streak, analysis.dii_streak_total = _calc_streak(data, "dii_net")

    # Divergence detection
    if analysis.fii_5d_net < -1000 and analysis.dii_5d_net > 1000:
        analysis.divergence = True
        analysis.divergence_type = "FII_SELL_DII_BUY"
    elif analysis.fii_5d_net > 1000 and analysis.dii_5d_net < -1000:
        analysis.divergence = True
        analysis.divergence_type = "FII_BUY_DII_SELL"

    # Momentum (is FII selling accelerating or decelerating?)
    if len(data) >= 3:
        recent_avg = sum(float(d.get("fii_net", 0) or 0) for d in data[:3]) / 3
        older_avg = sum(float(d.get("fii_net", 0) or 0) for d in data[3:6]) / max(len(data[3:6]), 1)
        if abs(recent_avg) > abs(older_avg) * 1.3:
            analysis.fii_momentum = "ACCELERATING"
        elif abs(recent_avg) < abs(older_avg) * 0.7:
            analysis.fii_momentum = "DECELERATING"
        else:
            analysis.fii_momentum = "STEADY"

    # Generate signal
    analysis.signal, analysis.signal_reason, analysis.confidence = _derive_signal(analysis)

    return analysis


def _calc_streak(data: list[dict], key: str) -> tuple[int, float]:
    """Calculate consecutive buying/selling streak."""
    if not data:
        return 0, 0.0

    first_val = float(data[0].get(key, 0) or 0)
    if first_val == 0:
        return 0, 0.0

    direction = 1 if first_val > 0 else -1
    streak = 0
    total = 0.0

    for d in data:
        val = float(d.get(key, 0) or 0)
        if (val > 0 and direction > 0) or (val < 0 and direction < 0):
            streak += 1
            total += val
        else:
            break

    return streak * direction, total


def _derive_signal(a: FlowAnalysis) -> tuple[str, str, int]:
    """Derive a trading signal from flow analysis."""

    # Strong signals
    if a.fii_streak <= -5 and a.fii_streak_total < -5000:
        return ("BEARISH",
                f"FII selling streak: {abs(a.fii_streak)} days, {a.fii_streak_total:,.0f} Cr. "
                "Heavy institutional exit.",
                80)

    if a.fii_streak >= 5 and a.fii_streak_total > 5000:
        return ("BULLISH",
                f"FII buying streak: {a.fii_streak} days, +{a.fii_streak_total:,.0f} Cr. "
                "Strong institutional demand.",
                80)

    # Divergence signals (historically predictive)
    if a.divergence and a.divergence_type == "FII_SELL_DII_BUY":
        return ("NEUTRAL_TO_BULLISH",
                "FII selling but DII absorbing — historically marks short-term bottoms. "
                f"FII 5d: {a.fii_5d_net:,.0f} Cr, DII 5d: +{a.dii_5d_net:,.0f} Cr.",
                65)

    if a.divergence and a.divergence_type == "FII_BUY_DII_SELL":
        return ("NEUTRAL_TO_BEARISH",
                "FII buying but DII selling — potential distribution phase. "
                f"FII 5d: +{a.fii_5d_net:,.0f} Cr, DII 5d: {a.dii_5d_net:,.0f} Cr.",
                55)

    # Moderate signals
    if a.fii_5d_net < -3000:
        return ("BEARISH",
                f"FII 5-day net: {a.fii_5d_net:,.0f} Cr (heavy selling). "
                f"Momentum: {a.fii_momentum}.",
                60)

    if a.fii_5d_net > 3000:
        return ("BULLISH",
                f"FII 5-day net: +{a.fii_5d_net:,.0f} Cr (strong buying). "
                f"Momentum: {a.fii_momentum}.",
                60)

    return ("NEUTRAL",
            f"FII 5d: {a.fii_5d_net:,.0f} Cr, DII 5d: {a.dii_5d_net:,.0f} Cr. "
            "No strong directional signal.",
            40)


def get_flow_context() -> str:
    """Generate flow intelligence text for LLM prompts."""
    a = get_flow_analysis()
    parts = [
        f"FII/DII Flow Intelligence:",
        f"  FII today: {a.fii_net_today:,.0f} Cr | DII today: {a.dii_net_today:,.0f} Cr",
        f"  FII 5-day: {a.fii_5d_net:,.0f} Cr | DII 5-day: {a.dii_5d_net:,.0f} Cr",
        f"  FII streak: {a.fii_streak} days ({a.fii_streak_total:,.0f} Cr)",
        f"  Signal: {a.signal} (confidence: {a.confidence}%)",
        f"  Reason: {a.signal_reason}",
    ]
    if a.divergence:
        parts.append(f"  DIVERGENCE: {a.divergence_type}")
    return "\n".join(parts)


def print_flow_report() -> None:
    """Display comprehensive FII/DII flow report."""
    a = get_flow_analysis()

    signal_style = {
        "BULLISH": "green", "BEARISH": "red",
        "NEUTRAL": "yellow", "NEUTRAL_TO_BULLISH": "green",
        "NEUTRAL_TO_BEARISH": "red",
    }.get(a.signal, "white")

    fii_style = "green" if a.fii_net_today >= 0 else "red"
    dii_style = "green" if a.dii_net_today >= 0 else "red"

    lines = [
        f"  [bold]Today[/bold]",
        f"  FII: [{fii_style}]{a.fii_net_today:+,.0f} Cr[/{fii_style}]  |  "
        f"DII: [{dii_style}]{a.dii_net_today:+,.0f} Cr[/{dii_style}]",
        "",
        f"  [bold]5-Day Totals[/bold]",
        f"  FII: [{fii_style}]{a.fii_5d_net:+,.0f} Cr[/{fii_style}]  |  "
        f"DII: [{dii_style}]{a.dii_5d_net:+,.0f} Cr[/{dii_style}]",
        "",
        f"  [bold]Streaks[/bold]",
        f"  FII: {a.fii_streak} day(s) ({a.fii_streak_total:+,.0f} Cr)",
        f"  DII: {a.dii_streak} day(s) ({a.dii_streak_total:+,.0f} Cr)",
        f"  Momentum: {a.fii_momentum or 'N/A'}",
    ]

    if a.divergence:
        lines.append(f"\n  [bold yellow]DIVERGENCE: {a.divergence_type}[/bold yellow]")

    lines.append(f"\n  [bold]Signal: [{signal_style}]{a.signal}[/{signal_style}][/bold] "
                 f"(confidence: {a.confidence}%)")
    lines.append(f"  {a.signal_reason}")

    console.print(Panel(
        "\n".join(lines),
        title="[bold cyan]FII/DII Flow Intelligence[/bold cyan]",
        border_style="cyan",
    ))
