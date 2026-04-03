"""
engine/patterns.py
──────────────────
India-specific market pattern knowledge base.

Pre-built calendar and behavioral patterns that repeat in Indian markets.
Used by analysts and the synthesis agent to add seasonal/event context.

Usage:
    from engine.patterns import get_active_patterns, get_pattern_context

    # Get patterns relevant right now
    patterns = get_active_patterns()

    # Get text context for LLM prompts
    context = get_pattern_context()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class MarketPattern:
    """A recurring Indian market pattern."""

    name: str
    description: str
    impact: str  # "BULLISH" / "BEARISH" / "VOLATILE" / "NEUTRAL"
    confidence: int  # 0-100, how reliably this pattern occurs
    action: str  # recommended action
    tags: list[str]


# ── Calendar Patterns ────────────────────────────────────────


def _get_calendar_patterns(today: date) -> list[MarketPattern]:
    """Patterns based on date/time of year."""
    patterns = []
    month = today.month
    day = today.day
    weekday = today.weekday()  # 0=Monday

    # ── Weekly patterns ──────────────────────────────────────

    # Monday effect
    if weekday == 0:
        patterns.append(
            MarketPattern(
                name="Monday Gap Risk",
                description="Markets often gap up/down on Monday based on global cues over the weekend. "
                "Wait for first 30 min to settle before taking positions.",
                impact="VOLATILE",
                confidence=65,
                action="Wait for 9:45 AM before entering. Watch SGX Nifty for direction.",
                tags=["weekly", "intraday"],
            )
        )

    # Thursday expiry
    if weekday == 3:
        patterns.append(
            MarketPattern(
                name="Weekly Expiry Day",
                description="NIFTY/BANKNIFTY weekly options expire today. High gamma risk, "
                "sharp moves possible near 22000/23000 round levels. Max pain gravitational pull.",
                impact="VOLATILE",
                confidence=80,
                action="Avoid selling naked options. Use spreads. Close positions before 2:30 PM.",
                tags=["weekly", "expiry", "options"],
            )
        )

    # Friday profit booking
    if weekday == 4:
        patterns.append(
            MarketPattern(
                name="Friday Profit Booking",
                description="Traders often book profits on Friday to avoid weekend risk. "
                "Mild bearish bias in last 1-2 hours.",
                impact="BEARISH",
                confidence=55,
                action="Avoid fresh long entries after 2 PM. Good time to sell covered calls.",
                tags=["weekly", "intraday"],
            )
        )

    # ── Monthly patterns ─────────────────────────────────────

    # Last Thursday of month — monthly expiry
    # (approximation: last week of month + Thursday)
    if weekday == 3 and day >= 24:
        patterns.append(
            MarketPattern(
                name="Monthly F&O Expiry",
                description="Monthly settlement day. Rollover activity, sharp OI unwinding, "
                "and max pain convergence. Highly volatile last 2 hours.",
                impact="VOLATILE",
                confidence=85,
                action="Roll positions before 1 PM. Avoid new positions. Watch OI data closely.",
                tags=["monthly", "expiry", "options"],
            )
        )

    # Series start (first week of month)
    if day <= 7 and weekday == 0:
        patterns.append(
            MarketPattern(
                name="New Series Positioning",
                description="First week of new F&O series. FIIs build fresh positions. "
                "OI buildup gives directional clues for the month.",
                impact="NEUTRAL",
                confidence=60,
                action="Watch FII OI data for directional bias. Good time for fresh trades.",
                tags=["monthly", "options"],
            )
        )

    # ── Seasonal patterns ────────────────────────────────────

    # Budget rally (Jan-Feb)
    if month == 1 and day >= 15:
        patterns.append(
            MarketPattern(
                name="Pre-Budget Rally",
                description="Markets often rally in anticipation of Union Budget (Feb 1). "
                "Infra, defence, PSU sectors get speculative interest.",
                impact="BULLISH",
                confidence=65,
                action="Watch infra/defence/PSU stocks. Buy on dips. Trim before budget day.",
                tags=["seasonal", "budget"],
            )
        )

    if month == 2 and day == 1:
        patterns.append(
            MarketPattern(
                name="Budget Day Volatility",
                description="Union Budget day. Extremely volatile. Markets can swing 2-3% either way. "
                "Do NOT trade the first reaction — wait for dust to settle.",
                impact="VOLATILE",
                confidence=90,
                action="Stay flat or hedge fully. No naked positions. Analyze after close.",
                tags=["seasonal", "budget", "event"],
            )
        )

    # March quarter-end
    if month == 3 and day >= 20:
        patterns.append(
            MarketPattern(
                name="FY-End FII Selling",
                description="FIIs often sell in late March for portfolio rebalancing and tax purposes. "
                "Domestic mutual funds may buy (SIP flows).",
                impact="BEARISH",
                confidence=60,
                action="Watch FII data closely. Hedge longs. Good entry if selling is heavy.",
                tags=["seasonal", "quarter-end"],
            )
        )

    # April new FY rally
    if month == 4 and day <= 15:
        patterns.append(
            MarketPattern(
                name="New Financial Year Rally",
                description="Fresh FY allocations from FIIs and mutual funds. "
                "Markets often bounce in early April after March selling.",
                impact="BULLISH",
                confidence=60,
                action="Buy quality on dips. New SIP flows support the market.",
                tags=["seasonal"],
            )
        )

    # Earnings season (mid Jan, mid Apr, mid Jul, mid Oct)
    if month in (1, 4, 7, 10) and 10 <= day <= 31:
        patterns.append(
            MarketPattern(
                name="Earnings Season",
                description="Quarterly results season. Stock-specific moves of 5-15% on results. "
                "IV expansion before results, IV crush after.",
                impact="VOLATILE",
                confidence=85,
                action="Check earnings calendar. Sell straddles before results (if IV is high). "
                "Avoid holding options through results unless directional conviction is strong.",
                tags=["seasonal", "earnings"],
            )
        )

    # October-November Diwali rally
    if month == 10 and day >= 15:
        patterns.append(
            MarketPattern(
                name="Pre-Diwali Rally",
                description="Markets historically rally before Diwali. Muhurat trading session "
                "is symbolic but sentiment is generally positive.",
                impact="BULLISH",
                confidence=65,
                action="Go long quality large-caps. Muhurat trading day is often positive.",
                tags=["seasonal", "diwali"],
            )
        )

    if month == 11 and day <= 15:
        patterns.append(
            MarketPattern(
                name="Post-Diwali Correction",
                description="After Diwali euphoria, markets often correct in November. "
                "Profit booking + FII selling ahead of US holidays.",
                impact="BEARISH",
                confidence=55,
                action="Book partial profits. Tighten stop-losses.",
                tags=["seasonal", "diwali"],
            )
        )

    # December tax-loss selling
    if month == 12 and day >= 15:
        patterns.append(
            MarketPattern(
                name="Year-End Tax Selling",
                description="Global fund managers sell losers for tax-loss harvesting. "
                "Low volumes, thin markets. January effect follows (bounce in losers).",
                impact="BEARISH",
                confidence=55,
                action="Avoid illiquid stocks. Watch for January effect opportunities.",
                tags=["seasonal", "year-end"],
            )
        )

    return patterns


# ── RBI/Policy Patterns ──────────────────────────────────────


def _get_event_patterns() -> list[MarketPattern]:
    """Patterns around known recurring events (always applicable)."""
    return [
        MarketPattern(
            name="Pre-RBI Policy Caution",
            description="Markets are cautious 2-3 days before RBI MPC decision. "
            "Rate-sensitive sectors (banks, NBFCs, realty) move sharply on the decision.",
            impact="VOLATILE",
            confidence=75,
            action="Hedge bank positions. Avoid fresh entries in rate-sensitives until post-MPC.",
            tags=["event", "rbi"],
        ),
        MarketPattern(
            name="FII-DII Divergence Signal",
            description="When FII sells heavily but DII buys (or vice versa), it often marks "
            "a short-term bottom (FII selling + DII buying) or top (FII buying + DII selling).",
            impact="NEUTRAL",
            confidence=70,
            action="Track FII/DII for 3 consecutive days. Divergence > ₹3000 Cr is significant.",
            tags=["flow", "institutional"],
        ),
        MarketPattern(
            name="VIX Mean Reversion",
            description="India VIX tends to mean-revert. VIX > 20 often precedes a market bounce. "
            "VIX < 12 often precedes a spike (complacency). Use VIX extremes as contrarian signals.",
            impact="NEUTRAL",
            confidence=70,
            action="VIX > 20: start accumulating. VIX < 12: buy protection (puts/VIX calls).",
            tags=["volatility", "contrarian"],
        ),
    ]


# ── Public API ───────────────────────────────────────────────


def get_active_patterns(today: Optional[date] = None) -> list[MarketPattern]:
    """Get all patterns relevant to the current date."""
    today = today or date.today()
    patterns = _get_calendar_patterns(today)
    patterns.extend(_get_event_patterns())
    return patterns


def get_pattern_context(today: Optional[date] = None) -> str:
    """
    Generate a text summary of active patterns for injecting into LLM prompts.
    """
    patterns = get_active_patterns(today)
    if not patterns:
        return "No specific market patterns active today."

    parts = [f"Active market patterns ({len(patterns)}):"]
    for p in patterns:
        parts.append(
            f"  [{p.impact}] {p.name} (confidence: {p.confidence}%)\n"
            f"    {p.description}\n"
            f"    Action: {p.action}"
        )
    return "\n\n".join(parts)


def get_patterns_for_tags(tags: list[str]) -> list[MarketPattern]:
    """Get patterns matching specific tags (e.g. ["expiry", "options"])."""
    all_patterns = get_active_patterns()
    return [p for p in all_patterns if any(t in p.tags for t in tags)]
