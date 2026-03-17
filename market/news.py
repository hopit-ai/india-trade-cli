"""
market/news.py
──────────────
News fetching from multiple sources:
  1. NewsAPI.org       — global + Indian business news by keyword/ticker
  2. RSS feeds         — ET Markets, MoneyControl, Business Standard, Hindu BL
  3. NSE announcements — corporate filings via NSE public API

All functions return a list of NewsItem dicts:
    { title, source, url, published, summary }
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime    import datetime, timezone
from typing      import Optional

import feedparser
import httpx


# ── NewsItem ─────────────────────────────────────────────────

@dataclass
class NewsItem:
    title:     str
    source:    str
    url:       str
    published: str          # ISO datetime string
    summary:   str = ""


# ── RSS feed definitions ──────────────────────────────────────

RSS_FEEDS = {
    "ET Markets":         "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "ET Stocks":          "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "MoneyControl":       "https://www.moneycontrol.com/rss/latestnews.xml",
    "Business Standard":  "https://www.business-standard.com/rss/markets-106.rss",
    "Hindu BL":           "https://www.thehindubusinessline.com/markets/?service=rss",
    "LiveMint Markets":   "https://www.livemint.com/rss/markets",
}

NSE_ANNOUNCEMENTS_URL = (
    "https://www.nseindia.com/api/corporate-announcements"
    "?index=equities&symbol={symbol}"
)

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"


# ── RSS helper ────────────────────────────────────────────────

def get_rss_feed(url: str, source: str = "RSS", n: int = 10) -> list[NewsItem]:
    """
    Parse any RSS feed and return the latest n items.
    Gracefully returns empty list on failure.
    """
    try:
        feed    = feedparser.parse(url)
        items   = []
        for entry in feed.entries[:n]:
            published = entry.get("published", entry.get("updated", ""))
            # Normalise to ISO string
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published = dt.isoformat()
            items.append(NewsItem(
                title     = entry.get("title", "").strip(),
                source    = source,
                url       = entry.get("link", ""),
                published = published,
                summary   = _strip_html(entry.get("summary", "")),
            ))
        return items
    except Exception:
        return []


def _strip_html(text: str) -> str:
    """Remove HTML tags from summary text."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()[:400]


# ── NewsAPI ───────────────────────────────────────────────────

def get_stock_news(symbol: str, n: int = 10) -> list[NewsItem]:
    """
    Latest news for a stock symbol via NewsAPI.org.
    Falls back to RSS if API key not set.

    Args:
        symbol: NSE symbol e.g. "RELIANCE", "HDFCBANK"
        n:      Number of articles (max 100 per call on free tier)
    """
    from config.credentials import get_credential
    api_key = get_credential("NEWSAPI_KEY", "NewsAPI.org Key", secret=True, required=False)

    if api_key:
        return _newsapi_fetch(
            query   = f"{symbol} stock India NSE",
            api_key = api_key,
            n       = n,
        )

    # Fallback: scan ET Markets RSS for symbol mentions
    all_items = get_rss_feed(RSS_FEEDS["ET Markets"], "ET Markets", 50)
    matched   = [i for i in all_items if symbol.upper() in i.title.upper()]
    return matched[:n] or all_items[:n]


def get_market_news(n: int = 20) -> list[NewsItem]:
    """
    Broad Indian market headlines from ET + MoneyControl RSS feeds.
    Returns merged, deduplicated, sorted by recency.
    """
    items: list[NewsItem] = []
    for source, url in list(RSS_FEEDS.items())[:3]:     # top 3 feeds
        items.extend(get_rss_feed(url, source, n=10))

    # Deduplicate by title similarity
    seen:   set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.title[:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Sort descending by published (best-effort — string sort works for ISO dates)
    unique.sort(key=lambda x: x.published, reverse=True)
    return unique[:n]


def _newsapi_fetch(query: str, api_key: str, n: int = 10) -> list[NewsItem]:
    """Fetch from NewsAPI.org /everything endpoint."""
    try:
        r = httpx.get(
            NEWSAPI_ENDPOINT,
            params={
                "q":        query,
                "language": "en",
                "sortBy":   "publishedAt",
                "pageSize": min(n, 100),
                "apiKey":   api_key,
            },
            timeout=8,
        )
        r.raise_for_status()
        articles = r.json().get("articles", [])
        return [
            NewsItem(
                title     = a.get("title", "").strip(),
                source    = a.get("source", {}).get("name", "NewsAPI"),
                url       = a.get("url", ""),
                published = a.get("publishedAt", ""),
                summary   = (a.get("description") or "")[:400],
            )
            for a in articles
            if a.get("title") and "[Removed]" not in a.get("title", "")
        ]
    except Exception:
        return []


# ── NSE Corporate Announcements ───────────────────────────────

def get_nse_announcements(symbol: str, n: int = 5) -> list[NewsItem]:
    """
    Recent corporate announcements from NSE for a symbol.
    Public endpoint — no auth needed.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept":     "application/json",
            "Referer":    "https://www.nseindia.com",
        }
        # NSE requires a session cookie from their homepage first
        session = httpx.Client(follow_redirects=True)
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(
            NSE_ANNOUNCEMENTS_URL.format(symbol=symbol.upper()),
            headers=headers,
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        items = []
        for ann in data[:n]:
            items.append(NewsItem(
                title     = ann.get("subject", ann.get("desc", "Announcement")),
                source    = "NSE",
                url       = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements",
                published = ann.get("an_dt", ""),
                summary   = ann.get("attchmntText", "")[:400],
            ))
        return items
    except Exception:
        return []
