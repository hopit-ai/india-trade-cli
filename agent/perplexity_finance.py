"""
agent/perplexity_finance.py
───────────────────────────
Perplexity Agent API — finance_search tool integration.

Perplexity launched finance_search in their Agent API (May 2026):
    https://docs.perplexity.ai/docs/agent-api/tools

Unlike the Sonar chat-completions API (generic web search), the Agent API
with finance_search routes to licensed financial datasets — NSE/BSE earnings,
analyst estimates, live quotes, fundamentals, and India-specific market news.

Configure via credentials / .env:
    PERPLEXITY_API_KEY=<your key>   # shared with Sonar web-search fallback

Usage:
    from agent.perplexity_finance import (
        perplexity_finance_available,
        finance_news_for_symbol,
        finance_fundamentals_for_symbol,
        finance_macro_india,
    )

    if perplexity_finance_available():
        result = finance_news_for_symbol("INFY")
        print(result.summary)      # full text with citations
        print(result.citations)    # list of source URLs
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests

# ── Constants ─────────────────────────────────────────────────────

AGENT_API_URL = "https://api.perplexity.ai/v1/agent"
DEFAULT_MODEL = "perplexity/sonar"  # cheaper; sonar-pro for deeper research

# Max chars of summary to pass to the LLM prompt (keep tokens manageable)
MAX_SUMMARY_CHARS = 2000

# Timeout for Agent API (finance_search can be slower than Sonar)
REQUEST_TIMEOUT = 20


# ── Data model ────────────────────────────────────────────────────


@dataclass
class FinanceSearchResult:
    """Result from a Perplexity finance_search Agent API call."""

    query: str
    summary: str  # LLM-synthesised answer (with inline citations)
    citations: list[str] = field(default_factory=list)  # source URLs
    model: str = DEFAULT_MODEL
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    def as_prompt_text(self, max_chars: int = MAX_SUMMARY_CHARS) -> str:
        """Return compact text for injecting into LLM prompts."""
        if self.error:
            return ""
        text = self.summary.strip()[:max_chars]
        if self.citations:
            sources = "\n".join(f"  • {u}" for u in self.citations[:3])
            text += f"\n\nSources:\n{sources}"
        return text


# ── Core API call ─────────────────────────────────────────────────


def _call_finance_search(query: str, model: str = DEFAULT_MODEL) -> FinanceSearchResult:
    """
    Call the Perplexity Agent API with the finance_search tool.

    The Agent API (v1/agent) uses the OpenAI Responses API format:
      POST /v1/agent
      { "model": "...", "input": "...", "tools": [{"type": "finance_search"}] }

    The response `output` array contains tool call events + a final message.
    We extract the last message's text content as the summary.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        return FinanceSearchResult(query=query, summary="", error="PERPLEXITY_API_KEY not set")

    payload: dict = {
        "model": model,
        "input": query,
        "tools": [{"type": "finance_search"}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            AGENT_API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        return FinanceSearchResult(
            query=query,
            summary="",
            error=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        )
    except Exception as e:
        return FinanceSearchResult(query=query, summary="", error=str(e))

    # Parse Responses API output array
    summary = ""
    citations: list[str] = []
    try:
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        summary = block.get("text", "")
            elif item.get("type") == "web_search_call":
                pass  # ignore intermediate search events

        # Citations are sometimes at top level
        for cite in data.get("citations", []):
            if isinstance(cite, str):
                citations.append(cite)
            elif isinstance(cite, dict) and cite.get("url"):
                citations.append(cite["url"])
    except Exception as parse_err:
        return FinanceSearchResult(
            query=query,
            summary="",
            error=f"Parse error: {parse_err}",
        )

    if not summary:
        # Some responses return choices-style (fallback)
        try:
            summary = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
        except (KeyError, IndexError, TypeError):
            return FinanceSearchResult(
                query=query,
                summary="",
                error="Empty response from Perplexity Agent API",
            )

    return FinanceSearchResult(
        query=query,
        summary=summary,
        citations=citations,
        model=model,
    )


# ── Public helpers ────────────────────────────────────────────────


def perplexity_finance_available() -> bool:
    """Return True if PERPLEXITY_API_KEY is configured."""
    return bool(os.environ.get("PERPLEXITY_API_KEY"))


def finance_news_for_symbol(
    symbol: str,
    context_hint: str = "",
    model: str = DEFAULT_MODEL,
) -> FinanceSearchResult:
    """
    Fetch latest India market news for *symbol* via Perplexity finance_search.

    Covers NSE/BSE earnings, analyst upgrades/downgrades, regulatory events,
    sector news, and FII activity — all with citations to primary sources.

    Args:
        symbol:       NSE ticker (e.g. "INFY", "RELIANCE", "NIFTY")
        context_hint: Optional user focus (e.g. "AI deals", "Q4 earnings")
        model:        Perplexity model to use
    """
    query = f"{symbol} India stock latest news earnings analyst 2026"
    if context_hint:
        query = f"{symbol} India {context_hint} stock news 2026"
    return _call_finance_search(query, model=model)


def finance_fundamentals_for_symbol(
    symbol: str,
    model: str = DEFAULT_MODEL,
) -> FinanceSearchResult:
    """
    Fetch fundamental data for *symbol*: PE ratio, ROE, ROCE, revenue growth,
    debt/equity, promoter holding, and analyst target prices.

    Useful as a fallback when the broker API doesn't have fundamental data.

    Args:
        symbol: NSE ticker (e.g. "INFY", "HDFC", "WIPRO")
        model:  Perplexity model to use
    """
    query = (
        f"{symbol} NSE India fundamentals PE ratio ROE ROCE revenue growth "
        f"profit margin debt equity promoter holding analyst target price 2026"
    )
    return _call_finance_search(query, model=model)


def finance_macro_india(
    context: str = "",
    model: str = DEFAULT_MODEL,
) -> FinanceSearchResult:
    """
    Fetch India macro market context: NIFTY outlook, FII flows, RBI policy,
    USD/INR, global cues, sector rotation trends.

    Used in the morning brief for richer narrative.

    Args:
        context: Optional focus (e.g. "RBI meeting", "Q4 results season")
        model:   Perplexity model to use
    """
    query = (
        "India stock market today NIFTY outlook FII DII flows RBI USD INR "
        "global cues sector rotation NSE BSE 2026"
    )
    if context:
        query = f"India stock market {context} outlook today 2026"
    return _call_finance_search(query, model=model)
