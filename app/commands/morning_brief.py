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
    fii_data = None
    try:
        fii_data = get_fii_dii_data(5)  # 5 days for consecutive-day analysis
        _print_fii(fii_data[:3])  # display last 3 days
    except Exception as e:
        console.print(f"[red]FII/DII data unavailable: {e}[/red]")

    # ── Market breadth ────────────────────────────────────────
    breadth_data = None
    try:
        breadth_data = get_market_breadth()
        _print_breadth(breadth_data)
    except Exception as e:
        console.print(f"[red]Breadth data unavailable: {e}[/red]")

    # ── Events ────────────────────────────────────────────────
    try:
        events = get_upcoming_events(7)
        _print_events(events)
    except Exception as e:
        console.print(f"[red]Events unavailable: {e}[/red]")

    # ── Personal watchlist (from memory) ──────────────────────
    try:
        _print_memory_watchlist()
    except Exception:
        pass  # non-blocking

    # ── Actionable agenda ─────────────────────────────────────
    try:
        _print_actionable_agenda(fii_data, breadth_data)
    except Exception:
        pass  # non-blocking

    # ── Perplexity Finance macro context (best-effort) ────────
    try:
        from agent.perplexity_finance import finance_macro_india, perplexity_finance_available

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

    # Each field on MarketSnapshot is an IndexSnapshot with .ltp / .change_pct
    if snap.nifty and snap.nifty.ltp:
        row("NIFTY 50", snap.nifty.ltp, snap.nifty.change_pct)
    if snap.banknifty and snap.banknifty.ltp:
        row("BANKNIFTY", snap.banknifty.ltp, snap.banknifty.change_pct)
    if snap.sensex and snap.sensex.ltp:
        row("SENSEX", snap.sensex.ltp, snap.sensex.change_pct)
    if snap.vix and snap.vix.ltp:
        vix_val = snap.vix.ltp
        vix_color = "red" if vix_val > 20 else "yellow" if vix_val > 15 else "green"
        t.add_row("India VIX", f"[{vix_color}]{vix_val:.2f}[/{vix_color}]", "")

    # GIFT NIFTY pre-market indicator (#106)
    g = getattr(snap, "gift_nifty", None)
    if g and g.ltp:
        g_color = "green" if g.change >= 0 else "red"
        sign = "+" if g.change >= 0 else ""
        gap_str = ""
        if g.premium_pts is not None:
            gap_sign = "+" if g.premium_pct >= 0 else ""
            gap_label = "gap up" if g.premium_pct >= 0 else "gap down"
            gap_str = f" [dim]({gap_sign}{g.premium_pct:.2f}% {gap_label} implied)[/dim]"
        t.add_row(
            "GIFT NIFTY",
            f"{g.ltp:,.0f}",
            f"[{g_color}]{sign}{g.change:+.0f}pts, {sign}{g.change_pct:.2f}%[/{g_color}]{gap_str}",
        )

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


def _print_memory_watchlist() -> None:
    """
    Show recently-analyzed symbols from trade memory as a personal watchlist.
    Groups by symbol and shows last verdict + how long ago (#121).
    """
    try:
        from engine.memory import TradeMemory
        from datetime import datetime

        mem = TradeMemory()
        records = mem.query(limit=50)  # last 50 analyses
    except Exception:
        return  # non-blocking: if memory unavailable, skip silently

    if not records:
        return

    # Deduplicate by symbol — keep most recent record per symbol
    seen: dict[str, object] = {}
    for rec in records:
        if rec.symbol not in seen:
            seen[rec.symbol] = rec

    if not seen:
        return

    console.print("[bold cyan]🔭  Your Watchlist (from memory)[/bold cyan]")

    now = datetime.now()
    for sym, rec in list(seen.items())[:8]:  # show max 8 symbols
        verdict = rec.verdict or "—"
        verdict_color = (
            "green" if verdict == "BULLISH" else "red" if verdict == "BEARISH" else "yellow"
        )

        # Days since analysis
        try:
            ts = datetime.fromisoformat(rec.timestamp)
            days_ago = (now - ts).days
            age = f"{days_ago}d ago" if days_ago > 0 else "today"
        except Exception:
            age = "—"

        conf = f"({rec.confidence}%)" if rec.confidence else ""
        console.print(
            f"  [{verdict_color}]{verdict:<8}[/{verdict_color}] {sym:<12} {conf:<7} [dim]{age}[/dim]"
        )

    console.print()


def _print_actionable_agenda(fii_data=None, breadth_data=None) -> None:
    """
    Generate a prioritised action agenda for the trading day (#121).
    Based on FII flows, market breadth, and memory patterns.
    """
    from datetime import date

    agenda: list[tuple[str, str]] = []  # (priority_icon, action)

    # ── FII consecutive selling analysis ─────────────────────
    if fii_data:
        selling_streak = sum(1 for f in fii_data if getattr(f, "fii_net", 0) < -500)
        buying_streak = sum(1 for f in fii_data if getattr(f, "fii_net", 0) > 500)
        if selling_streak >= 3:
            agenda.append(
                (
                    "⚠️",
                    f"FII sold for {selling_streak} consecutive days — consider reducing long exposure",
                )
            )
        elif buying_streak >= 3:
            agenda.append(
                (
                    "✅",
                    f"FII buying streak ({buying_streak} days) — market has institutional support",
                )
            )

    # ── Market breadth agenda ─────────────────────────────────
    if breadth_data:
        verdict = getattr(breadth_data, "verdict", "") or ""
        ad = getattr(breadth_data, "ad_ratio", 0) or 0
        if verdict == "BROAD_DECLINE":
            agenda.append(("⚠️", f"Broad market decline (A/D={ad:.2f}) — avoid new longs today"))
        elif verdict == "BROAD_RALLY":
            agenda.append(("✅", f"Broad rally (A/D={ad:.2f}) — momentum is with the bulls"))

    # ── Day-of-week agenda ────────────────────────────────────
    today = date.today()
    weekday = today.weekday()  # 0=Mon, 4=Fri
    if weekday == 0:  # Monday
        agenda.append(("📋", "Monday: gap-and-go setups common — check pre-market ADRs"))
    elif weekday == 4:  # Friday
        agenda.append(("📋", "Friday expiry risk: roll or close short-dated positions"))
    elif weekday == 2:  # Wednesday
        agenda.append(("📋", "Mid-week: check open positions vs. key support/resistance"))

    # ── Memory-based agenda ───────────────────────────────────
    try:
        from engine.memory import TradeMemory

        mem = TradeMemory()
        recent = mem.query(limit=10)
        # Positions with stop/target set: check if worth revisiting
        with_targets = [r for r in recent if r.stop_loss or r.target_price]
        if with_targets:
            sym = with_targets[0].symbol
            agenda.append(("📍", f"Revisit open setup: {sym} — stop/target was set at analysis"))
    except Exception:
        pass

    if not agenda:
        return

    console.print("[bold cyan]📋  Today's Agenda[/bold cyan]")
    for icon, action in agenda[:5]:  # max 5 items
        console.print(f"  {icon}  {action}")
    console.print()
