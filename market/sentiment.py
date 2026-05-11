"""
market/sentiment.py
───────────────────
Market sentiment indicators:
  - FII / DII daily activity from NSE
  - News sentiment scoring (keyword-based, Claude-enhanced)
  - Market breadth (advance/decline)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from market.news import NewsItem


# ── FII / DII Data ───────────────────────────────────────────


@dataclass
class FIIDIIData:
    date: str
    fii_buy: float  # INR crore
    fii_sell: float
    fii_net: float  # positive = buying, negative = selling
    dii_buy: float
    dii_sell: float
    dii_net: float
    verdict: str  # "FII_BUYING" | "FII_SELLING" | "NEUTRAL"


NSE_FIIDII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"


def get_fii_dii_data(days: int = 5) -> list[FIIDIIData]:
    """
    FII / DII buy-sell activity from NSE (last N trading days).

    NSE API returns a flat list with separate entries for FII and DII
    per date. We group them into one record per date.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(NSE_FIIDII_URL, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()

        if not isinstance(data, list):
            return []

        # Group by date — API returns separate FII and DII entries
        by_date: dict[str, dict] = {}
        for item in data:
            dt = item.get("date", "")
            category = item.get("category", "").upper()
            buy_val = float(item.get("buyValue", 0))
            sell_val = float(item.get("sellValue", 0))
            net_val = float(item.get("netValue", 0))

            if dt not in by_date:
                by_date[dt] = {
                    "fii_buy": 0,
                    "fii_sell": 0,
                    "fii_net": 0,
                    "dii_buy": 0,
                    "dii_sell": 0,
                    "dii_net": 0,
                }

            if "FII" in category or "FPI" in category:
                by_date[dt]["fii_buy"] = buy_val
                by_date[dt]["fii_sell"] = sell_val
                by_date[dt]["fii_net"] = net_val
            elif "DII" in category:
                by_date[dt]["dii_buy"] = buy_val
                by_date[dt]["dii_sell"] = sell_val
                by_date[dt]["dii_net"] = net_val

        result = []
        # Sort by date descending so [0] is always the most recent day
        sorted_dates = sorted(by_date.keys(), reverse=True)
        for dt in sorted_dates[:days]:
            vals = by_date[dt]
            fii_net = vals["fii_net"]
            verdict = (
                "FII_BUYING" if fii_net > 500 else "FII_SELLING" if fii_net < -500 else "NEUTRAL"
            )
            result.append(
                FIIDIIData(
                    date=dt,
                    fii_buy=vals["fii_buy"],
                    fii_sell=vals["fii_sell"],
                    fii_net=fii_net,
                    dii_buy=vals["dii_buy"],
                    dii_sell=vals["dii_sell"],
                    dii_net=vals["dii_net"],
                    verdict=verdict,
                )
            )
        return result

    except Exception:
        return []  # No fake data — return empty list when NSE API fails


# ── News Sentiment ────────────────────────────────────────────

BULLISH_WORDS = {
    "surge",
    "rally",
    "gain",
    "jump",
    "rise",
    "high",
    "record",
    "strong",
    "beat",
    "outperform",
    "upgrade",
    "buy",
    "positive",
    "growth",
    "profit",
    "upside",
    "bull",
    "breakout",
    "momentum",
    "recovery",
    "boom",
}

BEARISH_WORDS = {
    "fall",
    "drop",
    "crash",
    "slump",
    "decline",
    "low",
    "weak",
    "loss",
    "miss",
    "underperform",
    "downgrade",
    "sell",
    "negative",
    "concern",
    "downside",
    "bear",
    "breakdown",
    "pressure",
    "recession",
    "crisis",
    "war",
    "inflation",
    "rate hike",
    "debt",
}


def score_headline(title: str) -> tuple[str, float]:
    """
    Simple keyword-based sentiment scoring for a headline.
    Returns (verdict, score) where score is -1.0 to +1.0.
    """
    words = set(re.sub(r"[^a-z\s]", "", title.lower()).split())
    bull = len(words & BULLISH_WORDS)
    bear = len(words & BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return "NEUTRAL", 0.0
    score = (bull - bear) / total
    verdict = "BULLISH" if score > 0.2 else "BEARISH" if score < -0.2 else "NEUTRAL"
    return verdict, round(score, 2)


def score_news_batch(items: list[NewsItem]) -> dict:
    """
    Aggregate sentiment across a list of news items.

    Returns:
        {
          "overall": "BULLISH" | "BEARISH" | "NEUTRAL",
          "score":   float (-1.0 to 1.0),
          "bullish_count": int,
          "bearish_count": int,
          "neutral_count": int,
          "items": [ {title, verdict, score}, ... ]
        }
    """
    scored = []
    for item in items:
        verdict, score = score_headline(item.title)
        scored.append(
            {
                "title": item.title,
                "source": item.source,
                "verdict": verdict,
                "score": score,
            }
        )

    bullish = sum(1 for s in scored if s["verdict"] == "BULLISH")
    bearish = sum(1 for s in scored if s["verdict"] == "BEARISH")
    neutral = sum(1 for s in scored if s["verdict"] == "NEUTRAL")

    avg_score = sum(s["score"] for s in scored) / len(scored) if scored else 0.0
    overall = "BULLISH" if avg_score > 0.1 else "BEARISH" if avg_score < -0.1 else "NEUTRAL"

    return {
        "overall": overall,
        "score": round(avg_score, 3),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "items": scored,
    }


# ── Market Breadth (Advance / Decline) ───────────────────────


@dataclass
class MarketBreadth:
    advances: int
    declines: int
    unchanged: int
    ad_ratio: float  # advances / declines
    verdict: str  # "BROAD_RALLY" | "BROAD_DECLINE" | "MIXED"


def get_market_breadth() -> MarketBreadth:
    """
    Advance/Decline ratio from NSE.
    Falls back to mock if NSE unavailable.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(
            "https://www.nseindia.com/api/allIndices",
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        # Parse NIFTY 500 advances/declines
        data = r.json().get("data", [])
        nifty500 = next((d for d in data if "500" in d.get("index", "")), None)
        if nifty500:
            adv = int(nifty500.get("advances", 0))
            dec = int(nifty500.get("declines", 0))
            unch = int(nifty500.get("unchanged", 0))
            return _build_breadth(adv, dec, unch)
    except Exception:
        pass

    # No mock data — return zeros so consumers know data is unavailable
    return MarketBreadth(advances=0, declines=0, unchanged=0, ad_ratio=0.0, verdict="UNAVAILABLE")


def _build_breadth(adv: int, dec: int, unch: int) -> MarketBreadth:
    ratio = adv / max(dec, 1)
    verdict = "BROAD_RALLY" if ratio > 2.0 else "BROAD_DECLINE" if ratio < 0.5 else "MIXED"
    return MarketBreadth(
        advances=adv,
        declines=dec,
        unchanged=unch,
        ad_ratio=round(ratio, 2),
        verdict=verdict,
    )


# ── Unified Sentiment Signal (#172) ──────────────────────────────


@dataclass
class SentimentSignal:
    """
    Aggregated India market sentiment for a symbol (#172).

    Combines FII/DII flows, news sentiment, bulk deals, and market
    breadth into a single weighted directional signal.
    """

    symbol: str
    overall_signal: str  # "BULLISH" | "NEUTRAL" | "BEARISH"
    confidence: int  # 0-100
    breakdown: dict[str, str]  # {"fii_dii": "BULLISH", "news": "NEUTRAL", ...}
    key_driver: str  # Most influential component
    sources: list[str]  # Data points used in scoring
    score: float  # -1.0 to +1.0 (raw weighted sum)


# Component weights
_COMPONENT_WEIGHTS = {
    "fii_dii": 0.30,
    "news": 0.25,
    "bulk_deals": 0.25,
    "breadth": 0.20,
}


def _fii_dii_signal(days: int = 5) -> tuple[str, float, list[str]]:
    """
    FII net flows over last N days.

    Returns (signal, score, sources_used).
    Bullish: cumulative FII net > +2000 Cr · Bearish: < -2000 Cr.
    """
    try:
        flows = get_fii_dii_data(days=days)
    except Exception:
        return "NEUTRAL", 0.0, []

    if not flows:
        return "NEUTRAL", 0.0, []

    cum_fii_net = sum(f.fii_net for f in flows)
    sources = [
        f"FII net {days}d: ₹{cum_fii_net:+,.0f} Cr (DII: ₹{sum(f.dii_net for f in flows):+,.0f} Cr)"
    ]

    if cum_fii_net > 2000:
        return "BULLISH", 1.0, sources
    if cum_fii_net > 500:
        return "BULLISH", 0.5, sources
    if cum_fii_net < -2000:
        return "BEARISH", -1.0, sources
    if cum_fii_net < -500:
        return "BEARISH", -0.5, sources
    return "NEUTRAL", 0.0, sources


def _news_signal(symbol: str) -> tuple[str, float, list[str]]:
    """
    News sentiment for the symbol.

    Returns (signal, score, sources_used).
    Uses keyword scoring from score_news_batch().
    """
    try:
        from market.news import get_stock_news

        items = get_stock_news(symbol, n=10)
    except Exception:
        return "NEUTRAL", 0.0, []

    if not items:
        return "NEUTRAL", 0.0, []

    result = score_news_batch(items)
    # score_news_batch returns: "overall", "score", "bullish_count", "bearish_count", "neutral_count"
    verdict = result.get("overall", "NEUTRAL")
    bull_count = result.get("bullish_count", 0)
    bear_count = result.get("bearish_count", 0)
    total = bull_count + bear_count + result.get("neutral_count", 0)

    bull_pct = bull_count / max(total, 1)
    bear_pct = bear_count / max(total, 1)

    sources = [
        f"News: {total} articles — {bull_pct * 100:.0f}% bullish, {bear_pct * 100:.0f}% bearish"
    ]

    if verdict == "BULLISH":
        score = 0.5 + 0.5 * max(0.0, bull_pct - bear_pct)
        return "BULLISH", min(1.0, score), sources
    if verdict == "BEARISH":
        score = -(0.5 + 0.5 * max(0.0, bear_pct - bull_pct))
        return "BEARISH", max(-1.0, score), sources
    return "NEUTRAL", 0.0, sources


def _bulk_deals_signal(symbol: str, days: int = 10) -> tuple[str, float, list[str]]:
    """
    Bulk/block deal direction for the symbol.

    Returns (signal, score, sources_used).
    Net institutional buying (BUY qty > SELL qty) → BULLISH.
    """
    try:
        from market.bulk_deals import get_bulk_deals

        deals = get_bulk_deals(days=days, symbol=symbol)
    except Exception:
        return "NEUTRAL", 0.0, []

    if not deals:
        return "NEUTRAL", 0.0, []

    buy_qty = sum(d.quantity for d in deals if d.deal_type == "BUY")
    sell_qty = sum(d.quantity for d in deals if d.deal_type == "SELL")
    sources = [
        f"Bulk deals {days}d: {len(deals)} deals (buy:{buy_qty:,} vs sell:{sell_qty:,} shares)"
    ]

    total = buy_qty + sell_qty
    if total == 0:
        return "NEUTRAL", 0.0, sources

    net_pct = (buy_qty - sell_qty) / total  # -1 to +1
    if net_pct > 0.30:
        return "BULLISH", min(1.0, net_pct), sources
    if net_pct < -0.30:
        return "BEARISH", max(-1.0, net_pct), sources
    return "NEUTRAL", net_pct, sources


def _breadth_signal() -> tuple[str, float, list[str]]:
    """
    Market breadth (advance/decline) as a macro context signal.

    Returns (signal, score, sources_used).
    BROAD_RALLY → BULLISH · BROAD_DECLINE → BEARISH · MIXED → NEUTRAL.
    """
    try:
        breadth = get_market_breadth()
    except Exception:
        return "NEUTRAL", 0.0, []

    if breadth.verdict == "UNAVAILABLE" or breadth.advances == 0:
        return "NEUTRAL", 0.0, []

    sources = [
        f"Breadth: {breadth.advances} adv / {breadth.declines} dec (A/D={breadth.ad_ratio:.2f})"
    ]

    if breadth.verdict == "BROAD_RALLY":
        return "BULLISH", min(1.0, breadth.ad_ratio / 2.0), sources
    if breadth.verdict == "BROAD_DECLINE":
        return "BEARISH", max(-1.0, -1.0 / max(breadth.ad_ratio, 0.1)), sources
    return "NEUTRAL", 0.0, sources


def get_sentiment(symbol: str, exchange: str = "NSE") -> SentimentSignal:
    """
    Aggregate India market sentiment for a symbol (#172).

    Combines four data signals with fixed weights:
      FII/DII flows  30% — net institutional flows over last 5 days
      News sentiment 25% — keyword scoring on last 10 headlines
      Bulk deals     25% — net buy vs sell in bulk/block deals (10 days)
      Market breadth 20% — NSE advance/decline ratio

    Returns a SentimentSignal with BULLISH / NEUTRAL / BEARISH verdict
    and 0-100 confidence.
    """
    sym = symbol.upper().replace(".NS", "").replace(".BO", "")

    # Gather signals from each component
    fii_signal, fii_score, fii_sources = _fii_dii_signal(days=5)
    news_signal, news_score, news_sources = _news_signal(sym)
    deal_signal, deal_score, deal_sources = _bulk_deals_signal(sym, days=10)
    breadth_signal, breadth_score, breadth_sources = _breadth_signal()

    component_signals = {
        "fii_dii": fii_signal,
        "news": news_signal,
        "bulk_deals": deal_signal,
        "breadth": breadth_signal,
    }
    component_scores = {
        "fii_dii": fii_score,
        "news": news_score,
        "bulk_deals": deal_score,
        "breadth": breadth_score,
    }

    # Weighted total score
    total_score = sum(component_scores[k] * _COMPONENT_WEIGHTS[k] for k in _COMPONENT_WEIGHTS)

    # Overall verdict
    if total_score >= 0.15:
        overall = "BULLISH"
    elif total_score <= -0.15:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    # Confidence: how strongly does the weighted score lean?
    confidence = int(min(100, abs(total_score) / 0.3 * 100))

    # Key driver: highest absolute weighted contribution
    weighted_contribs = {
        k: abs(component_scores[k] * _COMPONENT_WEIGHTS[k]) for k in _COMPONENT_WEIGHTS
    }
    key_driver_key = max(weighted_contribs, key=weighted_contribs.get)
    key_driver_labels = {
        "fii_dii": "FII/DII flows",
        "news": "news sentiment",
        "bulk_deals": "bulk deals",
        "breadth": "market breadth",
    }
    key_driver = f"{key_driver_labels[key_driver_key]} ({component_signals[key_driver_key]})"

    all_sources = fii_sources + news_sources + deal_sources + breadth_sources

    return SentimentSignal(
        symbol=sym,
        overall_signal=overall,
        confidence=confidence,
        breakdown=component_signals,
        key_driver=key_driver,
        sources=all_sources,
        score=round(total_score, 3),
    )
