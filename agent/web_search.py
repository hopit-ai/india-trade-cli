"""
agent/web_search.py
────────────────────
Web search integration for the trading agent.

Providers (tried in priority order when no provider is specified):
  1. Exa         — neural search, excellent for financial / news queries (EXA_API_KEY)
  2. Tavily      — research-focused, well-structured results (TAVILY_API_KEY)
  3. DuckDuckGo  — free, no key required, lower fidelity fallback (httpx)

Usage:
    from agent.web_search import web_search

    results = web_search("NIFTY 50 outlook this week", n=5)
    for r in results:
        print(r.title)
        print(r.snippet[:200])

    # Explicit provider:
    results = web_search("RELIANCE Q4 results", n=3, provider="tavily")

The function never raises — it returns an empty list on total failure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


# ── Data model ────────────────────────────────────────────────


@dataclass
class WebSearchResult:
    """A single search result from any provider."""

    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    source: str = ""  # "exa" | "tavily" | "duckduckgo"
    score: float = 0.0

    @property
    def text(self) -> str:
        """Backward-compat alias for snippet."""
        return self.snippet

    def as_text(self) -> str:
        """One-liner for terminal display."""
        date_str = f"  [{self.published_date}]" if self.published_date else ""
        return f"• {self.title}{date_str}\n  {self.url}\n  {self.snippet[:200]}"


@dataclass
class SearchResult:
    """Backward-compat class (PR #202 API) — uses 'text' field name instead of 'snippet'."""

    title: str = ""
    url: str = ""
    text: str = ""
    score: float = 0.0
    published_date: Optional[str] = None
    source: str = ""

    @property
    def snippet(self) -> str:
        """Alias for text — lets format_search_results work with both classes."""
        return self.text


# ── Public API ────────────────────────────────────────────────


def web_search(
    query: str,
    n: int = 5,
    provider: Optional[str] = None,
    *,
    max_results: Optional[int] = None,  # alias for n — used by multi_agent.py
) -> list[WebSearchResult]:
    """
    Search the web and return up to *n* results.

    Args:
        query:       Natural-language search query.
        n:           Max results (default 5). Also accepted as max_results=.
        provider:    "exa" | "tavily" | "duckduckgo" | "perplexity" | None (auto-select).

    Returns:
        List of WebSearchResult (may be empty if all providers fail).
    """
    limit = min(max_results if max_results is not None else n, 5)
    if provider:
        # Try explicit provider; if it raises, fall through to auto-select.
        # Return immediately on success (even empty — caller chose the provider).
        try:
            return _dispatch(provider.lower(), query, limit)
        except ValueError:
            raise  # unknown provider name → propagate
        except Exception:
            pass  # provider failed (network / key error) → try auto-select below

    # Auto-select: first provider whose API key is configured
    for name, key_env in [
        ("exa", "EXA_API_KEY"),
        ("tavily", "TAVILY_API_KEY"),
        ("perplexity", "PERPLEXITY_API_KEY"),
    ]:
        if os.environ.get(key_env):
            try:
                results = _dispatch(name, query, limit)
                if results:
                    return results
            except Exception:
                continue  # fall through to next provider

    # Free fallback — always try even without a key
    try:
        return _search_duckduckgo(query, limit)
    except Exception:
        return []


def available_providers() -> list[str]:
    """Return list of providers whose API keys are currently configured."""
    providers = []
    if os.environ.get("EXA_API_KEY"):
        providers.append("exa")
    if os.environ.get("TAVILY_API_KEY"):
        providers.append("tavily")
    if os.environ.get("PERPLEXITY_API_KEY"):
        providers.append("perplexity")
    providers.append("duckduckgo")  # always available (free)
    return providers


def web_search_available() -> bool:
    """Return True if at least one keyed provider (Exa/Tavily/Perplexity) is configured."""
    return bool(
        os.environ.get("EXA_API_KEY")
        or os.environ.get("TAVILY_API_KEY")
        or os.environ.get("PERPLEXITY_API_KEY")
    )


def format_search_results(results: list[WebSearchResult]) -> str:
    """Format a list of results into a compact text block for LLM prompts."""
    if not results:
        return ""
    lines = []
    for i, r in enumerate(results, 1):
        date = f" [{r.published_date}]" if r.published_date else ""
        lines.append(f"{i}. {r.title}{date}")
        lines.append(f"   {r.url}")
        if r.snippet:
            lines.append(f"   {r.snippet[:300]}")
    return "\n".join(lines)


# ── Dispatcher ────────────────────────────────────────────────


def _dispatch(provider: str, query: str, n: int) -> list[WebSearchResult]:
    if provider == "exa":
        return _exa_search(query, n)
    elif provider == "tavily":
        return _tavily_search(query, n)
    elif provider == "duckduckgo":
        return _search_duckduckgo(query, n)
    elif provider == "perplexity":
        return _perplexity_search(query, n)
    else:
        raise ValueError(
            f"Unknown search provider: {provider!r}. "
            "Use 'exa', 'tavily', 'duckduckgo', or 'perplexity'."
        )


# ── Exa ───────────────────────────────────────────────────────


def _exa_search(query: str, n: int) -> list[WebSearchResult]:
    """
    Exa neural search (exa.ai).
    Uses semantic / neural search — far better than keyword search for
    financial queries like 'NIFTY support levels this week'.

    Requires: EXA_API_KEY env var, exa-py package.
    """
    key = os.environ.get("EXA_API_KEY")
    if not key:
        raise ValueError("EXA_API_KEY not set")

    try:
        from exa_py import Exa
    except ImportError as e:
        raise ImportError("exa-py not installed. Run: pip install exa-py") from e

    exa = Exa(api_key=key)
    response = exa.search_and_contents(
        query,
        num_results=n,
        text={"max_characters": 500},
        type="neural",
    )

    results = []
    for r in response.results:
        results.append(
            WebSearchResult(
                title=r.title or "",
                url=r.url or "",
                snippet=(r.text or "")[:500],
                published_date=getattr(r, "published_date", None),
                source="exa",
            )
        )
    return results


# ── Tavily ────────────────────────────────────────────────────


def _tavily_search(
    query: str, n: int = 5, *, max_results: Optional[int] = None
) -> list[WebSearchResult]:
    """
    Tavily research-focused search (tavily.com).
    Returns well-structured results with content snippets.

    Requires: TAVILY_API_KEY env var, tavily-python package.
    """
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY not set")

    limit = max_results if max_results is not None else n

    try:
        from tavily import TavilyClient
    except ImportError as e:
        raise ImportError("tavily-python not installed. Run: pip install tavily-python") from e

    client = TavilyClient(api_key=key)
    response = client.search(query, max_results=limit, search_depth="basic")

    results = []
    for r in response.get("results", []):
        results.append(
            WebSearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                published_date=r.get("published_date"),
                source="tavily",
                score=r.get("score", 0.0),
            )
        )
    return results


# ── DuckDuckGo (free fallback) ────────────────────────────────


def _search_duckduckgo(query: str, n: int) -> list[WebSearchResult]:
    """
    DuckDuckGo Instant Answer API — free, no key needed.
    Returns fewer / lower-quality results than Exa/Tavily but always available.
    Hits the public DDG JSON API (no scraping).
    """
    import urllib.parse

    try:
        import httpx
    except ImportError as e:
        raise ImportError("httpx not installed. Run: pip install httpx") from e

    encoded = urllib.parse.quote_plus(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
    resp = httpx.get(url, timeout=10.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    results = []

    # Abstract (single top result)
    if data.get("AbstractText") and data.get("AbstractURL"):
        results.append(
            WebSearchResult(
                title=data.get("Heading", query),
                url=data["AbstractURL"],
                snippet=data["AbstractText"][:500],
                source="duckduckgo",
            )
        )

    # Related topics as additional results
    for topic in data.get("RelatedTopics", []):
        if len(results) >= n:
            break
        if not isinstance(topic, dict) or "Text" not in topic:
            continue
        results.append(
            WebSearchResult(
                title=topic.get("Text", "")[:120],
                url=topic.get("FirstURL", ""),
                snippet=topic.get("Text", ""),
                source="duckduckgo",
            )
        )

    return results[:n]


# ── Perplexity Sonar ──────────────────────────────────────────


def _perplexity_search(query: str, n: int) -> list[WebSearchResult]:
    """
    Perplexity Sonar search (perplexity.ai).
    Returns an AI-synthesised answer with citations.

    Requires: PERPLEXITY_API_KEY env var, requests package.
    """
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        raise ValueError("PERPLEXITY_API_KEY not set")

    try:
        import requests
    except ImportError as e:
        raise ImportError("requests not installed. Run: pip install requests") from e

    headers = {
        "Authorization": f"Bearer {key}",
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

    results: list[WebSearchResult] = [
        WebSearchResult(
            title="Perplexity answer",
            url="",
            snippet=answer[:500],
            source="perplexity",
        )
    ]
    for cite in citations[: n - 1]:
        if isinstance(cite, str):
            results.append(
                WebSearchResult(title="Citation", url=cite, snippet="", source="perplexity")
            )
        elif isinstance(cite, dict):
            results.append(
                WebSearchResult(
                    title=cite.get("title", ""),
                    url=cite.get("url", ""),
                    snippet=cite.get("snippet", ""),
                    source="perplexity",
                )
            )
    return results


# ── Backward-compat aliases ───────────────────────────────────
# PR #202 tests reference the older _search_* naming convention.
# These aliases let both test suites pass without duplication.

_search_exa = _exa_search
_search_tavily = _tavily_search
_search_perplexity = _perplexity_search
