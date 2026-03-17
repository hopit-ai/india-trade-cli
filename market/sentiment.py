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
from datetime    import date
from typing      import Optional

import httpx

from market.news import NewsItem


# ── FII / DII Data ───────────────────────────────────────────

@dataclass
class FIIDIIData:
    date:          str
    fii_buy:       float       # INR crore
    fii_sell:      float
    fii_net:       float       # positive = buying, negative = selling
    dii_buy:       float
    dii_sell:      float
    dii_net:       float
    verdict:       str         # "FII_BUYING" | "FII_SELLING" | "NEUTRAL"


NSE_FIIDII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"


def get_fii_dii_data(days: int = 5) -> list[FIIDIIData]:
    """
    FII / DII buy-sell activity from NSE (last N trading days).
    Falls back to mock data if NSE API is unavailable.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept":     "application/json",
            "Referer":    "https://www.nseindia.com",
        }
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(NSE_FIIDII_URL, headers=headers, timeout=8)
        r.raise_for_status()
        data = r.json()

        result = []
        for item in data[:days]:
            fii_net = float(item.get("fiiNetBuySell", 0))
            dii_net = float(item.get("diiNetBuySell", 0))
            verdict = (
                "FII_BUYING"  if fii_net > 500 else
                "FII_SELLING" if fii_net < -500 else
                "NEUTRAL"
            )
            result.append(FIIDIIData(
                date     = item.get("tradeDate", ""),
                fii_buy  = float(item.get("fiiBuyValue",  0)),
                fii_sell = float(item.get("fiiSellValue", 0)),
                fii_net  = fii_net,
                dii_buy  = float(item.get("diiBuyValue",  0)),
                dii_sell = float(item.get("diiSellValue", 0)),
                dii_net  = dii_net,
                verdict  = verdict,
            ))
        return result

    except Exception:
        return _mock_fii_dii(days)


def _mock_fii_dii(days: int = 5) -> list[FIIDIIData]:
    """Synthetic FII/DII data for demo mode."""
    import random
    random.seed(42)
    today    = date.today()
    results  = []
    from datetime import timedelta
    for i in range(days):
        day     = today - timedelta(days=i + 1)
        fii_net = round(random.gauss(500, 2000), 2)
        dii_net = round(random.gauss(-200, 1000), 2)
        results.append(FIIDIIData(
            date     = day.isoformat(),
            fii_buy  = round(abs(fii_net) + random.uniform(5000, 15000), 2),
            fii_sell = round(abs(fii_net) + random.uniform(4000, 14000), 2),
            fii_net  = fii_net,
            dii_buy  = round(abs(dii_net) + random.uniform(3000, 10000), 2),
            dii_sell = round(abs(dii_net) + random.uniform(3000, 10000), 2),
            dii_net  = dii_net,
            verdict  = "FII_BUYING" if fii_net > 500 else "FII_SELLING" if fii_net < -500 else "NEUTRAL",
        ))
    return results


# ── News Sentiment ────────────────────────────────────────────

BULLISH_WORDS = {
    "surge", "rally", "gain", "jump", "rise", "high", "record", "strong",
    "beat", "outperform", "upgrade", "buy", "positive", "growth", "profit",
    "upside", "bull", "breakout", "momentum", "recovery", "boom",
}

BEARISH_WORDS = {
    "fall", "drop", "crash", "slump", "decline", "low", "weak", "loss",
    "miss", "underperform", "downgrade", "sell", "negative", "concern",
    "downside", "bear", "breakdown", "pressure", "recession", "crisis",
    "war", "inflation", "rate hike", "debt",
}


def score_headline(title: str) -> tuple[str, float]:
    """
    Simple keyword-based sentiment scoring for a headline.
    Returns (verdict, score) where score is -1.0 to +1.0.
    """
    words = set(re.sub(r"[^a-z\s]", "", title.lower()).split())
    bull  = len(words & BULLISH_WORDS)
    bear  = len(words & BEARISH_WORDS)
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
        scored.append({
            "title":   item.title,
            "source":  item.source,
            "verdict": verdict,
            "score":   score,
        })

    bullish = sum(1 for s in scored if s["verdict"] == "BULLISH")
    bearish = sum(1 for s in scored if s["verdict"] == "BEARISH")
    neutral = sum(1 for s in scored if s["verdict"] == "NEUTRAL")

    avg_score = sum(s["score"] for s in scored) / len(scored) if scored else 0.0
    overall   = "BULLISH" if avg_score > 0.1 else "BEARISH" if avg_score < -0.1 else "NEUTRAL"

    return {
        "overall":       overall,
        "score":         round(avg_score, 3),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "items":         scored,
    }


# ── Market Breadth (Advance / Decline) ───────────────────────

@dataclass
class MarketBreadth:
    advances:  int
    declines:  int
    unchanged: int
    ad_ratio:  float        # advances / declines
    verdict:   str          # "BROAD_RALLY" | "BROAD_DECLINE" | "MIXED"


def get_market_breadth() -> MarketBreadth:
    """
    Advance/Decline ratio from NSE.
    Falls back to mock if NSE unavailable.
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
            "https://www.nseindia.com/api/allIndices",
            headers=headers, timeout=8,
        )
        r.raise_for_status()
        # Parse NIFTY 500 advances/declines
        data = r.json().get("data", [])
        nifty500 = next((d for d in data if "500" in d.get("index", "")), None)
        if nifty500:
            adv  = int(nifty500.get("advances", 0))
            dec  = int(nifty500.get("declines", 0))
            unch = int(nifty500.get("unchanged", 0))
            return _build_breadth(adv, dec, unch)
    except Exception:
        pass

    # Mock: slightly bullish market
    import random
    random.seed(1)
    adv  = random.randint(280, 380)
    dec  = random.randint(120, 220)
    unch = 500 - adv - dec
    return _build_breadth(adv, dec, unch)


def _build_breadth(adv: int, dec: int, unch: int) -> MarketBreadth:
    ratio   = adv / max(dec, 1)
    verdict = (
        "BROAD_RALLY"   if ratio > 2.0 else
        "BROAD_DECLINE" if ratio < 0.5 else
        "MIXED"
    )
    return MarketBreadth(
        advances  = adv,
        declines  = dec,
        unchanged = unch,
        ad_ratio  = round(ratio, 2),
        verdict   = verdict,
    )
