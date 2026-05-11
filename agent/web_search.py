"""
agent/web_search.py
───────────────────
Web search tool for the News/Macro analyst (#149).

Provider priority (first available key wins, each falls back to the next):
  1. Exa         — semantic search, full page content (EXA_API_KEY)
  2. Tavily      — AI-native search, structured results  (TAVILY_API_KEY)
  3. Perplexity  — summarised answer + citations        (PERPLEXITY_API_KEY)

Configure via credentials / .env:
    EXA_API_KEY=<your key>          # primary — best for finance news
    TAVILY_API_KEY=<your key>       # free tier: 1 000 searches/month (no CC)
    PERPLEXITY_API_KEY=<your key>   # fallback — also used for Finance Agent API

Only one key is needed; having multiple gives automatic failover.

Usage (within analyst):
    from agent.web_search import web_search, web_search_available

    if web_search_available():
        results = web_search("Infosys AI deal Topaz revenue Q4 2026", max_results=3)
        for r in results:
            print(r.title, r.url)
            print(r.text[:500])
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    text: str  # Full or summarised page content
    published_date: Optional[str] = None
    author: Optional[str] = None
    score: float = 0.0  # Relevance score (provider-specific)


# ── Provider: Exa ────────────────────────────────────────────────


def _exa_search(query: str, max_results: int = 3) -> list[SearchResult]:
    """
    Search using Exa (semantic search, returns full page content).
    Requires EXA_API_KEY.
    """
    try:
        from exa_py import Exa  # pip install exa-py
    except ImportError:
        raise RuntimeError(
            "exa-py not installed. Run: pip install exa-py\n"
            "Then set EXA_API_KEY via: credentials set EXA_API_KEY"
        )

    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        raise RuntimeError("EXA_API_KEY not set. Run: credentials set EXA_API_KEY")

    exa = Exa(api_key=api_key)
    response = exa.search_and_contents(
        query,
        num_results=max_results,
        text={"max_characters": 1500},  # enough context without token bloat
        use_autoprompt=True,  # Exa rewrites query for better results
    )

    results = []
    for item in response.results:
        results.append(
            SearchResult(
                title=getattr(item, "title", "") or "",
                url=getattr(item, "url", "") or "",
                text=getattr(item, "text", "") or "",
                published_date=getattr(item, "published_date", None),
                author=getattr(item, "author", None),
                score=getattr(item, "score", 0.0) or 0.0,
            )
        )
    return results


# ── Provider: Tavily ─────────────────────────────────────────────


def _tavily_search(query: str, max_results: int = 3) -> list[SearchResult]:
    """
    Search using Tavily (AI-native search, returns structured results).
    Free tier: 1 000 searches/month at https://app.tavily.com — no credit card.
    Requires TAVILY_API_KEY.
    """
    try:
        from tavily import TavilyClient  # pip install tavily-python
    except ImportError:
        raise RuntimeError(
            "tavily-python not installed. Run: pip install tavily-python\n"
            "Get a free key at https://app.tavily.com — no credit card required."
        )

    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set. Run: credentials set TAVILY_API_KEY")

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query,
        search_depth="basic",  # "advanced" is slower but more thorough
        max_results=max_results,
        include_answer=False,  # raw results, not a synthesised answer
    )

    results = []
    for item in response.get("results", []):
        results.append(
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                text=item.get("content", "")[:1500],
                published_date=item.get("published_date"),
                score=float(item.get("score", 0.0)),
            )
        )
    return results


# ── Provider: Perplexity Sonar ────────────────────────────────────


def _perplexity_search(query: str, max_results: int = 3) -> list[SearchResult]:
    """
    Search using Perplexity Sonar API (returns summarised answer + citations).
    Requires PERPLEXITY_API_KEY.
    """
    import requests

    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY not set.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": query}],
        "max_tokens": 800,
        "return_citations": True,
    }
    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    answer = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])

    # Return main answer as first result, citations as additional
    results = [SearchResult(title="Perplexity answer", url="", text=answer)]
    for cite in citations[: max_results - 1]:
        if isinstance(cite, str):
            results.append(SearchResult(title="Citation", url=cite, text=""))
        elif isinstance(cite, dict):
            results.append(
                SearchResult(
                    title=cite.get("title", ""),
                    url=cite.get("url", ""),
                    text=cite.get("snippet", ""),
                )
            )
    return results


# ── Public API ───────────────────────────────────────────────────

MAX_SEARCHES_PER_ANALYSIS = 3  # cap to limit latency + cost

# Priority order for auto-detection
_PROVIDER_PRIORITY = [
    ("exa", "EXA_API_KEY"),
    ("tavily", "TAVILY_API_KEY"),
    ("perplexity", "PERPLEXITY_API_KEY"),
]


def web_search_available() -> bool:
    """Return True if at least one search provider is configured."""
    return any(os.environ.get(key) for _, key in _PROVIDER_PRIORITY)


def _detect_provider() -> str:
    """Return the name of the first configured provider."""
    for name, key in _PROVIDER_PRIORITY:
        if os.environ.get(key):
            return name
    return "exa"  # will fail gracefully


def _call_provider(name: str, query: str, max_results: int) -> list[SearchResult]:
    """Dispatch to the named provider function."""
    if name == "exa":
        return _exa_search(query, max_results)
    if name == "tavily":
        return _tavily_search(query, max_results)
    return _perplexity_search(query, max_results)


def web_search(
    query: str,
    max_results: int = 3,
    provider: Optional[str] = None,
) -> list[SearchResult]:
    """
    Search the web for the given query.

    Auto-detects available provider (Exa → Tavily → Perplexity).
    Returns [] on any failure — web search is always best-effort.

    Args:
        query:       Natural language search query
        max_results: Maximum results to return (capped at 5)
        provider:    Force "exa", "tavily", or "perplexity"; auto-detect if None

    Returns:
        List of SearchResult objects, empty on failure.
    """
    max_results = min(max_results, 5)

    primary = (provider or "").lower() or _detect_provider()

    # Try primary provider
    try:
        return _call_provider(primary, query, max_results)
    except Exception:
        pass

    # Fallback through remaining providers in priority order
    for name, key in _PROVIDER_PRIORITY:
        if name == primary or not os.environ.get(key):
            continue
        try:
            return _call_provider(name, query, max_results)
        except Exception:
            continue

    return []


def format_search_results(results: list[SearchResult]) -> str:
    """
    Format search results as compact text for LLM consumption.
    Strips excessive whitespace; caps each result at 1200 chars.
    """
    if not results:
        return ""

    parts = []
    for i, r in enumerate(results, 1):
        header = f"[{i}] {r.title}"
        if r.url:
            header += f"\nSource: {r.url}"
        if r.published_date:
            header += f" ({r.published_date[:10]})"
        text = (r.text or "").strip()[:1200]
        parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(parts)
