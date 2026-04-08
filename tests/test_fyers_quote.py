"""
tests/test_fyers_quote.py
─────────────────────────
Unit tests for the Fyers quote after-close change fallback.

After NSE close Fyers rolls prev_close_price to today's official close, making
ch ≈ 0.  The broker should detect this and fall back to open-based change.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fyers(token_valid: bool = True):
    """Return a FyersAPI instance with __init__ bypassed."""
    from brokers.fyers import FyersAPI

    obj = FyersAPI.__new__(FyersAPI)
    obj.app_id = "TESTAPP"
    obj._token = "testtoken" if token_valid else None
    obj._fyers = MagicMock()
    return obj


def _fyers_tick_response(
    symbol: str,
    lp: float,
    open_price: float,
    high_price: float,
    low_price: float,
    prev_close_price: float,
    ch: float,
    chp: float,
    volume: int = 1_000_000,
) -> dict:
    """Build a fake Fyers quotes API response for one symbol."""
    return {
        "code": 200,
        "message": "",
        "s": "ok",
        "d": [
            {
                "n": symbol,
                "s": "ok",
                "v": {
                    "lp": lp,
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "prev_close_price": prev_close_price,
                    "volume": volume,
                    "ch": ch,
                    "chp": chp,
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFyersQuoteChange:
    """Tests for the after-close change fallback in FyersAPI.get_quote."""

    def _get_quote(self, fyers_obj, symbol, raw_response):
        """Call get_quote with a mocked Fyers SDK response."""
        fyers_obj._fyers.quotes.return_value = raw_response
        return fyers_obj.get_quote([symbol])

    def test_normal_session_change_preserved(self):
        """During market hours ch/chp are meaningful — use them as-is."""
        f = _make_fyers()
        # lp=1304.6, open=1295, high=1308.3, low=1291 → range=17.3
        # ch=-1.40 → abs(-1.40) / 17.3 = 0.081 > 0.05 → NOT a rollover
        resp = _fyers_tick_response(
            "NSE:RELIANCE-EQ",
            lp=1304.6,
            open_price=1295.0,
            high_price=1308.3,
            low_price=1291.0,
            prev_close_price=1306.0,
            ch=-1.40,
            chp=-0.11,
        )
        quotes = self._get_quote(f, "NSE:RELIANCE-EQ", resp)
        q = quotes["NSE:RELIANCE-EQ"]
        assert q.change == -1.40
        assert q.change_pct == -0.11

    def test_after_close_rollover_uses_open_fallback(self):
        """After close prev_close rolls to today's close → ch ≈ 0 → fallback to open-based."""
        f = _make_fyers()
        # After close: prev_close_price = today's close ≈ lp
        # ch = -0.10 (lp - new_prev_close), very small vs range of 17.3
        resp = _fyers_tick_response(
            "NSE:RELIANCE-EQ",
            lp=1304.6,
            open_price=1295.0,
            high_price=1308.3,
            low_price=1291.0,
            prev_close_price=1304.7,
            ch=-0.10,
            chp=-0.01,
        )
        quotes = self._get_quote(f, "NSE:RELIANCE-EQ", resp)
        q = quotes["NSE:RELIANCE-EQ"]
        # Fallback: change = lp - open = 1304.6 - 1295.0 = 9.6
        assert q.change == pytest.approx(9.6, abs=0.01)
        assert q.change_pct == pytest.approx((9.6 / 1295.0) * 100, abs=0.01)

    def test_genuinely_flat_day_not_triggered(self):
        """If the stock barely moved (tiny range), don't apply rollover fix."""
        f = _make_fyers()
        # Flat day: range = 0.4 (<0.5 threshold) → skip fallback
        resp = _fyers_tick_response(
            "NSE:SOMESTOCK-EQ",
            lp=100.0,
            open_price=100.1,
            high_price=100.3,
            low_price=99.9,
            prev_close_price=100.1,
            ch=-0.10,
            chp=-0.10,
        )
        quotes = self._get_quote(f, "NSE:SOMESTOCK-EQ", resp)
        q = quotes["NSE:SOMESTOCK-EQ"]
        # Range < 0.5 → keep original ch/chp
        assert q.change == -0.10
        assert q.change_pct == -0.10

    def test_zero_open_price_no_division_error(self):
        """If open_price is 0 (bad data), fallback is skipped — original values kept."""
        f = _make_fyers()
        resp = _fyers_tick_response(
            "NSE:BAD-EQ",
            lp=100.0,
            open_price=0.0,
            high_price=105.0,
            low_price=95.0,
            prev_close_price=100.05,
            ch=-0.05,
            chp=-0.05,
        )
        quotes = self._get_quote(f, "NSE:BAD-EQ", resp)
        q = quotes["NSE:BAD-EQ"]
        # open=0 → open_price > 0 guard skips fallback → original ch/chp kept, no ZeroDivisionError
        assert q.change == -0.05
        assert q.change_pct == -0.05

    def test_other_fields_unaffected_by_fallback(self):
        """Fallback only touches change/change_pct — all other fields stay correct."""
        f = _make_fyers()
        resp = _fyers_tick_response(
            "NSE:RELIANCE-EQ",
            lp=1304.6,
            open_price=1295.0,
            high_price=1308.3,
            low_price=1291.0,
            prev_close_price=1304.7,
            ch=-0.10,
            chp=-0.01,
            volume=28_382_724,
        )
        quotes = self._get_quote(f, "NSE:RELIANCE-EQ", resp)
        q = quotes["NSE:RELIANCE-EQ"]
        assert q.last_price == 1304.6
        assert q.open == 1295.0
        assert q.high == 1308.3
        assert q.low == 1291.0
        assert q.close == 1304.7
        assert q.volume == 28_382_724
        assert q.symbol == "RELIANCE-EQ"
