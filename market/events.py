"""
market/events.py
────────────────
Market calendar: F&O expiry dates, earnings, RBI policy, corporate actions.
All data sourced from public endpoints (NSE, RBI websites).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime    import date, datetime, timedelta
from typing      import Optional

import httpx

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False


# ── Result types ─────────────────────────────────────────────

@dataclass
class ExpiryDates:
    weekly:  date            # nearest weekly expiry (Thursday)
    monthly: date            # nearest monthly expiry (last Thursday of month)
    next_monthly: date       # following month's expiry


@dataclass
class EarningsEvent:
    symbol:    str
    company:   str
    date:      str           # "YYYY-MM-DD"
    purpose:   str           # "Quarterly Results", "Board Meeting" etc.


@dataclass
class RBIEvent:
    date:      str
    event:     str
    rate:      Optional[float] = None    # repo rate after decision


@dataclass
class CorporateAction:
    symbol:    str
    action:    str           # "Dividend", "Bonus", "Split", "Rights"
    ex_date:   str
    details:   str


# ── F&O Expiry Dates ─────────────────────────────────────────

def _last_thursday(year: int, month: int) -> date:
    """Last Thursday of the given month."""
    # Walk back from last day to find Thursday (weekday 3)
    # Get last day properly
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    while last.weekday() != 3:   # 3 = Thursday
        last -= timedelta(days=1)
    return last


def _next_thursday(from_date: date = None) -> date:
    """Next Thursday from given date (or today)."""
    d = from_date or date.today()
    days_ahead = 3 - d.weekday()   # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def get_expiry_dates() -> ExpiryDates:
    """
    Calculate current week/month/next-month F&O expiry dates.
    NSE weekly expiries: every Thursday.
    NSE monthly expiries: last Thursday of the month.
    """
    today   = date.today()
    year, month = today.year, today.month

    # Weekly: next Thursday (if today is Thursday and market hours, it's today)
    weekly = _next_thursday(today)
    if today.weekday() == 3:
        weekly = today     # today IS Thursday

    # Monthly: last Thursday of current month
    monthly = _last_thursday(year, month)
    if monthly < today:
        # Current month already expired — move to next month
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        monthly = _last_thursday(ny, nm)

    # Next monthly
    if monthly.month == 12:
        nm2, ny2 = 1, monthly.year + 1
    else:
        nm2, ny2 = monthly.month + 1, monthly.year
    next_monthly = _last_thursday(ny2, nm2)

    return ExpiryDates(
        weekly       = weekly,
        monthly      = monthly,
        next_monthly = next_monthly,
    )


# ── Earnings Calendar ─────────────────────────────────────────

NSE_CORP_CALENDAR_URL = (
    "https://www.nseindia.com/api/event-calendar"
)

def get_earnings_calendar(
    symbols: Optional[list[str]] = None,
    days:    int = 14,
) -> list[EarningsEvent]:
    """
    Upcoming earnings / board meetings for watchlist symbols.

    Args:
        symbols: Filter to these symbols. None = all upcoming.
        days:    Look ahead this many days.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept":     "application/json",
            "Referer":    "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(NSE_CORP_CALENDAR_URL, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()

        today    = date.today()
        cutoff   = today + timedelta(days=days)
        events   = []
        for item in data:
            sym     = item.get("symbol", "")
            ev_date = item.get("date", "")
            purpose = item.get("purpose", "")
            if symbols and sym.upper() not in [s.upper() for s in symbols]:
                continue
            try:
                ev_dt = datetime.strptime(ev_date, "%d-%b-%Y").date()
                if today <= ev_dt <= cutoff:
                    events.append(EarningsEvent(
                        symbol  = sym,
                        company = item.get("company", sym),
                        date    = ev_dt.isoformat(),
                        purpose = purpose,
                    ))
            except (ValueError, TypeError):
                continue
        return sorted(events, key=lambda e: e.date)

    except Exception:
        return []  # No mock data — return empty when NSE API fails


# ── RBI Calendar ─────────────────────────────────────────────

RBI_RSS = "https://rbi.org.in/scripts/RSSFeedMonetary.aspx"

def get_rbi_calendar() -> list[RBIEvent]:
    """
    RBI Monetary Policy Committee upcoming dates.
    Fetches from RBI RSS feed. Returns empty list if unavailable.
    """
    if not _FEEDPARSER_AVAILABLE:
        return []
    try:
        feed  = feedparser.parse(RBI_RSS)
        events = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            if "monetary" in title.lower() or "policy" in title.lower() or "repo" in title.lower():
                published = entry.get("published", "")
                events.append(RBIEvent(
                    date  = published[:10] if published else "",
                    event = title,
                ))
        if events:
            return events
    except Exception:
        pass

    return []  # No mock data — return empty when RBI RSS fails


# ── Corporate Actions ─────────────────────────────────────────

NSE_CORP_ACTIONS_URL = (
    "https://www.nseindia.com/api/corporates-corporateActions"
    "?index=equities&symbol={symbol}"
)


def get_corporate_actions(symbol: str, n: int = 5) -> list[CorporateAction]:
    """
    Recent dividends, splits, bonuses from NSE for a given symbol.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept":     "application/json",
            "Referer":    "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(
            NSE_CORP_ACTIONS_URL.format(symbol=symbol.upper()),
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        actions = []
        for item in data[:n]:
            actions.append(CorporateAction(
                symbol  = symbol.upper(),
                action  = item.get("subject", item.get("purpose", "Action")),
                ex_date = item.get("exDate", item.get("ex_date", "")),
                details = item.get("remarks", ""),
            ))
        return actions
    except Exception:
        return []


# ── Upcoming market events summary ────────────────────────────

def get_upcoming_events(days: int = 7) -> dict:
    """
    Combined summary of all upcoming market events.
    Used by morning brief.
    """
    expiries = get_expiry_dates()
    earnings = get_earnings_calendar(days=days)
    rbi      = get_rbi_calendar()
    today    = date.today()

    return {
        "expiries": {
            "weekly":       expiries.weekly.isoformat(),
            "monthly":      expiries.monthly.isoformat(),
            "days_to_weekly":  (expiries.weekly  - today).days,
            "days_to_monthly": (expiries.monthly - today).days,
        },
        "earnings":  [{"symbol": e.symbol, "date": e.date, "purpose": e.purpose} for e in earnings[:5]],
        "rbi":       [{"date": r.date, "event": r.event} for r in rbi[:2]],
    }
