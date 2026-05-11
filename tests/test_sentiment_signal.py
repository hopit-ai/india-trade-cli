"""
tests/test_sentiment_signal.py
────────────────────────────────
Tests for the unified India market sentiment signal (#172).

Covers:
  - SentimentSignal dataclass
  - Individual component signals (FII/DII, news, bulk deals, breadth)
  - get_sentiment() aggregation (weights, thresholds, confidence)
  - Edge cases: empty data, unavailable data, all signals agree
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from market.sentiment import (
    FIIDIIData,
    MarketBreadth,
    SentimentSignal,
    _COMPONENT_WEIGHTS,
    _breadth_signal,
    _bulk_deals_signal,
    _fii_dii_signal,
    _news_signal,
    get_sentiment,
)


# ── Helpers ───────────────────────────────────────────────────────


def _fii(net: float, days: int = 1) -> list[FIIDIIData]:
    verdict = "FII_BUYING" if net > 500 else "FII_SELLING" if net < -500 else "NEUTRAL"
    return [
        FIIDIIData(
            date="2026-05-10",
            fii_buy=abs(net),
            fii_sell=0,
            fii_net=net,
            dii_buy=100,
            dii_sell=100,
            dii_net=0,
            verdict=verdict,
        )
    ] * days


def _breadth(adv: int, dec: int) -> MarketBreadth:
    ratio = adv / max(dec, 1)
    v = "BROAD_RALLY" if ratio > 2.0 else "BROAD_DECLINE" if ratio < 0.5 else "MIXED"
    return MarketBreadth(
        advances=adv, declines=dec, unchanged=0, ad_ratio=round(ratio, 2), verdict=v
    )


# ── SentimentSignal dataclass ─────────────────────────────────────


class TestSentimentSignalDataclass:
    def test_fields_set(self):
        sig = SentimentSignal(
            symbol="INFY",
            overall_signal="BULLISH",
            confidence=60,
            breakdown={"fii_dii": "BULLISH"},
            key_driver="FII/DII flows",
            sources=["FII net: +3000 Cr"],
            score=0.30,
        )
        assert sig.symbol == "INFY"
        assert sig.overall_signal == "BULLISH"
        assert sig.confidence == 60

    def test_overall_signal_values(self):
        for s in ("BULLISH", "NEUTRAL", "BEARISH"):
            sig = SentimentSignal("X", s, 50, {}, "", [], 0.0)
            assert sig.overall_signal == s


# ── Component weights ─────────────────────────────────────────────


class TestComponentWeights:
    def test_weights_sum_to_one(self):
        assert abs(sum(_COMPONENT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_components_present(self):
        for k in ("fii_dii", "news", "bulk_deals", "breadth"):
            assert k in _COMPONENT_WEIGHTS


# ── _fii_dii_signal ───────────────────────────────────────────────


class TestFIIDIISignal:
    def test_bullish_on_strong_fii_buying(self):
        with patch("market.sentiment.get_fii_dii_data", return_value=_fii(3000, 5)):
            sig, score, sources = _fii_dii_signal()
        assert sig == "BULLISH"
        assert score > 0

    def test_bearish_on_strong_fii_selling(self):
        with patch("market.sentiment.get_fii_dii_data", return_value=_fii(-3000, 5)):
            sig, score, sources = _fii_dii_signal()
        assert sig == "BEARISH"
        assert score < 0

    def test_neutral_on_low_flows(self):
        with patch("market.sentiment.get_fii_dii_data", return_value=_fii(100, 3)):
            sig, score, _ = _fii_dii_signal()
        assert sig == "NEUTRAL"
        assert score == 0.0

    def test_neutral_on_empty_data(self):
        with patch("market.sentiment.get_fii_dii_data", return_value=[]):
            sig, score, sources = _fii_dii_signal()
        assert sig == "NEUTRAL"
        assert sources == []

    def test_neutral_on_exception(self):
        with patch("market.sentiment.get_fii_dii_data", side_effect=Exception("NSE down")):
            sig, score, sources = _fii_dii_signal()
        assert sig == "NEUTRAL"
        assert score == 0.0

    def test_sources_not_empty_when_data_available(self):
        with patch("market.sentiment.get_fii_dii_data", return_value=_fii(2500, 5)):
            _, _, sources = _fii_dii_signal()
        assert len(sources) > 0
        assert "FII" in sources[0]


# ── _news_signal ──────────────────────────────────────────────────


class TestNewsSignal:
    def _mock_news_items(self, n: int = 5):
        item = MagicMock()
        item.title = "INFY Q4 beats estimates"
        item.summary = "Strong revenue growth"
        return [item] * n

    def test_bullish_on_positive_news(self):
        items = self._mock_news_items()
        with patch("market.news.get_stock_news", return_value=items):
            with patch(
                "market.sentiment.score_news_batch",
                return_value={
                    "overall": "BULLISH",
                    "score": 0.5,
                    "bullish_count": 4,
                    "bearish_count": 0,
                    "neutral_count": 1,
                    "items": [],
                },
            ):
                sig, score, sources = _news_signal("INFY")
        assert sig == "BULLISH"
        assert score > 0

    def test_bearish_on_negative_news(self):
        items = self._mock_news_items()
        with patch("market.news.get_stock_news", return_value=items):
            with patch(
                "market.sentiment.score_news_batch",
                return_value={
                    "overall": "BEARISH",
                    "score": -0.5,
                    "bullish_count": 0,
                    "bearish_count": 4,
                    "neutral_count": 1,
                    "items": [],
                },
            ):
                sig, score, sources = _news_signal("INFY")
        assert sig == "BEARISH"
        assert score < 0

    def test_neutral_on_no_news(self):
        with patch("market.news.get_stock_news", return_value=[]):
            sig, score, sources = _news_signal("INFY")
        assert sig == "NEUTRAL"
        assert sources == []

    def test_neutral_on_exception(self):
        with patch("market.news.get_stock_news", side_effect=Exception("timeout")):
            sig, score, sources = _news_signal("INFY")
        assert sig == "NEUTRAL"


# ── _bulk_deals_signal ────────────────────────────────────────────


class TestBulkDealsSignal:
    def _make_deal(self, deal_type: str, qty: int = 100_000) -> MagicMock:
        d = MagicMock()
        d.deal_type = deal_type
        d.quantity = qty
        return d

    def test_bullish_on_net_buying(self):
        deals = [self._make_deal("BUY", 200_000)] * 3 + [self._make_deal("SELL", 10_000)]
        with patch("market.bulk_deals.get_bulk_deals", return_value=deals):
            sig, score, sources = _bulk_deals_signal("INFY")
        assert sig == "BULLISH"
        assert score > 0

    def test_bearish_on_net_selling(self):
        deals = [self._make_deal("SELL", 200_000)] * 3 + [self._make_deal("BUY", 10_000)]
        with patch("market.bulk_deals.get_bulk_deals", return_value=deals):
            sig, score, sources = _bulk_deals_signal("INFY")
        assert sig == "BEARISH"
        assert score < 0

    def test_neutral_on_no_deals(self):
        with patch("market.bulk_deals.get_bulk_deals", return_value=[]):
            sig, score, sources = _bulk_deals_signal("INFY")
        assert sig == "NEUTRAL"
        assert sources == []

    def test_neutral_on_exception(self):
        with patch("market.bulk_deals.get_bulk_deals", side_effect=Exception("API down")):
            sig, score, sources = _bulk_deals_signal("INFY")
        assert sig == "NEUTRAL"

    def test_sources_describe_deals(self):
        deals = [self._make_deal("BUY", 100_000)]
        with patch("market.bulk_deals.get_bulk_deals", return_value=deals):
            _, _, sources = _bulk_deals_signal("INFY")
        assert len(sources) > 0


# ── _breadth_signal ───────────────────────────────────────────────


class TestBreadthSignal:
    def test_bullish_on_broad_rally(self):
        with patch("market.sentiment.get_market_breadth", return_value=_breadth(400, 100)):
            sig, score, sources = _breadth_signal()
        assert sig == "BULLISH"
        assert score > 0

    def test_bearish_on_broad_decline(self):
        with patch("market.sentiment.get_market_breadth", return_value=_breadth(50, 400)):
            sig, score, sources = _breadth_signal()
        assert sig == "BEARISH"
        assert score < 0

    def test_neutral_on_mixed(self):
        with patch("market.sentiment.get_market_breadth", return_value=_breadth(200, 200)):
            sig, score, sources = _breadth_signal()
        assert sig == "NEUTRAL"

    def test_neutral_on_unavailable(self):
        unavail = MarketBreadth(0, 0, 0, 0.0, "UNAVAILABLE")
        with patch("market.sentiment.get_market_breadth", return_value=unavail):
            sig, score, sources = _breadth_signal()
        assert sig == "NEUTRAL"
        assert sources == []

    def test_neutral_on_exception(self):
        with patch("market.sentiment.get_market_breadth", side_effect=Exception("down")):
            sig, score, sources = _breadth_signal()
        assert sig == "NEUTRAL"


# ── get_sentiment (aggregation) ───────────────────────────────────


class TestGetSentiment:
    def _mock_all_components(
        self,
        fii=("NEUTRAL", 0.0, []),
        news=("NEUTRAL", 0.0, []),
        deals=("NEUTRAL", 0.0, []),
        breadth=("NEUTRAL", 0.0, []),
    ):
        return {
            "market.sentiment._fii_dii_signal": fii,
            "market.sentiment._news_signal": news,
            "market.sentiment._bulk_deals_signal": deals,
            "market.sentiment._breadth_signal": breadth,
        }

    def test_returns_sentiment_signal(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        assert isinstance(result, SentimentSignal)

    def test_symbol_normalised(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY.NS")
        assert result.symbol == "INFY"

    def test_bullish_when_all_bullish(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, ["s1"])),
            patch("market.sentiment._news_signal", return_value=("BULLISH", 1.0, ["s2"])),
            patch("market.sentiment._bulk_deals_signal", return_value=("BULLISH", 1.0, ["s3"])),
            patch("market.sentiment._breadth_signal", return_value=("BULLISH", 1.0, ["s4"])),
        ):
            result = get_sentiment("INFY")
        assert result.overall_signal == "BULLISH"
        assert result.score > 0

    def test_bearish_when_all_bearish(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BEARISH", -1.0, ["s1"])),
            patch("market.sentiment._news_signal", return_value=("BEARISH", -1.0, ["s2"])),
            patch("market.sentiment._bulk_deals_signal", return_value=("BEARISH", -1.0, ["s3"])),
            patch("market.sentiment._breadth_signal", return_value=("BEARISH", -1.0, ["s4"])),
        ):
            result = get_sentiment("INFY")
        assert result.overall_signal == "BEARISH"
        assert result.score < 0

    def test_neutral_when_all_neutral(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        assert result.overall_signal == "NEUTRAL"
        assert result.score == pytest.approx(0.0)

    def test_breakdown_has_all_components(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        assert set(result.breakdown.keys()) == {"fii_dii", "news", "bulk_deals", "breadth"}

    def test_confidence_zero_when_all_neutral(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        assert result.confidence == 0

    def test_confidence_100_when_all_max_bullish(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._news_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("BULLISH", 1.0, [])),
        ):
            result = get_sentiment("INFY")
        assert result.confidence == 100

    def test_key_driver_set(self):
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, ["fii"])),
            patch("market.sentiment._news_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        assert "FII" in result.key_driver

    def test_sources_aggregated_from_all_components(self):
        with (
            patch(
                "market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, ["fii source"])
            ),
            patch("market.sentiment._news_signal", return_value=("BULLISH", 1.0, ["news source"])),
            patch(
                "market.sentiment._bulk_deals_signal",
                return_value=("BULLISH", 1.0, ["deals source"]),
            ),
            patch(
                "market.sentiment._breadth_signal",
                return_value=("BULLISH", 1.0, ["breadth source"]),
            ),
        ):
            result = get_sentiment("INFY")
        assert "fii source" in result.sources
        assert "news source" in result.sources

    def test_score_bounded(self):
        # Max possible score is 1.0 (all weights × 1.0 = 1.0)
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._news_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("BULLISH", 1.0, [])),
        ):
            result = get_sentiment("INFY")
        assert -1.0 <= result.score <= 1.0

    def test_mixed_signals_neutral(self):
        """FII bullish, news bearish → approximately neutral."""
        with (
            patch("market.sentiment._fii_dii_signal", return_value=("BULLISH", 1.0, [])),
            patch("market.sentiment._news_signal", return_value=("BEARISH", -1.0, [])),
            patch("market.sentiment._bulk_deals_signal", return_value=("NEUTRAL", 0.0, [])),
            patch("market.sentiment._breadth_signal", return_value=("NEUTRAL", 0.0, [])),
        ):
            result = get_sentiment("INFY")
        # FII weight=0.30, news weight=0.25 → net = 0.30 - 0.25 = 0.05 (NEUTRAL threshold)
        assert result.overall_signal == "NEUTRAL"
