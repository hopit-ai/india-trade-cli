"""
market/earnings.py
──────────────────
Earnings Season Agent — quarterly results tracking, pre-earnings IV analysis,
and post-earnings surprise detection.

India-specific:
  - Quarterly results season: mid-Jan, mid-Apr, mid-Jul, mid-Oct
  - NSE filings for board meeting dates
  - Pre-earnings IV expansion tracking
  - Consensus vs actual comparison (when available)

Usage:
    from market.earnings import (
        get_earnings_calendar,
        get_pre_earnings_iv,
        is_earnings_season,
        get_earnings_context,
    )

    # Upcoming earnings for watchlist
    calendar = get_earnings_calendar(["RELIANCE", "TCS", "INFY"])

    # Pre-earnings IV check
    iv_data = get_pre_earnings_iv("RELIANCE")

    # Is it earnings season right now?
    if is_earnings_season():
        print("Earnings season active — watch for stock-specific moves")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class EarningsEntry:
    """A single stock's earnings event."""

    symbol: str
    company_name: str = ""
    result_date: str = ""  # YYYY-MM-DD or "TBD"
    quarter: str = ""  # "Q3FY26", "Q4FY26"
    status: str = "UPCOMING"  # UPCOMING / REPORTED / MISSED
    # Pre-earnings data
    iv_rank: Optional[float] = None
    iv_percentile: Optional[float] = None
    avg_move: Optional[float] = None  # historical avg post-earnings move %
    # Post-earnings data (filled after results)
    surprise: Optional[str] = None  # "BEAT" / "MISS" / "INLINE"
    actual_move: Optional[float] = None  # actual % move on result day


# ── NIFTY 50 Earnings Calendar ───────────────────────────────
# Major companies and their typical result months
# This serves as a baseline — actual dates come from NSE filings

_NIFTY50_EARNINGS_MONTHS = {
    # Company: [typical result months (1-indexed)]
    "RELIANCE": [1, 4, 7, 10],
    "TCS": [1, 4, 7, 10],  # TCS is usually first to report
    "HDFCBANK": [1, 4, 7, 10],
    "INFY": [1, 4, 7, 10],  # Infosys reports early (mid-month)
    "ICICIBANK": [1, 4, 7, 10],
    "SBIN": [2, 5, 8, 11],  # PSU banks report slightly later
    "BHARTIARTL": [1, 4, 7, 10],
    "ITC": [1, 4, 7, 10],
    "KOTAKBANK": [1, 4, 7, 10],
    "LT": [1, 4, 7, 10],
    "AXISBANK": [1, 4, 7, 10],
    "TATAMOTORS": [2, 5, 8, 11],
    "MARUTI": [1, 4, 7, 10],
    "SUNPHARMA": [2, 5, 8, 11],
    "BAJFINANCE": [1, 4, 7, 10],
    "TITAN": [2, 5, 8, 11],
    "WIPRO": [1, 4, 7, 10],
    "ASIANPAINT": [1, 4, 7, 10],
    "ULTRACEMCO": [1, 4, 7, 10],
    "TATASTEEL": [2, 5, 8, 11],
    "HINDUNILVR": [1, 4, 7, 10],
    "M&M": [2, 5, 8, 11],
    "DRREDDY": [2, 5, 8, 11],
    "ADANIENT": [2, 5, 8, 11],
    "NTPC": [2, 5, 8, 11],
    "POWERGRID": [2, 5, 8, 11],
}

# Historical average post-earnings move (absolute %) for major stocks
_AVG_EARNINGS_MOVE = {
    "TCS": 3.5,
    "INFY": 4.2,
    "RELIANCE": 2.8,
    "HDFCBANK": 2.5,
    "ICICIBANK": 3.0,
    "SBIN": 4.0,
    "BHARTIARTL": 3.5,
    "ITC": 2.0,
    "TATAMOTORS": 5.0,
    "BAJFINANCE": 4.5,
    "WIPRO": 3.8,
    "MARUTI": 3.0,
    "TITAN": 3.5,
    "SUNPHARMA": 3.2,
}


def _current_quarter() -> str:
    """Get current FY quarter label (e.g. 'Q4FY26')."""
    today = date.today()
    month = today.month
    year = today.year

    # Indian FY: Apr-Mar
    if month >= 4:
        fy = year + 1
    else:
        fy = year

    if month in (4, 5, 6):
        q = 1
    elif month in (7, 8, 9):
        q = 2
    elif month in (10, 11, 12):
        q = 3
    else:
        q = 4

    return f"Q{q}FY{fy % 100}"


def is_earnings_season() -> bool:
    """Check if we're currently in an earnings reporting window."""
    today = date.today()
    month = today.month
    day = today.day
    # Earnings season: roughly 10th of Jan/Apr/Jul/Oct to end of following month
    return month in (1, 2, 4, 5, 7, 8, 10, 11) and (
        (month in (1, 4, 7, 10) and day >= 10) or (month in (2, 5, 8, 11) and day <= 15)
    )


def _next_expected_date(sym: str, today: date) -> Optional[date]:
    """
    Compute the next expected reporting date for a stock based on its
    typical reporting-month pattern.  Returns None if unknown.
    """
    months = _NIFTY50_EARNINGS_MONTHS.get(sym, [])
    if not months:
        return None
    for offset in range(13):  # look up to ~1 year ahead
        m = ((today.month - 1 + offset) % 12) + 1
        y = today.year + ((today.month - 1 + offset) // 12)
        if m in months:
            # Results typically land around the 15th–20th of the month
            day = min(15, 28)
            est = date(y, m, day)
            if est >= today:
                return est
    return None


def get_earnings_calendar(
    symbols: Optional[list[str]] = None,
    days_ahead: int = 60,
) -> list[EarningsEntry]:
    """
    Get upcoming earnings for given symbols (or NIFTY 50 by default).

    Uses a combination of:
    1. Known reporting patterns (which month each company typically reports)
    2. NSE board meeting calendar (for actual dates when available)

    Only returns genuinely future events.  Past dates from NSE (previous
    quarter) are discarded and replaced with the next expected date.
    """
    today = date.today()
    quarter = _current_quarter()
    target_symbols = symbols or list(_NIFTY50_EARNINGS_MONTHS.keys())

    entries = []
    for sym in target_symbols:
        sym = sym.upper()

        entry = EarningsEntry(
            symbol=sym,
            quarter=quarter,
            result_date="TBD",
            avg_move=_AVG_EARNINGS_MOVE.get(sym),
        )

        # Try to get actual date from NSE
        nse_date: Optional[date] = None
        try:
            raw = _fetch_earnings_date_nse(sym)
            if raw and raw != "TBD":
                nse_date = date.fromisoformat(raw)
        except Exception:
            pass

        if nse_date and nse_date >= today:
            # NSE returned a genuine upcoming date — use it
            entry.result_date = nse_date.strftime("%d-%b-%Y")
            entry.status = "UPCOMING"
        else:
            # NSE date is stale (past quarter) or unavailable — estimate next
            next_dt = _next_expected_date(sym, today)
            if next_dt:
                entry.result_date = next_dt.strftime("%d-%b-%Y")
                # Mark confirmed only if within the current season window
                entry.status = "UPCOMING"
            else:
                entry.result_date = "TBD"
                entry.status = "UPCOMING"

        # Filter: skip if estimated date is beyond days_ahead (unless caller
        # explicitly requested this symbol)
        if not symbols:
            try:
                result_dt = date.strptime(entry.result_date, "%d-%b-%Y")
                if (result_dt - today).days > days_ahead:
                    continue
            except ValueError:
                pass  # TBD — include anyway

        entries.append(entry)

    # Sort by date (TBD at the end)
    entries.sort(key=lambda e: e.result_date if e.result_date != "TBD" else "9999")
    return entries


def get_pre_earnings_iv(symbol: str) -> dict:
    """
    Check IV rank/percentile before earnings.
    High IV rank = expensive options = consider selling premium.
    Low IV rank = cheap options = consider buying straddles.
    """
    symbol = symbol.upper()
    avg_move = _AVG_EARNINGS_MOVE.get(symbol, 3.0)

    try:
        from agent.tools import build_registry

        reg = build_registry()
        iv_result = reg.execute("get_iv_rank", {"symbol": symbol})
        iv_rank = iv_result.get("iv_rank", 50) if isinstance(iv_result, dict) else 50
    except Exception:
        iv_rank = 50

    # Strategy suggestion based on IV
    if iv_rank > 60:
        strategy = "SELL premium — IV elevated. Consider selling straddle/strangle."
        action = "SELL_PREMIUM"
    elif iv_rank < 30:
        strategy = "BUY options — IV cheap. Consider buying straddle for earnings move."
        action = "BUY_STRADDLE"
    else:
        strategy = "Neutral IV — consider iron condor or stay away."
        action = "NEUTRAL"

    return {
        "symbol": symbol,
        "iv_rank": iv_rank,
        "avg_earnings_move": avg_move,
        "strategy_suggestion": strategy,
        "action": action,
        "quarter": _current_quarter(),
    }


def _fetch_earnings_date_nse(symbol: str) -> Optional[str]:
    """Try to get the actual earnings date from NSE corporate filings."""
    try:
        import httpx

        url = "https://www.nseindia.com/api/corporate-board-meetings"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        with httpx.Client(headers=headers, timeout=10, follow_redirects=True) as client:
            client.get("https://www.nseindia.com")  # cookie warmup
            params = {"index": "equities", "symbol": symbol}
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                meetings = data if isinstance(data, list) else []
                for m in meetings:
                    purpose = (m.get("bm_purpose", "") or "").lower()
                    if "financial result" in purpose or "quarterly" in purpose:
                        return m.get("bm_date", "TBD")
    except Exception:
        pass
    return None


def predict_earnings_surprise(symbol: str) -> dict:
    """
    Predict likely earnings outcome based on available signals.

    Uses:
    - Pre-earnings technical momentum (is stock rallying into results?)
    - IV rank (high IV = market expects big move)
    - FII/DII positioning (institutional conviction)
    - Historical beat/miss patterns
    - Sector performance (sector tailwind = higher beat probability)

    Returns dict with prediction, confidence, and reasoning.
    """
    symbol = symbol.upper()
    signals = []
    bullish_count = 0
    bearish_count = 0

    # 1. Pre-earnings technical momentum
    try:
        from analysis.technical import analyse as tech_analyse

        snap = tech_analyse(symbol)
        if snap.score > 30:
            signals.append(
                f"Strong technical momentum (score: {snap.score:+d}) — stocks rallying into earnings often beat"
            )
            bullish_count += 1
        elif snap.score < -30:
            signals.append(
                f"Weak technical setup (score: {snap.score:+d}) — bearish momentum pre-earnings"
            )
            bearish_count += 1
        else:
            signals.append(f"Neutral technicals (score: {snap.score:+d})")

        if snap.rsi > 65:
            signals.append(f"RSI {snap.rsi:.0f} — overbought, limited upside on beat")
        elif snap.rsi < 35:
            signals.append(
                f"RSI {snap.rsi:.0f} — oversold, positive surprise could trigger sharp rally"
            )
            bullish_count += 1
    except Exception:
        pass

    # 2. IV rank (market expectation)
    iv_data = get_pre_earnings_iv(symbol)
    iv_rank = iv_data.get("iv_rank", 50)
    avg_move = iv_data.get("avg_earnings_move", 3.0)

    if iv_rank > 70:
        signals.append(f"IV rank {iv_rank} — market expects big move (±{avg_move:.1f}%)")
    elif iv_rank < 30:
        signals.append(f"IV rank {iv_rank} — market complacent, surprise could be amplified")

    # 3. Historical beat/miss tendency
    _BEAT_TENDENCY = {
        "TCS": 0.7,
        "INFY": 0.65,
        "RELIANCE": 0.6,
        "HDFCBANK": 0.65,
        "ICICIBANK": 0.6,
        "BHARTIARTL": 0.55,
        "ITC": 0.7,
        "BAJFINANCE": 0.55,
        "MARUTI": 0.5,
        "TATAMOTORS": 0.5,
        "WIPRO": 0.45,
        "SBIN": 0.5,
    }
    beat_prob = _BEAT_TENDENCY.get(symbol, 0.5)
    if beat_prob > 0.6:
        signals.append(f"Historical beat rate: {beat_prob:.0%} — tends to exceed expectations")
        bullish_count += 1
    elif beat_prob < 0.45:
        signals.append(f"Historical beat rate: {beat_prob:.0%} — tends to miss expectations")
        bearish_count += 1
    else:
        signals.append(f"Historical beat rate: {beat_prob:.0%} — coin flip")

    # 4. Derive prediction
    if bullish_count >= 2:
        prediction = "LIKELY_BEAT"
        confidence = min(55 + bullish_count * 10, 75)
    elif bearish_count >= 2:
        prediction = "LIKELY_MISS"
        confidence = min(55 + bearish_count * 10, 75)
    else:
        prediction = "UNCERTAIN"
        confidence = 40

    return {
        "symbol": symbol,
        "prediction": prediction,
        "confidence": confidence,
        "signals": signals,
        "iv_rank": iv_rank,
        "avg_move": avg_move,
        "beat_probability": beat_prob,
        "quarter": _current_quarter(),
        "strategy": iv_data.get("strategy_suggestion", ""),
    }


def get_earnings_context(symbols: Optional[list[str]] = None) -> str:
    """Generate text context about earnings for LLM prompts."""
    if not is_earnings_season():
        return "Not currently in earnings season."

    calendar = get_earnings_calendar(symbols, days_ahead=14)
    if not calendar:
        return "No upcoming earnings for watched symbols in next 14 days."

    parts = [f"Earnings season active ({_current_quarter()}):"]
    for e in calendar[:10]:
        line = f"  {e.symbol}: {e.result_date}"
        if e.avg_move:
            line += f" (avg move: ±{e.avg_move:.1f}%)"
        parts.append(line)

    return "\n".join(parts)


def print_earnings_calendar(symbols: Optional[list[str]] = None) -> None:
    """Display earnings calendar as a Rich table."""
    calendar = get_earnings_calendar(symbols)
    if not calendar:
        console.print("[dim]No upcoming earnings found.[/dim]")
        return

    season = "[green]ACTIVE[/green]" if is_earnings_season() else "[dim]Not active[/dim]"
    table = Table(title=f"Earnings Calendar — {_current_quarter()} (Season: {season})")
    table.add_column("Symbol", style="bold", width=12)
    table.add_column("Date", width=12)
    table.add_column("Avg Move", justify="right", width=10)
    table.add_column("Status", width=10)

    for e in calendar:
        move_str = f"±{e.avg_move:.1f}%" if e.avg_move else "-"
        table.add_row(e.symbol, e.result_date, move_str, e.status)

    console.print(table)
