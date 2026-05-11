"""
tests/test_perplexity_finance.py
────────────────────────────────
Tests for Perplexity Agent API finance_search integration.

Covers:
  - perplexity_finance_available()
  - finance_news_for_symbol()
  - finance_fundamentals_for_symbol()
  - finance_macro_india()
  - FinanceSearchResult dataclass helpers
  - HTTP error handling
  - FundamentalAnalyst fallback wiring
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── Availability check ────────────────────────────────────────────


class TestAvailability:
    def test_unavailable_when_no_key(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        from agent.perplexity_finance import perplexity_finance_available

        assert perplexity_finance_available() is False

    def test_available_when_key_set(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test-key")
        from agent.perplexity_finance import perplexity_finance_available

        assert perplexity_finance_available() is True


# ── FinanceSearchResult helpers ───────────────────────────────────


class TestFinanceSearchResult:
    def test_ok_when_no_error(self):
        from agent.perplexity_finance import FinanceSearchResult

        r = FinanceSearchResult(query="test", summary="some text")
        assert r.ok is True

    def test_not_ok_when_error(self):
        from agent.perplexity_finance import FinanceSearchResult

        r = FinanceSearchResult(query="test", summary="", error="HTTP 401")
        assert r.ok is False

    def test_as_prompt_text_empty_on_error(self):
        from agent.perplexity_finance import FinanceSearchResult

        r = FinanceSearchResult(query="test", summary="hello", error="fail")
        assert r.as_prompt_text() == ""

    def test_as_prompt_text_contains_summary(self):
        from agent.perplexity_finance import FinanceSearchResult

        r = FinanceSearchResult(
            query="test",
            summary="INFY reported 12% revenue growth in Q4",
        )
        text = r.as_prompt_text()
        assert "INFY" in text
        assert "12%" in text

    def test_as_prompt_text_includes_citations(self):
        from agent.perplexity_finance import FinanceSearchResult

        r = FinanceSearchResult(
            query="test",
            summary="Some summary",
            citations=["https://example.com/1", "https://example.com/2"],
        )
        text = r.as_prompt_text()
        assert "example.com/1" in text

    def test_as_prompt_text_truncates_at_max_chars(self):
        from agent.perplexity_finance import FinanceSearchResult, MAX_SUMMARY_CHARS

        long_summary = "X" * (MAX_SUMMARY_CHARS + 500)
        r = FinanceSearchResult(query="test", summary=long_summary)
        text = r.as_prompt_text()
        # Should not exceed MAX_SUMMARY_CHARS + citation overhead
        assert len(text) <= MAX_SUMMARY_CHARS + 200


# ── _call_finance_search (unit tests with mocked HTTP) ───────────


class TestCallFinanceSearch:
    def _mock_response(self, body: dict, status: int = 200):
        mock = MagicMock()
        mock.status_code = status
        mock.json.return_value = body
        mock.raise_for_status = MagicMock()
        if status >= 400:
            import requests

            mock.raise_for_status.side_effect = requests.HTTPError(response=mock)
            mock.text = "Unauthorized"
        return mock

    def test_parses_responses_api_format(self, monkeypatch):
        """Responses API format: output[*].type=message content[*].type=output_text."""
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        body = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "INFY Q4 revenue up 12%."}],
                }
            ],
            "citations": ["https://example.com/q4"],
        }
        with patch(
            "agent.perplexity_finance.requests.post", return_value=self._mock_response(body)
        ):
            from agent.perplexity_finance import _call_finance_search

            result = _call_finance_search("INFY India stock news")
            assert result.ok
            assert "INFY" in result.summary
            assert any("example.com/q4" in c for c in result.citations)

    def test_falls_back_to_choices_format(self, monkeypatch):
        """Sonar-style choices format as fallback."""
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        body = {
            "output": [],  # empty — triggers fallback
            "choices": [{"message": {"content": "RELIANCE reported strong earnings."}}],
        }
        with patch(
            "agent.perplexity_finance.requests.post", return_value=self._mock_response(body)
        ):
            from agent.perplexity_finance import _call_finance_search

            result = _call_finance_search("RELIANCE stock")
            assert result.ok
            assert "RELIANCE" in result.summary

    def test_returns_error_on_http_failure(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        bad_resp = self._mock_response({}, status=401)
        with patch("agent.perplexity_finance.requests.post", return_value=bad_resp):
            from agent.perplexity_finance import _call_finance_search

            result = _call_finance_search("test")
            assert not result.ok
            assert "401" in result.error

    def test_returns_error_on_no_key(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        from agent.perplexity_finance import _call_finance_search

        result = _call_finance_search("test")
        assert not result.ok
        assert "PERPLEXITY_API_KEY" in result.error

    def test_returns_error_on_network_exception(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch(
            "agent.perplexity_finance.requests.post", side_effect=ConnectionError("timeout")
        ):
            from agent.perplexity_finance import _call_finance_search

            result = _call_finance_search("test")
            assert not result.ok
            assert "timeout" in result.error

    def test_empty_output_and_no_choices_returns_error(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        body = {"output": [], "choices": []}
        with patch(
            "agent.perplexity_finance.requests.post", return_value=self._mock_response(body)
        ):
            from agent.perplexity_finance import _call_finance_search

            result = _call_finance_search("test")
            assert not result.ok


# ── Public convenience functions ──────────────────────────────────


class TestPublicFunctions:
    def _good_result(self):
        from agent.perplexity_finance import FinanceSearchResult

        return FinanceSearchResult(
            query="test",
            summary="Good summary",
            citations=["https://example.com"],
        )

    def test_finance_news_for_symbol_builds_india_query(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch("agent.perplexity_finance._call_finance_search") as mock_call:
            mock_call.return_value = self._good_result()
            from agent.perplexity_finance import finance_news_for_symbol

            finance_news_for_symbol("INFY")
            query_used = mock_call.call_args[0][0]
            assert "INFY" in query_used
            assert "India" in query_used

    def test_finance_news_includes_context_hint(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch("agent.perplexity_finance._call_finance_search") as mock_call:
            mock_call.return_value = self._good_result()
            from agent.perplexity_finance import finance_news_for_symbol

            finance_news_for_symbol("TCS", context_hint="AI revenue deals")
            query_used = mock_call.call_args[0][0]
            assert "AI revenue deals" in query_used

    def test_finance_fundamentals_query_contains_key_terms(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch("agent.perplexity_finance._call_finance_search") as mock_call:
            mock_call.return_value = self._good_result()
            from agent.perplexity_finance import finance_fundamentals_for_symbol

            finance_fundamentals_for_symbol("HDFC")
            query_used = mock_call.call_args[0][0]
            assert "HDFC" in query_used
            assert "PE" in query_used or "ROE" in query_used

    def test_finance_macro_india_builds_nifty_query(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch("agent.perplexity_finance._call_finance_search") as mock_call:
            mock_call.return_value = self._good_result()
            from agent.perplexity_finance import finance_macro_india

            finance_macro_india()
            query_used = mock_call.call_args[0][0]
            assert "NIFTY" in query_used or "India" in query_used

    def test_finance_macro_with_context(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        with patch("agent.perplexity_finance._call_finance_search") as mock_call:
            mock_call.return_value = self._good_result()
            from agent.perplexity_finance import finance_macro_india

            finance_macro_india(context="RBI rate cut")
            query_used = mock_call.call_args[0][0]
            assert "RBI rate cut" in query_used


# ── FundamentalAnalyst fallback wiring ───────────────────────────


class TestFundamentalFallback:
    """Verify FundamentalAnalyst falls back to Perplexity when broker tool fails."""

    def _make_analyst(self):
        from agent.multi_agent import FundamentalAnalyst

        registry = MagicMock()
        registry.execute.side_effect = RuntimeError("broker unavailable")
        return FundamentalAnalyst(registry)

    def test_fallback_returns_neutral_verdict_on_success(self, monkeypatch):
        """Perplexity Finance path is used when yfinance returns no structured data."""
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        from agent.perplexity_finance import FinanceSearchResult

        good = FinanceSearchResult(
            query="test",
            summary="INFY PE=25 ROE=28% revenue growth 12%",
        )
        # Make yfinance return empty info so it falls through to Perplexity
        empty_ticker = MagicMock()
        empty_ticker.info = {}

        with patch("yfinance.Ticker", return_value=empty_ticker):
            with patch("agent.perplexity_finance.perplexity_finance_available", return_value=True):
                with patch(
                    "agent.perplexity_finance.finance_fundamentals_for_symbol", return_value=good
                ):
                    analyst = self._make_analyst()
                    report = analyst.analyze("INFY", "NSE")

        assert report.verdict == "NEUTRAL"
        assert report.confidence == 40
        assert any("Perplexity" in p for p in report.key_points)

    def test_fallback_returns_unknown_when_both_unavailable(self, monkeypatch):
        """UNKNOWN only when both yfinance (empty) and Perplexity (no key) fail."""
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        empty_ticker = MagicMock()
        empty_ticker.info = {}
        with patch("yfinance.Ticker", return_value=empty_ticker):
            analyst = self._make_analyst()
            report = analyst.analyze("INFY", "NSE")
        assert report.verdict == "UNKNOWN"
        assert report.error != ""

    def test_fallback_returns_unknown_on_perplexity_error(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        from agent.perplexity_finance import FinanceSearchResult

        bad = FinanceSearchResult(query="test", summary="", error="HTTP 500")
        empty_ticker = MagicMock()
        empty_ticker.info = {}
        with patch("yfinance.Ticker", return_value=empty_ticker):
            with patch("agent.perplexity_finance.perplexity_finance_available", return_value=True):
                with patch(
                    "agent.perplexity_finance.finance_fundamentals_for_symbol", return_value=bad
                ):
                    analyst = self._make_analyst()
                    report = analyst.analyze("INFY", "NSE")

        assert report.verdict == "UNKNOWN"
        assert report.error != ""


# ── NewsMacroAnalyst wiring ───────────────────────────────────────


class TestNewsMacroFinanceWiring:
    """finance_search runs before generic web search in NewsMacroAnalyst."""

    def _make_analyst(self):
        from agent.multi_agent import NewsMacroAnalyst

        registry = MagicMock()
        registry.execute.return_value = []  # no tools data
        return NewsMacroAnalyst(registry)

    def test_finance_search_result_injected_into_data(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        from agent.perplexity_finance import FinanceSearchResult

        good = FinanceSearchResult(
            query="INFY",
            summary="Infosys announced major AI deal with European bank.",
            citations=["https://example.com/infy"],
        )
        with patch("agent.perplexity_finance.perplexity_finance_available", return_value=True):
            with patch("agent.perplexity_finance.finance_news_for_symbol", return_value=good):
                analyst = self._make_analyst()
                report = analyst.analyze("INFY", "NSE")

        # The report key_points should mention Perplexity Finance
        assert any("Perplexity Finance" in p for p in report.key_points)

    def test_finance_search_skipped_when_unavailable(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        monkeypatch.delenv("EXA_API_KEY", raising=False)

        analyst = self._make_analyst()
        # Should not raise; just skip finance search
        report = analyst.analyze("RELIANCE", "NSE")
        assert report is not None
        assert not any("Perplexity Finance" in p for p in report.key_points)
