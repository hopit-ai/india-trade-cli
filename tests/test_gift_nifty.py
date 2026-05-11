"""
tests/test_gift_nifty.py
─────────────────────────
Tests for GIFT NIFTY pre-market indicator (#106).

Covers:
  - GiftNiftySnapshot dataclass construction and properties
  - as_text() display formatting
  - _from_yfinance() happy path + fallback + import-error
  - get_gift_nifty() wrapper
  - MarketSnapshot integration (gift_nifty field propagated from get_market_snapshot)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── GiftNiftySnapshot unit tests ─────────────────────────────────────────────


class TestGiftNiftySnapshot:
    def test_basic_construction(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24500.0, change=120.0, change_pct=0.493)
        assert g.ltp == 24500.0
        assert g.change == 120.0
        assert g.change_pct == 0.493

    def test_defaults(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24000.0, change=-50.0, change_pct=-0.208)
        assert g.high == 0.0
        assert g.low == 0.0
        assert g.premium_pts is None
        assert g.premium_pct is None
        assert g.source == ""

    def test_implied_gap_pct_property(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24600.0, change=200.0, change_pct=0.82, premium_pct=0.75)
        assert g.implied_gap_pct == 0.75

    def test_implied_gap_pct_none_when_no_premium(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24000.0, change=0.0, change_pct=0.0)
        assert g.implied_gap_pct is None

    def test_as_text_no_gap(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24500.0, change=100.0, change_pct=0.41)
        text = g.as_text()
        assert "GIFT NIFTY" in text
        assert "24,500" in text or "24500" in text

    def test_as_text_with_gap_up(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(
            ltp=24600.0,
            change=200.0,
            change_pct=0.82,
            premium_pts=150.0,
            premium_pct=0.615,
        )
        text = g.as_text()
        assert "gap up" in text
        assert "0.62" in text or "0.615" in text or "0.61" in text

    def test_as_text_with_gap_down(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(
            ltp=24200.0,
            change=-150.0,
            change_pct=-0.615,
            premium_pts=-150.0,
            premium_pct=-0.615,
        )
        text = g.as_text()
        assert "gap down" in text

    def test_positive_change_direction(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24500.0, change=100.0, change_pct=0.41)
        text = g.as_text()
        # No leading negative sign for positive change
        assert "+" in text or "100" in text

    def test_negative_change_direction(self):
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24200.0, change=-100.0, change_pct=-0.41)
        text = g.as_text()
        assert "-" in text or "−" in text or "100" in text


# ── _from_yfinance unit tests ─────────────────────────────────────────────────


class TestFromYFinance:
    def _make_fast_info(self, last_price, prev_close, day_high=None, day_low=None):
        """Helper: create a mock fast_info object."""
        fi = MagicMock()
        fi.last_price = last_price
        fi.previous_close = prev_close
        fi.day_high = day_high
        fi.day_low = day_low
        return fi

    def test_returns_snapshot_on_valid_data(self):
        from market.gift_nifty import _from_yfinance

        mock_fi = self._make_fast_info(24500.0, 24380.0, 24550.0, 24300.0)
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is not None
        assert result.ltp == pytest.approx(24500.0, abs=1)
        assert result.change == pytest.approx(120.0, abs=1)
        assert result.source == "yfinance"

    def test_change_computed_correctly(self):
        from market.gift_nifty import _from_yfinance

        mock_fi = self._make_fast_info(24500.0, 24000.0)
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is not None
        assert result.change == pytest.approx(500.0, abs=1)
        assert result.change_pct == pytest.approx(500 / 24000 * 100, abs=0.01)

    def test_premium_computed_when_nifty_spot_given(self):
        from market.gift_nifty import _from_yfinance

        mock_fi = self._make_fast_info(24600.0, 24400.0)
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = _from_yfinance(nifty_spot=24400.0)

        assert result is not None
        assert result.premium_pts == pytest.approx(200.0, abs=1)
        assert result.premium_pct == pytest.approx(200 / 24400 * 100, abs=0.01)

    def test_premium_none_when_no_nifty_spot(self):
        from market.gift_nifty import _from_yfinance

        mock_fi = self._make_fast_info(24500.0, 24380.0)
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is not None
        assert result.premium_pts is None
        assert result.premium_pct is None

    def test_skips_ticker_with_zero_price(self):
        from market.gift_nifty import _from_yfinance

        # First ticker returns 0, second returns valid data
        fi_zero = self._make_fast_info(0.0, 24380.0)
        fi_valid = self._make_fast_info(24500.0, 24380.0)

        tickers = [MagicMock(fast_info=fi_zero), MagicMock(fast_info=fi_valid)]
        call_count = {"n": 0}

        def make_ticker(sym):
            t = tickers[call_count["n"]]
            call_count["n"] += 1
            return t

        with patch("yfinance.Ticker", side_effect=make_ticker):
            result = _from_yfinance(nifty_spot=None)

        # Should eventually return valid data from the second ticker
        assert result is not None
        assert result.ltp == pytest.approx(24500.0, abs=1)

    def test_returns_none_when_all_tickers_fail(self):
        from market.gift_nifty import _from_yfinance

        def raising_ticker(sym):
            raise RuntimeError("network error")

        with patch("yfinance.Ticker", side_effect=raising_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is None

    def test_returns_none_on_import_error(self):
        from market.gift_nifty import _from_yfinance

        with patch.dict("sys.modules", {"yfinance": None}):
            result = _from_yfinance(nifty_spot=None)

        assert result is None

    def test_skips_ticker_with_none_price(self):
        from market.gift_nifty import _from_yfinance

        fi_none = MagicMock()
        fi_none.last_price = None
        fi_none.previous_close = 24380.0

        fi_valid = self._make_fast_info(24500.0, 24380.0)

        tickers = [MagicMock(fast_info=fi_none), MagicMock(fast_info=fi_valid)]
        call_count = {"n": 0}

        def make_ticker(sym):
            t = tickers[call_count["n"]]
            call_count["n"] += 1
            return t

        with patch("yfinance.Ticker", side_effect=make_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is not None

    def test_high_low_captured(self):
        from market.gift_nifty import _from_yfinance

        mock_fi = self._make_fast_info(24500.0, 24380.0, day_high=24600.0, day_low=24300.0)
        mock_ticker = MagicMock()
        mock_ticker.fast_info = mock_fi

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = _from_yfinance(nifty_spot=None)

        assert result is not None
        assert result.high == pytest.approx(24600.0, abs=1)
        assert result.low == pytest.approx(24300.0, abs=1)


# ── get_gift_nifty public API ─────────────────────────────────────────────────


class TestGetGiftNifty:
    def test_returns_snapshot_on_success(self):
        from market.gift_nifty import get_gift_nifty, GiftNiftySnapshot

        fake = GiftNiftySnapshot(ltp=24500.0, change=100.0, change_pct=0.41, source="yfinance")
        with patch("market.gift_nifty._from_yfinance", return_value=fake):
            result = get_gift_nifty()

        assert result is fake

    def test_returns_none_when_all_sources_fail(self):
        from market.gift_nifty import get_gift_nifty

        with patch("market.gift_nifty._from_yfinance", return_value=None):
            result = get_gift_nifty()

        assert result is None

    def test_passes_nifty_spot_through(self):
        from market.gift_nifty import get_gift_nifty

        with patch("market.gift_nifty._from_yfinance", return_value=None) as mock_fn:
            get_gift_nifty(nifty_spot=24350.0)
            mock_fn.assert_called_once_with(24350.0)


# ── MarketSnapshot integration ────────────────────────────────────────────────


class TestMarketSnapshotIntegration:
    def _make_index_snapshot(self, name="NIFTY50", ltp=24000.0):
        from market.indices import IndexSnapshot

        return IndexSnapshot(
            name=name, instrument=f"NSE:{name}", ltp=ltp, change=100.0, change_pct=0.42,
            open=23900.0, high=24100.0, low=23800.0,
        )

    def test_gift_nifty_field_exists_on_market_snapshot(self):
        from market.indices import MarketSnapshot

        snap = MarketSnapshot(
            nifty=self._make_index_snapshot("NIFTY50"),
            banknifty=self._make_index_snapshot("BANKNIFTY", 52000.0),
            vix=self._make_index_snapshot("VIX", 14.5),
            sensex=self._make_index_snapshot("SENSEX", 79000.0),
            posture="BULLISH",
            posture_reason="NIFTY +0.42%",
        )
        assert hasattr(snap, "gift_nifty")
        assert snap.gift_nifty is None  # default

    def test_gift_nifty_set_on_market_snapshot(self):
        from market.indices import MarketSnapshot
        from market.gift_nifty import GiftNiftySnapshot

        g = GiftNiftySnapshot(ltp=24200.0, change=100.0, change_pct=0.42, source="yfinance")
        snap = MarketSnapshot(
            nifty=self._make_index_snapshot("NIFTY50"),
            banknifty=self._make_index_snapshot("BANKNIFTY", 52000.0),
            vix=self._make_index_snapshot("VIX", 14.5),
            sensex=self._make_index_snapshot("SENSEX", 79000.0),
            posture="BULLISH",
            posture_reason="NIFTY +0.42%",
            gift_nifty=g,
        )
        assert snap.gift_nifty is g
        assert snap.gift_nifty.ltp == 24200.0

    def test_get_market_snapshot_includes_gift_nifty(self):
        """get_market_snapshot() should attach gift_nifty (or None) to the snapshot."""
        from market.indices import get_market_snapshot
        from market.gift_nifty import GiftNiftySnapshot

        fake_quote = MagicMock()
        fake_quote.last_price = 24000.0
        fake_quote.change = 100.0
        fake_quote.change_pct = 0.42
        fake_quote.open = 23900.0
        fake_quote.high = 24100.0
        fake_quote.low = 23800.0

        fake_gift = GiftNiftySnapshot(ltp=24150.0, change=150.0, change_pct=0.63, source="yfinance")

        with (
            patch("market.quotes.get_quote", return_value={
                "NSE:NIFTY 50": fake_quote,
                "NSE:NIFTY BANK": fake_quote,
                "NSE:INDIA VIX": MagicMock(last_price=14.5, change=0.1, change_pct=0.69,
                                            open=14.4, high=14.6, low=14.2),
                "BSE:SENSEX": fake_quote,
            }),
            patch("market.gift_nifty.get_gift_nifty", return_value=fake_gift),
        ):
            snap = get_market_snapshot()

        assert snap.gift_nifty is not None
        assert snap.gift_nifty.ltp == 24150.0

    def test_get_market_snapshot_handles_gift_nifty_failure(self):
        """gift_nifty failure should not crash get_market_snapshot."""
        from market.indices import get_market_snapshot

        fake_quote = MagicMock()
        fake_quote.last_price = 24000.0
        fake_quote.change = 100.0
        fake_quote.change_pct = 0.42
        fake_quote.open = 23900.0
        fake_quote.high = 24100.0
        fake_quote.low = 23800.0

        with (
            patch("market.quotes.get_quote", return_value={
                "NSE:NIFTY 50": fake_quote,
                "NSE:NIFTY BANK": fake_quote,
                "NSE:INDIA VIX": MagicMock(last_price=14.5, change=0.1, change_pct=0.69,
                                            open=14.4, high=14.6, low=14.2),
                "BSE:SENSEX": fake_quote,
            }),
            patch("market.gift_nifty.get_gift_nifty", side_effect=Exception("timeout")),
        ):
            snap = get_market_snapshot()  # must not raise

        # gift_nifty is None when fetch fails
        assert snap.gift_nifty is None
        # Core fields are still populated
        assert snap.nifty.ltp == 24000.0
