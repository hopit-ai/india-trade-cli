"""Tests for market/sentiment.py — FII/DII parsing, breadth, news scoring."""

import pytest

from market.sentiment import FIIDIIData, score_headline, _build_breadth


class TestFIIDIIVerdict:
    def test_fii_buying(self):
        """FII net > 500 → FII_BUYING."""
        d = FIIDIIData(
            date="2025-04-01", fii_buy=15000, fii_sell=10000, fii_net=5000,
            dii_buy=8000, dii_sell=9000, dii_net=-1000, verdict="FII_BUYING",
        )
        assert d.verdict == "FII_BUYING"

    def test_fii_selling(self):
        d = FIIDIIData(
            date="2025-04-01", fii_buy=10000, fii_sell=18000, fii_net=-8000,
            dii_buy=8000, dii_sell=5000, dii_net=3000, verdict="FII_SELLING",
        )
        assert d.verdict == "FII_SELLING"


class TestBreadth:
    def test_broad_rally(self):
        b = _build_breadth(400, 100, 0)
        assert b.verdict == "BROAD_RALLY"
        assert b.ad_ratio > 2.0

    def test_broad_decline(self):
        b = _build_breadth(50, 400, 50)
        assert b.verdict == "BROAD_DECLINE"
        assert b.ad_ratio < 0.5

    def test_mixed(self):
        b = _build_breadth(250, 250, 0)
        assert b.verdict == "MIXED"


class TestNewsScoring:
    def test_bullish_headline(self):
        verdict, score = score_headline("Stock surges to record high on strong results")
        assert verdict == "BULLISH"
        assert score > 0

    def test_bearish_headline(self):
        verdict, score = score_headline("Stocks crash plunge decline amid selloff losses")
        assert verdict == "BEARISH"
        assert score < 0

    def test_neutral_headline(self):
        verdict, score = score_headline("Company announces board meeting")
        assert verdict == "NEUTRAL"
        assert score == pytest.approx(0.0, abs=0.1)
