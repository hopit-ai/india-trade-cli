"""
app/commands/morning_brief.py
──────────────────────────────
Morning brief command — generates a daily market context via the AI agent.

Calling sequence (Claude tool calls):
  1. get_market_snapshot → NIFTY, BANKNIFTY, VIX, posture
  2. get_market_news     → top 5 overnight headlines
  3. get_fii_dii_data    → yesterday's institutional flows
  4. get_market_breadth  → advance/decline ratio
  5. get_upcoming_events → expiry dates, RBI, earnings today

Output: rich terminal panel with narrative + recommended posture.

Also supports a raw (non-AI) fallback that prints structured data directly
when called with use_agent=False — useful for testing without API keys.
"""

from __future__ import annotations

from datetime import datetime
import pytz

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

IST = pytz.timezone("Asia/Kolkata")


def run(use_agent: bool = True) -> None:
    """
    Entry point for `morning-brief` command.

    Args:
        use_agent: If True, delegates to AI agent for narrative.
                   If False, prints raw data directly (faster, no API needed).
    """
    now_ist = datetime.now(IST).strftime("%d %b %Y  %I:%M %p IST")
    console.print()
    console.print(
        Panel(
            f"[bold cyan]🌅  Morning Market Brief[/bold cyan]   [dim]{now_ist}[/dim]",
            box=box.SIMPLE_HEAVY,
            style="cyan",
        )
    )

    if use_agent:
        _run_with_agent()
    else:
        _run_raw()


def _run_with_agent() -> None:
    """Delegate to AI agent — it calls tools and generates the full brief."""
    from agent.core import get_agent

    agent = get_agent()
    agent.run_command("morning_brief")


def _run_raw() -> None:
    """
    Print structured market data directly without AI narrative.
    Useful for quick checks or when API key is not configured.
    """
    from market.indices import get_market_snapshot
    from market.news import get_market_news
    from market.sentiment import get_fii_dii_data, get_market_breadth
    from market.events import get_upcoming_events

    # ── Market snapshot ───────────────────────────────────────
    try:
        snap = get_market_snapshot()
        _print_snapshot(snap)
    except Exception as e:
        console.print(f"[red]Market snapshot unavailable: {e}[/red]")

    # ── News ──────────────────────────────────────────────────
    try:
        news = get_market_news(5)
        _print_news(news)
    except Exception as e:
        console.print(f"[red]News unavailable: {e}[/red]")

    # ── FII / DII ─────────────────────────────────────────────
    try:
        fii = get_fii_dii_data(3)
        _print_fii(fii)
    except Exception as e:
        console.print(f"[red]FII/DII data unavailable: {e}[/red]")

    # ── Market breadth ────────────────────────────────────────
    try:
        breadth = get_market_breadth()
        _print_breadth(breadth)
    except Exception as e:
        console.print(f"[red]Breadth data unavailable: {e}[/red]")

    # ── Events ────────────────────────────────────────────────
    try:
        events = get_upcoming_events(7)
        _print_events(events)
    except Exception as e:
        console.print(f"[red]Events unavailable: {e}[/red]")

    # ── Perplexity Finance macro context (best-effort) ────────
    try:
        from agent.perplexity_finance import perplexity_finance_available, finance_macro_india

        if perplexity_finance_available():
            console.print()
            console.print("[bold cyan]◆ Perplexity Finance — India Market Context[/bold cyan]")
            result = finance_macro_india()
            if result.ok and result.summary:
                console.print(result.summary[:1500])
                if result.citations:
                    console.print(
                        "\n[dim]Sources: " + "  |  ".join(result.citations[:3]) + "[/dim]"
                    )
            else:
                console.print(f"[dim]Finance data unavailable: {result.error}[/dim]")
    except Exception:
        pass  # finance context is always best-effort


# ── Raw display helpers ───────────────────────────────────────


def _print_snapshot(snap) -> None:
    t = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    t.add_column(style="dim")
    t.add_column(style="bold")
    t.add_column(style="dim")

    def row(name, val, chg):
        color = "green" if chg >= 0 else "red"
        sign = "+" if chg >= 0 else ""
        t.add_row(name, f"{val:,.2f}", f"[{color}]{sign}{chg:.2f}%[/{color}]")

    if snap.nifty:
        row("NIFTY 50", snap.nifty, snap.nifty_chg)
    if snap.banknifty:
        row("BANKNIFTY", snap.banknifty, snap.banknifty_chg)
    if snap.sensex:
        row("SENSEX", snap.sensex, snap.sensex_chg)
    if snap.india_vix:
        vix_color = "red" if snap.india_vix > 20 else "yellow" if snap.india_vix > 15 else "green"
        t.add_row("India VIX", f"[{vix_color}]{snap.india_vix:.2f}[/{vix_color}]", "")

    posture_color = {"BULLISH": "green", "BEARISH": "red", "VOLATILE": "yellow"}.get(
        snap.posture, "white"
    )
    console.print(
        Panel(
            t,
            title=f"[bold]Market Posture: [{posture_color}]{snap.posture}[/{posture_color}][/bold]",
            box=box.ROUNDED,
        )
    )


def _print_news(news: list) -> None:
    console.print("\n[bold cyan]📰  Top Headlines[/bold cyan]")
    for i, item in enumerate(news[:5], 1):
        source = getattr(item, "source", "")
        title = getattr(item, "title", str(item))
        console.print(f"  {i}. [white]{title}[/white]  [dim]({source})[/dim]")
    console.print()


def _print_fii(fii_data) -> None:
    console.print("[bold cyan]💰  FII / DII Activity[/bold cyan]")
    if isinstance(fii_data, list):
        for entry in fii_data[:3]:
            date_str = entry.get("date", "")
            fii_net = entry.get("fii_net", 0)
            dii_net = entry.get("dii_net", 0)
            fc = "green" if fii_net >= 0 else "red"
            dc = "green" if dii_net >= 0 else "red"
            console.print(
                f"  {date_str}  "
                f"FII [{fc}]₹{fii_net:+,.0f}Cr[/{fc}]  "
                f"DII [{dc}]₹{dii_net:+,.0f}Cr[/{dc}]"
            )
    console.print()


def _print_breadth(breadth) -> None:
    ad = breadth.get("advance_decline_ratio", 0) if isinstance(breadth, dict) else 0
    adv = breadth.get("advances", 0) if isinstance(breadth, dict) else 0
    dec = breadth.get("declines", 0) if isinstance(breadth, dict) else 0
    color = "green" if ad > 1.5 else "red" if ad < 0.7 else "yellow"
    console.print(
        f"[bold cyan]📊  Market Breadth[/bold cyan]  "
        f"Advances: [green]{adv}[/green]  Declines: [red]{dec}[/red]  "
        f"A/D Ratio: [{color}]{ad:.2f}[/{color}]"
    )
    console.print()


def _print_events(events: dict) -> None:
    console.print("[bold cyan]📅  Upcoming Events (7 days)[/bold cyan]")
    expiry = events.get("expiry", {})
    if expiry.get("weekly"):
        console.print(f"  📌 Weekly Expiry:  {expiry['weekly']}")
    if expiry.get("monthly"):
        console.print(f"  📌 Monthly Expiry: {expiry['monthly']}")

    for ev in events.get("earnings", [])[:3]:
        console.print(f"  📣 Earnings: {ev.get('symbol', '')} on {ev.get('date', '')}")

    for ev in events.get("rbi", [])[:1]:
        console.print(f"  🏦 RBI MPC: {ev.get('date', '')} — {ev.get('description', '')}")

    console.print()
