"""
tests/test_broker_quote_change.py
──────────────────────────────────
Tests that change / change_pct and day_change / day_change_pct are computed
correctly in all broker implementations.

Bugs fixed:
  - AngelOne get_quote: change/change_pct were missing (defaulted to 0.0)
  - AngelOne holdings: day_change sign was inverted (close - ltp instead of ltp - close)
  - Upstox get_quote: used LTP-only endpoint (OHLC all equal ltp, change always 0)
  - Upstox holdings/positions: day_change hardcoded to 0.0
"""

from __future__ import annotations

from unittest.mock import MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────


def _bypass_init(cls):
    """Return an instance of cls with __init__ bypassed."""
    obj = cls.__new__(cls)
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# AngelOne
# ─────────────────────────────────────────────────────────────────────────────


class TestAngelOneQuoteChange:
    """AngelOne get_quote must compute change/change_pct from ltp - prev_close."""

    def _make_broker(self, ltp_data: dict):
        from brokers.angelone import AngelOneAPI

        b = _bypass_init(AngelOneAPI)
        b._obj = MagicMock()
        b._obj.ltpData.return_value = {"data": ltp_data}
        return b

    def test_change_computed_from_ltp_minus_close(self):
        b = self._make_broker(
            {
                "ltp": 1304.6,
                "close": 1306.0,
                "open": 1295.0,
                "high": 1308.3,
                "low": 1291.0,
                "tradedVolume": 1000,
            }
        )
        q = b.get_quote(["NSE:RELIANCE"])["NSE:RELIANCE"]
        assert q.change == round(1304.6 - 1306.0, 2)  # -1.4
        assert q.change_pct == round(-1.4 / 1306.0 * 100, 2)  # -0.11

    def test_change_positive_when_stock_up(self):
        b = self._make_broker(
            {
                "ltp": 1310.0,
                "close": 1306.0,
                "open": 1295.0,
                "high": 1315.0,
                "low": 1290.0,
                "tradedVolume": 500,
            }
        )
        q = b.get_quote(["NSE:RELIANCE"])["NSE:RELIANCE"]
        assert q.change == pytest.approx(4.0, abs=0.01)
        assert q.change_pct > 0

    def test_change_pct_zero_when_prev_close_zero(self):
        b = self._make_broker({"ltp": 100.0, "close": 0.0, "tradedVolume": 0})
        q = b.get_quote(["NSE:BADDATA"])["NSE:BADDATA"]
        assert q.change_pct == 0.0

    def test_other_fields_correct(self):
        b = self._make_broker(
            {
                "ltp": 1304.6,
                "close": 1306.0,
                "open": 1295.0,
                "high": 1308.3,
                "low": 1291.0,
                "tradedVolume": 28_000_000,
            }
        )
        q = b.get_quote(["NSE:RELIANCE"])["NSE:RELIANCE"]
        assert q.last_price == 1304.6
        assert q.open == 1295.0
        assert q.high == 1308.3
        assert q.low == 1291.0
        assert q.volume == 28_000_000


class TestAngelOneHoldingsDayChange:
    """AngelOne holdings day_change must be ltp - close (not close - ltp)."""

    def _make_broker(self, holding_data: list):
        from brokers.angelone import AngelOneAPI

        b = _bypass_init(AngelOneAPI)
        b._obj = MagicMock()
        b._obj.holding.return_value = {"data": holding_data}
        return b

    def test_day_change_positive_when_stock_up(self):
        """ltp > close → day_change must be positive."""
        b = self._make_broker(
            [
                {
                    "tradingsymbol": "RELIANCE",
                    "exchange": "NSE",
                    "quantity": 10,
                    "averageprice": 1200.0,
                    "ltp": 1310.0,
                    "close": 1306.0,
                }
            ]
        )
        h = b.get_holdings()[0]
        assert h.day_change == pytest.approx(4.0, abs=0.01)
        assert h.day_change_pct > 0

    def test_day_change_negative_when_stock_down(self):
        """ltp < close → day_change must be negative."""
        b = self._make_broker(
            [
                {
                    "tradingsymbol": "RELIANCE",
                    "exchange": "NSE",
                    "quantity": 10,
                    "averageprice": 1200.0,
                    "ltp": 1304.6,
                    "close": 1306.0,
                }
            ]
        )
        h = b.get_holdings()[0]
        assert h.day_change == pytest.approx(-1.4, abs=0.01)
        assert h.day_change_pct < 0

    def test_day_change_pct_computed(self):
        b = self._make_broker(
            [
                {
                    "tradingsymbol": "INFY",
                    "exchange": "NSE",
                    "quantity": 5,
                    "averageprice": 1500.0,
                    "ltp": 1530.0,
                    "close": 1500.0,
                }
            ]
        )
        h = b.get_holdings()[0]
        assert h.day_change_pct == pytest.approx(30.0 / 1500.0 * 100, abs=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# Upstox
# ─────────────────────────────────────────────────────────────────────────────


class TestUpstoxQuoteChange:
    """Upstox get_quote must return full OHLCV with correct change/change_pct."""

    def _make_broker(self, quote_data: dict):
        from brokers.upstox import UpstoxAPI

        b = _bypass_init(UpstoxAPI)
        b._token = "testtoken"
        # Patch _get to return the provided data
        b._get = MagicMock(return_value={"data": quote_data})
        return b

    def test_full_ohlcv_returned(self):
        b = self._make_broker(
            {
                "NSE_EQ|RELIANCE": {
                    "last_price": 1304.6,
                    "ohlc": {"open": 1295.0, "high": 1308.3, "low": 1291.0, "close": 1306.0},
                    "volume": 28_000_000,
                    "oi": 0,
                }
            }
        )
        q = b.get_quote(["RELIANCE"])["RELIANCE"]
        assert q.open == 1295.0
        assert q.high == 1308.3
        assert q.low == 1291.0
        assert q.volume == 28_000_000

    def test_change_computed_correctly(self):
        b = self._make_broker(
            {
                "NSE_EQ|RELIANCE": {
                    "last_price": 1304.6,
                    "ohlc": {"open": 1295.0, "high": 1308.3, "low": 1291.0, "close": 1306.0},
                    "volume": 100,
                }
            }
        )
        q = b.get_quote(["RELIANCE"])["RELIANCE"]
        assert q.change == pytest.approx(1304.6 - 1306.0, abs=0.01)
        assert q.change_pct == pytest.approx((1304.6 - 1306.0) / 1306.0 * 100, abs=0.01)

    def test_fallback_on_exception_returns_zeros_not_ltp(self):
        from brokers.upstox import UpstoxAPI

        b = _bypass_init(UpstoxAPI)
        b._token = "testtoken"
        b._get = MagicMock(side_effect=Exception("network error"))
        q = b.get_quote(["RELIANCE"])["RELIANCE"]
        assert q.last_price == 0
        assert q.change == 0.0
        assert q.change_pct == 0.0


class TestUpstoxHoldingsDayChange:
    """Upstox holdings/positions day_change must come from API, not be hardcoded 0."""

    def _make_broker(self, holdings_data: list):
        from brokers.upstox import UpstoxAPI

        b = _bypass_init(UpstoxAPI)
        b._token = "testtoken"
        b._get = MagicMock(return_value={"data": holdings_data})
        return b

    def test_day_change_from_api_field(self):
        b = self._make_broker(
            [
                {
                    "tradingsymbol": "RELIANCE",
                    "isin": "INE002A01018",
                    "exchange": "NSE",
                    "quantity": 10,
                    "average_price": 1200.0,
                    "last_price": 1304.6,
                    "day_change": -1.4,
                    "day_change_percentage": -0.11,
                }
            ]
        )
        h = b.get_holdings()[0]
        assert h.day_change == -1.4
        assert h.day_change_pct == -0.11

    def test_day_change_defaults_to_zero_gracefully(self):
        """If API doesn't return day_change, defaults to 0 without crashing."""
        b = self._make_broker(
            [
                {
                    "tradingsymbol": "INFY",
                    "isin": "INE009A01021",
                    "exchange": "NSE",
                    "quantity": 5,
                    "average_price": 1500.0,
                    "last_price": 1530.0,
                    # no day_change / day_change_percentage fields
                }
            ]
        )
        h = b.get_holdings()[0]
        assert h.day_change == 0.0
        assert h.day_change_pct == 0.0


import pytest
