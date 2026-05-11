"""
tests/test_web_search.py
─────────────────────────
Tests for agent/web_search.py — Exa + Tavily + DuckDuckGo providers.

All network calls are mocked; no real API keys needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest


# ── WebSearchResult ───────────────────────────────────────────────────────────


class TestWebSearchResult:
    def test_basic_fields(self):
        from agent.web_search import WebSearchResult

        r = WebSearchResult(
            title="NIFTY update", url="https://example.com", snippet="Markets rose today"
        )
        assert r.title == "NIFTY update"
        assert r.url == "https://example.com"
        assert r.snippet == "Markets rose today"
        assert r.published_date is None
        assert r.source == ""

    def test_as_text_includes_title_and_url(self):
        from agent.web_search import WebSearchResult

        r = WebSearchResult(
            title="HDFC Q4 Results",
            url="https://economictimes.com/hdfc-q4",
            snippet="HDFC Bank reported strong Q4 results.",
            published_date="2025-04-20",
            source="exa",
        )
        text = r.as_text()
        assert "HDFC Q4 Results" in text
        assert "https://economictimes.com/hdfc-q4" in text
        assert "2025-04-20" in text

    def test_as_text_no_date(self):
        from agent.web_search import WebSearchResult

        r = WebSearchResult(title="T", url="https://x.com", snippet="S")
        text = r.as_text()
        # No date bracket when published_date is None
        assert "[None]" not in text


# ── helpers ───────────────────────────────────────────────────────────────────


def _mock_exa_module(instance: MagicMock) -> MagicMock:
    """Return a fake exa_py module whose Exa() returns *instance*."""
    mod = MagicMock()
    mod.Exa.return_value = instance
    return mod


def _mock_tavily_module(instance: MagicMock) -> MagicMock:
    """Return a fake tavily module whose TavilyClient() returns *instance*."""
    mod = MagicMock()
    mod.TavilyClient.return_value = instance
    return mod


def _exa_result(title, url, text="snippet text", published_date=None):
    r = MagicMock()
    r.title = title
    r.url = url
    r.text = text
    r.published_date = published_date
    return r


# ── _search_exa ───────────────────────────────────────────────────────────────


class TestSearchExa:
    def test_returns_results(self):
        from agent.web_search import _search_exa

        mock_instance = MagicMock()
        mock_instance.search_and_contents.return_value = MagicMock(
            results=[
                _exa_result("NIFTY update", "https://a.com", "Markets up 1%", "2025-05-01"),
                _exa_result("BANKNIFTY analysis", "https://b.com", "Bank stocks rally"),
            ]
        )

        with patch.dict("sys.modules", {"exa_py": _mock_exa_module(mock_instance)}):
            with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}):
                results = _search_exa("NIFTY outlook", n=5)

        assert len(results) == 2
        assert results[0].title == "NIFTY update"
        assert results[0].source == "exa"
        assert results[0].published_date == "2025-05-01"
        assert results[1].title == "BANKNIFTY analysis"

    def test_raises_without_api_key(self):
        from agent.web_search import _search_exa

        # Key check happens BEFORE the import — no module needed
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="EXA_API_KEY"):
                _search_exa("test query", n=3)

    def test_raises_on_import_error(self):
        from agent.web_search import _search_exa

        with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"exa_py": None}):
                with pytest.raises(ImportError, match="exa-py"):
                    _search_exa("test query", n=3)

    def test_calls_neural_type(self):
        from agent.web_search import _search_exa

        mock_instance = MagicMock()
        mock_instance.search_and_contents.return_value = MagicMock(results=[])

        with patch.dict("sys.modules", {"exa_py": _mock_exa_module(mock_instance)}):
            with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}):
                _search_exa("NIFTY", n=5)

        call_kwargs = mock_instance.search_and_contents.call_args
        assert call_kwargs.kwargs.get("type") == "neural" or "neural" in str(call_kwargs)

    def test_snippet_truncated_at_500(self):
        from agent.web_search import _search_exa

        long_text = "x" * 1000
        mock_instance = MagicMock()
        mock_instance.search_and_contents.return_value = MagicMock(
            results=[_exa_result("T", "https://x.com", long_text)]
        )

        with patch.dict("sys.modules", {"exa_py": _mock_exa_module(mock_instance)}):
            with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}):
                results = _search_exa("test", n=1)

        assert len(results[0].snippet) <= 500

    def test_handles_none_title(self):
        from agent.web_search import _search_exa

        mock_instance = MagicMock()
        mock_instance.search_and_contents.return_value = MagicMock(
            results=[_exa_result(None, "https://x.com")]
        )

        with patch.dict("sys.modules", {"exa_py": _mock_exa_module(mock_instance)}):
            with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}):
                results = _search_exa("test", n=1)

        assert results[0].title == ""


# ── _search_tavily ────────────────────────────────────────────────────────────


class TestSearchTavily:
    def _tavily_response(self, results: list[dict]) -> dict:
        return {"results": results, "query": "test"}

    def test_returns_results(self):
        from agent.web_search import _search_tavily

        mock_client = MagicMock()
        mock_client.search.return_value = self._tavily_response(
            [
                {
                    "title": "RELIANCE Q4",
                    "url": "https://c.com",
                    "content": "Strong results",
                    "published_date": "2025-04-15",
                },
                {"title": "Sensex rally", "url": "https://d.com", "content": "Up 500 pts"},
            ]
        )

        with patch.dict("sys.modules", {"tavily": _mock_tavily_module(mock_client)}):
            with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
                results = _search_tavily("RELIANCE results", n=5)

        assert len(results) == 2
        assert results[0].title == "RELIANCE Q4"
        assert results[0].source == "tavily"
        assert results[0].published_date == "2025-04-15"
        assert results[1].snippet == "Up 500 pts"

    def test_raises_without_api_key(self):
        from agent.web_search import _search_tavily

        # Key check happens BEFORE the import — no module needed
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="TAVILY_API_KEY"):
                _search_tavily("test", n=3)

    def test_raises_on_import_error(self):
        from agent.web_search import _search_tavily

        with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"tavily": None}):
                with pytest.raises(ImportError, match="tavily-python"):
                    _search_tavily("test", n=3)

    def test_empty_results_handled(self):
        from agent.web_search import _search_tavily

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch.dict("sys.modules", {"tavily": _mock_tavily_module(mock_client)}):
            with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
                results = _search_tavily("nothing found", n=5)

        assert results == []

    def test_calls_basic_depth(self):
        from agent.web_search import _search_tavily

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch.dict("sys.modules", {"tavily": _mock_tavily_module(mock_client)}):
            with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}):
                _search_tavily("query", n=3)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs.get("search_depth") == "basic"
        assert call_kwargs.kwargs.get("max_results") == 3


# ── _search_duckduckgo ────────────────────────────────────────────────────────


class TestSearchDuckDuckGo:
    def _ddg_response(self, abstract="", abstract_url="", topics=None):
        return {
            "AbstractText": abstract,
            "AbstractURL": abstract_url,
            "Heading": "Test",
            "RelatedTopics": topics or [],
        }

    def test_returns_abstract_as_first_result(self):
        from agent.web_search import _search_duckduckgo

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._ddg_response(
            abstract="NIFTY traded at 24500 today.",
            abstract_url="https://en.wikipedia.org/wiki/NIFTY",
        )

        with patch("httpx.get", return_value=mock_resp):
            results = _search_duckduckgo("NIFTY 50", n=5)

        assert len(results) >= 1
        assert results[0].url == "https://en.wikipedia.org/wiki/NIFTY"
        assert results[0].source == "duckduckgo"
        assert "24500" in results[0].snippet

    def test_includes_related_topics(self):
        from agent.web_search import _search_duckduckgo

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._ddg_response(
            topics=[
                {"Text": "BANKNIFTY is a sectoral index", "FirstURL": "https://ddg.gg/banknifty"},
                {"Text": "SENSEX tracks BSE top 30", "FirstURL": "https://ddg.gg/sensex"},
            ]
        )

        with patch("httpx.get", return_value=mock_resp):
            results = _search_duckduckgo("India indices", n=5)

        texts = [r.snippet for r in results]
        assert any("BANKNIFTY" in t for t in texts)

    def test_respects_n_limit(self):
        from agent.web_search import _search_duckduckgo

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._ddg_response(
            abstract="abstract",
            abstract_url="https://x.com",
            topics=[{"Text": f"Topic {i}", "FirstURL": f"https://t{i}.com"} for i in range(10)],
        )

        with patch("httpx.get", return_value=mock_resp):
            results = _search_duckduckgo("query", n=3)

        assert len(results) <= 3

    def test_skips_non_dict_topics(self):
        from agent.web_search import _search_duckduckgo

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._ddg_response(
            topics=[
                "not a dict",  # should be skipped
                {"Text": "Valid topic", "FirstURL": "https://v.com"},
            ]
        )

        with patch("httpx.get", return_value=mock_resp):
            results = _search_duckduckgo("query", n=5)

        # "not a dict" should not appear, valid topic should
        urls = [r.url for r in results]
        assert "https://v.com" in urls

    def test_empty_response_returns_empty_list(self):
        from agent.web_search import _search_duckduckgo

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = self._ddg_response()

        with patch("httpx.get", return_value=mock_resp):
            results = _search_duckduckgo("obscure query", n=5)

        assert results == []


# ── web_search (auto-select) ──────────────────────────────────────────────────


class TestWebSearch:
    def _make_exa_result(self):
        from agent.web_search import WebSearchResult

        return [
            WebSearchResult(
                title="Exa result", url="https://exa.com", snippet="from exa", source="exa"
            )
        ]

    def _make_tavily_result(self):
        from agent.web_search import WebSearchResult

        return [
            WebSearchResult(
                title="Tavily result",
                url="https://tavily.com",
                snippet="from tavily",
                source="tavily",
            )
        ]

    def _make_ddg_result(self):
        from agent.web_search import WebSearchResult

        return [
            WebSearchResult(
                title="DDG result", url="https://ddg.com", snippet="from ddg", source="duckduckgo"
            )
        ]

    def test_uses_exa_when_key_present(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "key", "TAVILY_API_KEY": ""}):
            with patch(
                "agent.web_search._search_exa", return_value=self._make_exa_result()
            ) as mock_exa:
                results = web_search("NIFTY")

        mock_exa.assert_called_once()
        assert results[0].source == "exa"

    def test_falls_back_to_tavily_when_exa_key_missing(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "", "TAVILY_API_KEY": "key"}):
            with patch("agent.web_search._search_exa") as mock_exa:
                with patch(
                    "agent.web_search._search_tavily", return_value=self._make_tavily_result()
                ) as mock_tavily:
                    results = web_search("NIFTY")

        mock_exa.assert_not_called()
        mock_tavily.assert_called_once()
        assert results[0].source == "tavily"

    def test_falls_back_to_tavily_when_exa_fails(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "key", "TAVILY_API_KEY": "key2"}):
            with patch("agent.web_search._search_exa", side_effect=Exception("network error")):
                with patch(
                    "agent.web_search._search_tavily", return_value=self._make_tavily_result()
                ):
                    results = web_search("NIFTY")

        assert results[0].source == "tavily"

    def test_falls_back_to_duckduckgo_when_both_fail(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "key", "TAVILY_API_KEY": "key2"}):
            with patch("agent.web_search._search_exa", side_effect=Exception("fail")):
                with patch("agent.web_search._search_tavily", side_effect=Exception("fail")):
                    with patch(
                        "agent.web_search._search_duckduckgo", return_value=self._make_ddg_result()
                    ):
                        results = web_search("NIFTY")

        assert results[0].source == "duckduckgo"

    def test_returns_empty_list_when_all_fail(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {}, clear=True):
            with patch("agent.web_search._search_duckduckgo", side_effect=Exception("no network")):
                results = web_search("test")

        assert results == []

    def test_explicit_provider_exa(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "key"}):
            with patch(
                "agent.web_search._search_exa", return_value=self._make_exa_result()
            ) as mock_exa:
                with patch("agent.web_search._search_tavily") as mock_tavily:
                    web_search("test", provider="exa")

        mock_exa.assert_called_once()
        mock_tavily.assert_not_called()

    def test_explicit_provider_tavily(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"TAVILY_API_KEY": "key"}):
            with patch("agent.web_search._search_exa") as mock_exa:
                with patch(
                    "agent.web_search._search_tavily", return_value=self._make_tavily_result()
                ) as mock_tavily:
                    web_search("test", provider="tavily")

        mock_exa.assert_not_called()
        mock_tavily.assert_called_once()

    def test_unknown_provider_raises(self):
        from agent.web_search import web_search

        with pytest.raises(ValueError, match="Unknown search provider"):
            web_search("test", provider="bing")

    def test_exa_empty_results_falls_through_to_tavily(self):
        from agent.web_search import web_search

        with patch.dict("os.environ", {"EXA_API_KEY": "key", "TAVILY_API_KEY": "key2"}):
            with patch("agent.web_search._search_exa", return_value=[]):  # empty, not exception
                with patch(
                    "agent.web_search._search_tavily", return_value=self._make_tavily_result()
                ) as mock_tavily:
                    results = web_search("NIFTY")

        mock_tavily.assert_called_once()
        assert results[0].source == "tavily"


# ── available_providers ───────────────────────────────────────────────────────


class TestAvailableProviders:
    def test_both_keys_configured(self):
        from agent.web_search import available_providers

        with patch.dict("os.environ", {"EXA_API_KEY": "k1", "TAVILY_API_KEY": "k2"}):
            providers = available_providers()

        assert "exa" in providers
        assert "tavily" in providers
        assert "duckduckgo" in providers

    def test_only_exa_configured(self):
        from agent.web_search import available_providers

        with patch.dict("os.environ", {"EXA_API_KEY": "k1", "TAVILY_API_KEY": ""}):
            providers = available_providers()

        assert "exa" in providers
        assert "tavily" not in providers
        assert "duckduckgo" in providers  # always present

    def test_no_keys_configured(self):
        from agent.web_search import available_providers

        with patch.dict("os.environ", {}, clear=True):
            providers = available_providers()

        assert "exa" not in providers
        assert "tavily" not in providers
        assert "duckduckgo" in providers  # free fallback always listed
