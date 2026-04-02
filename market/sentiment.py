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

    NSE API returns a flat list with separate entries for FII and DII
    per date. We group them into one record per date.
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
                by_date[dt] = {"fii_buy": 0, "fii_sell": 0, "fii_net": 0,
                               "dii_buy": 0, "dii_sell": 0, "dii_net": 0}

            if "FII" in category or "FPI" in category:
                by_date[dt]["fii_buy"] = buy_val
                by_date[dt]["fii_sell"] = sell_val
                by_date[dt]["fii_net"] = net_val
            elif "DII" in category:
                by_date[dt]["dii_buy"] = buy_val
                by_date[dt]["dii_sell"] = sell_val
                by_date[dt]["dii_net"] = net_val

        result = []
        for dt, vals in list(by_date.items())[:days]:
            fii_net = vals["fii_net"]
            verdict = (
                "FII_BUYING"  if fii_net > 500 else
                "FII_SELLING" if fii_net < -500 else
                "NEUTRAL"
            )
            result.append(FIIDIIData(
                date     = dt,
                fii_buy  = vals["fii_buy"],
                fii_sell = vals["fii_sell"],
                fii_net  = fii_net,
                dii_buy  = vals["dii_buy"],
                dii_sell = vals["dii_sell"],
                dii_net  = vals["dii_net"],
                verdict  = verdict,
            ))
        return result

    except Exception:
        return []  # No fake data — return empty list when NSE API fails


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

    # No mock data — return zeros so consumers know data is unavailable
    return MarketBreadth(advances=0, declines=0, unchanged=0, ad_ratio=0.0, verdict="UNAVAILABLE")


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
