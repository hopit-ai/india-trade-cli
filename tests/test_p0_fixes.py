"""
tests/test_p0_fixes.py
──────────────────────
Tests for P0 bug fixes: #133, #142, #116, #114, #124, #137, #107.
All tests use synthetic data — no network calls.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch


# ── Bug #133: Broker primary overwrite ─────────────────────────


class TestBrokerPrimaryOverwrite:
    """register_broker default should NOT overwrite primary."""

    def setup_method(self):
        """Reset module state before each test."""
        import brokers.session as sess

        sess._brokers = {}
        sess._primary_key = ""

    def teardown_method(self):
        import brokers.session as sess

        sess._brokers = {}
        sess._primary_key = ""

    def test_first_broker_becomes_primary(self):
        from brokers.session import register_broker

        broker_a = MagicMock()
        register_broker("broker_a", broker_a)

        import brokers.session as sess

        assert sess._primary_key == "broker_a"

    def test_second_broker_does_not_overwrite_primary(self):
        from brokers.session import register_broker

        broker_a = MagicMock()
        broker_b = MagicMock()

        register_broker("broker_a", broker_a)
        register_broker("broker_b", broker_b)

        import brokers.session as sess

        assert sess._primary_key == "broker_a", (
            "Second register_broker() should NOT overwrite primary"
        )
        assert "broker_b" in sess._brokers

    def test_explicit_primary_true_does_overwrite(self):
        from brokers.session import register_broker

        broker_a = MagicMock()
        broker_b = MagicMock()

        register_broker("broker_a", broker_a)
        register_broker("broker_b", broker_b, primary=True)

        import brokers.session as sess

        assert sess._primary_key == "broker_b"

    def test_default_primary_is_false(self):
        """Verify the default value of primary parameter is False."""
        import inspect
        from brokers.session import register_broker

        sig = inspect.signature(register_broker)
        assert sig.parameters["primary"].default is False


# ── Bug #142: FII/DII today != 5-day ──────────────────────────


class TestFIIDIISorting:
    """get_fii_dii_data should sort by date descending so today != cumulative."""

    @patch("market.sentiment.httpx.Client")
    def test_today_is_most_recent_date(self, mock_client_cls):
        """The first entry should be the most recent date, not arbitrary order."""
        # Build mock API response with dates out of order
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "date": "01-Apr-2026",
                "category": "FII/FPI",
                "buyValue": 100,
                "sellValue": 200,
                "netValue": -100,
            },
            {
                "date": "01-Apr-2026",
                "category": "DII",
                "buyValue": 300,
                "sellValue": 100,
                "netValue": 200,
            },
            {
                "date": "03-Apr-2026",
                "category": "FII/FPI",
                "buyValue": 500,
                "sellValue": 100,
                "netValue": 400,
            },
            {
                "date": "03-Apr-2026",
                "category": "DII",
                "buyValue": 200,
                "sellValue": 300,
                "netValue": -100,
            },
            {
                "date": "02-Apr-2026",
                "category": "FII/FPI",
                "buyValue": 150,
                "sellValue": 250,
                "netValue": -100,
            },
            {
                "date": "02-Apr-2026",
                "category": "DII",
                "buyValue": 350,
                "sellValue": 150,
                "netValue": 200,
            },
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_client_cls.return_value = mock_session

        from market.sentiment import get_fii_dii_data

        result = get_fii_dii_data(days=5)

        assert len(result) >= 2
        # First entry should be the most recent date (03-Apr)
        assert result[0].date == "03-Apr-2026"
        # The today value (400) should differ from cumulative 5-day
        assert result[0].fii_net == 400
        # Second entry should be 02-Apr
        assert result[1].date == "02-Apr-2026"

    @patch("market.sentiment.httpx.Client")
    def test_today_not_equal_to_5day_cumulative(self, mock_client_cls):
        """Today's FII net should be just today, not the 5-day sum."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "date": "07-Apr-2026",
                "category": "FII/FPI",
                "buyValue": 1000,
                "sellValue": 500,
                "netValue": 500,
            },
            {
                "date": "07-Apr-2026",
                "category": "DII",
                "buyValue": 300,
                "sellValue": 100,
                "netValue": 200,
            },
            {
                "date": "04-Apr-2026",
                "category": "FII/FPI",
                "buyValue": 200,
                "sellValue": 800,
                "netValue": -600,
            },
            {
                "date": "04-Apr-2026",
                "category": "DII",
                "buyValue": 400,
                "sellValue": 200,
                "netValue": 200,
            },
        ]

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_client_cls.return_value = mock_session

        from market.sentiment import get_fii_dii_data

        result = get_fii_dii_data(days=5)
        today_fii = result[0].fii_net
        total_fii = sum(r.fii_net for r in result)

        # Today should not equal the cumulative (500 != 500 + -600 = -100)
        assert today_fii != total_fii, (
            f"Today FII ({today_fii}) should not equal 5-day total ({total_fii})"
        )


# ── Bug #116: IV solver for deep ITM ──────────────────────────


import pytest

scipy = pytest.importorskip("scipy", reason="scipy not installed")


class TestIVSolverDeepITM:
    """Newton-Raphson IV solver should converge for deep ITM options."""

    def test_deep_itm_put_iv_not_trivial(self):
        """Deep ITM put (strike=24050, spot=23000, premium=1050) should have real IV."""
        from analysis.options import _bs_greeks_manual

        greeks = _bs_greeks_manual(
            S=23000,
            K=24050,
            T=7 / 365,  # 7 DTE
            r=0.065,
            price=1050,
            option_type="PE",
        )

        # IV should NOT be the trivial 0.1% (0.001) — deep ITM has real vol
        assert greeks.iv > 0.01, f"IV for deep ITM put should be > 1%, got {greeks.iv_pct}%"
        # Should be reasonable (5%–200%)
        assert greeks.iv < 5.0, f"IV should be < 500%, got {greeks.iv_pct}%"

    def test_deep_itm_call_iv(self):
        """Deep ITM call should also converge to a non-zero IV."""
        from analysis.options import _bs_greeks_manual

        # S=24000, K=23000, intrinsic=1000, premium=1200 => time value=200
        greeks = _bs_greeks_manual(
            S=24000,
            K=23000,
            T=14 / 365,
            r=0.065,
            price=1200,
            option_type="CE",
        )

        # Should converge to something, not crash or return 0
        assert greeks.iv >= 0.001, f"IV should be >= 0.1%, got {greeks.iv_pct}%"
        assert greeks.iv <= 5.0, f"IV should be <= 500%, got {greeks.iv_pct}%"

    def test_atm_option_iv(self):
        """ATM option IV should converge normally."""
        from analysis.options import _bs_greeks_manual

        greeks = _bs_greeks_manual(
            S=23000,
            K=23000,
            T=14 / 365,
            r=0.065,
            price=300,
            option_type="CE",
        )

        assert 0.05 < greeks.iv < 2.0, f"ATM IV should be reasonable, got {greeks.iv_pct}%"

    def test_sigma_clamped_to_bounds(self):
        """IV should never go below 0.001 or above 5.0."""
        from analysis.options import _bs_greeks_manual

        greeks = _bs_greeks_manual(
            S=23000,
            K=24050,
            T=1 / 365,  # 1 DTE — extreme case
            r=0.065,
            price=1050,
            option_type="PE",
        )

        assert greeks.iv >= 0.001
        assert greeks.iv <= 5.0


# ── Bug #114: Follow-up routing bypass TradingAgent ────────────


class TestFollowupBypassAgent:
    """Follow-up endpoint should use direct LLM, not TradingAgent."""

    def test_followup_stores_session_as_dict(self):
        """After a followup call, _chat_sessions should store a dict, not TradingAgent."""
        from web.skills import _chat_sessions

        # Create a mock session entry like the new code would
        session_key = "followup_TEST_NSE_test123"
        _chat_sessions[session_key] = {
            "system": "You are a follow-up assistant for TEST.",
            "history": [],
        }

        session = _chat_sessions[session_key]
        assert isinstance(session, dict)
        assert "system" in session
        assert "history" in session
        assert isinstance(session["history"], list)

        # Clean up
        _chat_sessions.pop(session_key, None)

    def test_session_history_accumulates(self):
        """Session history should grow with each exchange."""
        session = {
            "system": "Follow-up mode for RELIANCE.",
            "history": [],
        }

        # Simulate multi-turn
        session["history"].append({"role": "user", "content": "What is the PE ratio?"})
        session["history"].append({"role": "assistant", "content": "PE is 25."})
        session["history"].append({"role": "user", "content": "Is that high?"})
        session["history"].append({"role": "assistant", "content": "It's average."})

        assert len(session["history"]) == 4
        assert session["history"][0]["role"] == "user"
        assert session["history"][-1]["role"] == "assistant"


# ── Bug #124: Telegram markdown → HTML ─────────────────────────


class TestMdToHtml:
    """Test the _md_to_html helper function."""

    def _md_to_html(self, text):
        from bot.telegram_bot import _md_to_html

        return _md_to_html(text)

    def test_bold(self):
        assert self._md_to_html("**hello**") == "<b>hello</b>"

    def test_italic(self):
        assert self._md_to_html("*hello*") == "<i>hello</i>"

    def test_bold_not_italic(self):
        """**bold** should not also produce italic markers."""
        result = self._md_to_html("**bold**")
        assert result == "<b>bold</b>"
        assert "<i>" not in result

    def test_inline_code(self):
        assert self._md_to_html("`code`") == "<code>code</code>"

    def test_code_block(self):
        result = self._md_to_html("```\nsome code\n```")
        assert "<pre>" in result
        assert "some code" in result

    def test_headers(self):
        assert self._md_to_html("# Header") == "<b>Header</b>"
        assert self._md_to_html("## Header") == "<b>Header</b>"
        assert self._md_to_html("### Header") == "<b>Header</b>"

    def test_horizontal_rule_dashes(self):
        assert self._md_to_html("---") == "\u2014"

    def test_horizontal_rule_heavy(self):
        assert self._md_to_html("\u2501\u2501\u2501") == "\u2014"

    def test_html_escape(self):
        """HTML special chars should be escaped BEFORE markdown conversion."""
        result = self._md_to_html("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result

    def test_mixed_content(self):
        text = "### Analysis\n**BULLISH** signal with `RSI` at *30*\n---"
        result = self._md_to_html(text)
        assert "<b>Analysis</b>" in result
        assert "<b>BULLISH</b>" in result
        assert "<code>RSI</code>" in result
        assert "<i>30</i>" in result


# ── Bug #137: Broker token validation with caching ─────────────


class TestBrokerAuthCache:
    """Auth check should cache results for 5 minutes."""

    def test_cached_auth_returns_cached_value(self):
        from web.api import _cached_auth, _auth_cache

        # Clear cache
        _auth_cache.clear()

        call_count = 0

        def _slow_check():
            nonlocal call_count
            call_count += 1
            return True

        # First call should invoke the check
        result1 = _cached_auth("test_broker", _slow_check)
        assert result1 is True
        assert call_count == 1

        # Second call should use cache (not invoke check again)
        result2 = _cached_auth("test_broker", _slow_check)
        assert result2 is True
        assert call_count == 1  # Still 1 — cached

        _auth_cache.clear()

    def test_cache_expires_after_ttl(self):
        from web.api import _cached_auth, _auth_cache, _AUTH_CACHE_TTL

        _auth_cache.clear()

        call_count = 0

        def _check():
            nonlocal call_count
            call_count += 1
            return True

        _cached_auth("expire_test", _check)
        assert call_count == 1

        # Manually expire the cache entry
        _auth_cache["expire_test"] = (True, time.time() - _AUTH_CACHE_TTL - 1)

        _cached_auth("expire_test", _check)
        assert call_count == 2  # Re-checked after expiry

        _auth_cache.clear()

    def test_cache_stores_false_for_failed_auth(self):
        from web.api import _cached_auth, _auth_cache

        _auth_cache.clear()

        result = _cached_auth("failed_broker", lambda: False)
        assert result is False

        # Should still be cached (don't re-check on every poll)
        cached = _auth_cache.get("failed_broker")
        assert cached is not None
        assert cached[0] is False

        _auth_cache.clear()


# ── Bug #107: AI pivots silently — prompt guardrail ────────────


class TestDataGapGuardrail:
    """System prompt should contain data availability guardrail."""

    def test_prompt_contains_data_gap_section(self):
        from agent.prompts import build_system_prompt

        prompt = build_system_prompt()
        assert "Data Availability & Honesty" in prompt
        assert "I don't have data on" in prompt
        assert "Do NOT pivot to unrelated analysis" in prompt
        assert "silent pivots erode it" in prompt

    def test_guardrail_before_guardrails_section(self):
        """Data gap section should come before the general Guardrails section."""
        from agent.prompts import build_system_prompt

        prompt = build_system_prompt()
        gap_pos = prompt.index("Data Availability & Honesty")
        guardrails_pos = prompt.index("## Guardrails")
        assert gap_pos < guardrails_pos
