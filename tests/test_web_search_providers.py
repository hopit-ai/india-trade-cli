"""
tests/test_web_search_providers.py
───────────────────────────────────
Tests for multi-provider web search (Exa → Tavily → Perplexity) and
yfinance-first fundamentals fallback in FundamentalAnalyst.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── web_search_available ──────────────────────────────────────────


class TestWebSearchAvailable:
    def test_false_when_no_keys(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        from agent.web_search import web_search_available

        assert web_search_available() is False

    def test_true_when_only_tavily(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        from agent.web_search import web_search_available

        assert web_search_available() is True

    def test_true_when_only_exa(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "exa-test")
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        from agent.web_search import web_search_available

        assert web_search_available() is True

    def test_true_when_only_perplexity(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        from agent.web_search import web_search_available

        assert web_search_available() is True


# ── Provider priority ─────────────────────────────────────────────


class TestProviderPriority:
    def test_exa_used_first_when_available(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "exa-test")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

        with patch("agent.web_search._exa_search", return_value=[]) as mock_exa:
            from agent.web_search import web_search

            web_search("test query")
            mock_exa.assert_called_once()

    def test_tavily_used_when_exa_absent(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

        with patch("agent.web_search._tavily_search", return_value=[]) as mock_tavily:
            from agent.web_search import web_search

            web_search("test query")
            mock_tavily.assert_called_once()

    def test_perplexity_used_when_only_key(self, monkeypatch):
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")

        with patch("agent.web_search._perplexity_search", return_value=[]) as mock_pplx:
            from agent.web_search import web_search

            web_search("test query")
            mock_pplx.assert_called_once()

    def test_falls_back_to_tavily_when_exa_fails(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "exa-test")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

        from agent.web_search import SearchResult

        tavily_result = [SearchResult(title="Tavily result", url="https://t.com", text="content")]

        with patch("agent.web_search._exa_search", side_effect=RuntimeError("exa down")):
            with patch("agent.web_search._tavily_search", return_value=tavily_result):
                from agent.web_search import web_search

                results = web_search("test query")
                assert len(results) == 1
                assert results[0].title == "Tavily result"

    def test_returns_empty_when_all_fail(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "bad")
        monkeypatch.setenv("TAVILY_API_KEY", "bad")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "bad")

        with patch("agent.web_search._exa_search", side_effect=RuntimeError("fail")):
            with patch("agent.web_search._tavily_search", side_effect=RuntimeError("fail")):
                with patch("agent.web_search._perplexity_search", side_effect=RuntimeError("fail")):
                    from agent.web_search import web_search

                    assert web_search("test") == []

    def test_provider_forced_via_arg(self, monkeypatch):
        monkeypatch.setenv("EXA_API_KEY", "exa-test")
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

        with patch("agent.web_search._tavily_search", return_value=[]) as mock_tavily:
            from agent.web_search import web_search

            web_search("test", provider="tavily")
            mock_tavily.assert_called_once()


# ── Tavily provider ───────────────────────────────────────────────


class TestTavilyProvider:
    def _mock_tavily_module(self, search_results: list[dict]):
        """Create a fake tavily module with TavilyClient that returns given results."""
        mock_client_instance = MagicMock()
        mock_client_instance.search.return_value = {"results": search_results}
        mock_client_class = MagicMock(return_value=mock_client_instance)
        mock_module = MagicMock()
        mock_module.TavilyClient = mock_client_class
        return mock_module, mock_client_instance

    def test_maps_fields_correctly(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        tavily_results = [
            {
                "title": "INFY Q4 beats",
                "url": "https://example.com/infy",
                "content": "Infosys Q4 revenue grew 12%.",
                "published_date": "2026-05-01",
                "score": 0.92,
            }
        ]
        mock_module, _ = self._mock_tavily_module(tavily_results)

        with patch.dict("sys.modules", {"tavily": mock_module}):
            from agent.web_search import _tavily_search

            results = _tavily_search("INFY India stock", max_results=2)
            assert len(results) == 1
            assert results[0].title == "INFY Q4 beats"
            assert results[0].url == "https://example.com/infy"
            assert "12%" in results[0].text
            assert results[0].score == 0.92

    def test_raises_without_key(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        import pytest

        mock_module = MagicMock()
        mock_module.TavilyClient = MagicMock()
        with patch.dict("sys.modules", {"tavily": mock_module}):
            from agent.web_search import _tavily_search

            with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
                _tavily_search("test")

    def test_raises_when_sdk_missing(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        import pytest

        with patch.dict("sys.modules", {"tavily": None}):
            from agent.web_search import _tavily_search

            with pytest.raises((RuntimeError, ImportError)):
                _tavily_search("test")

    def test_empty_results_returns_empty_list(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
        mock_module, _ = self._mock_tavily_module([])

        with patch.dict("sys.modules", {"tavily": mock_module}):
            from agent.web_search import _tavily_search

            results = _tavily_search("empty query")
            assert results == []


# ── yfinance fundamentals fallback ────────────────────────────────


class TestYfinanceFundamentalsFallback:
    """FundamentalAnalyst._fundamentals_fallback: yfinance first, then Perplexity."""

    def _make_analyst(self):
        from agent.multi_agent import FundamentalAnalyst

        registry = MagicMock()
        registry.execute.side_effect = RuntimeError("broker unavailable")
        return FundamentalAnalyst(registry)

    def _mock_yf_info(self, pe=22.5, roe=0.28, pb=3.1, d_e=0.15, rev_growth=0.12):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "trailingPE": pe,
            "returnOnEquity": roe,
            "priceToBook": pb,
            "debtToEquity": d_e,
            "revenueGrowth": rev_growth,
        }
        return mock_ticker

    def test_yfinance_used_as_primary_fallback(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info()

        with patch("yfinance.Ticker", return_value=ticker):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")

        assert report.verdict in ("BULLISH", "NEUTRAL", "BEARISH")
        assert report.error == ""
        assert any("PE" in p for p in report.key_points)
        assert any("ROE" in p for p in report.key_points)

    def test_yfinance_uses_ns_suffix(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info()

        with patch("yfinance.Ticker", return_value=ticker) as mock_yf:
            analyst = self._make_analyst()
            analyst.analyze("RELIANCE", "NSE")
            # Check .NS suffix was added
            call_arg = mock_yf.call_args[0][0]
            assert call_arg == "RELIANCE.NS"

    def test_yfinance_does_not_add_ns_twice(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info()

        with patch("yfinance.Ticker", return_value=ticker) as mock_yf:
            analyst = self._make_analyst()
            analyst.analyze("INFY.NS", "NSE")
            call_arg = mock_yf.call_args[0][0]
            assert call_arg == "INFY.NS"  # not INFY.NS.NS

    def test_bullish_verdict_for_high_roe(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info(roe=0.45, pe=18.0)  # very high ROE, fair PE

        with patch("yfinance.Ticker", return_value=ticker):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")

        assert report.verdict == "BULLISH"

    def test_falls_through_to_perplexity_when_yfinance_empty(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        empty_ticker = MagicMock()
        empty_ticker.info = {}  # no PE or ROE

        from agent.perplexity_finance import FinanceSearchResult

        good = FinanceSearchResult(query="test", summary="INFY PE=25 ROE=28%")
        with patch("yfinance.Ticker", return_value=empty_ticker):
            with patch("agent.perplexity_finance.perplexity_finance_available", return_value=True):
                with patch(
                    "agent.perplexity_finance.finance_fundamentals_for_symbol", return_value=good
                ):
                    analyst = self._make_analyst()
                    report = analyst.analyze("INFY", "NSE")

        assert report.verdict == "NEUTRAL"
        assert any("Perplexity Finance" in p for p in report.key_points)

    def test_returns_unknown_when_both_fail(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        with patch("yfinance.Ticker", side_effect=Exception("network error")):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")

        assert report.verdict == "UNKNOWN"
        assert report.error != ""

    def test_confidence_is_50_for_yfinance(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info()

        with patch("yfinance.Ticker", return_value=ticker):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")

        assert report.confidence == 50

    def test_yfinance_source_tagged_in_key_points(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        ticker = self._mock_yf_info()

        with patch("yfinance.Ticker", return_value=ticker):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")

        assert any("yfinance" in p for p in report.key_points)
