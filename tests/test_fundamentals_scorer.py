"""
tests/test_fundamentals_scorer.py
───────────────────────────────────
Tests for the structured India fundamentals scorer (#171).

Covers:
  - MetricResult dataclass
  - FundamentalsScore dataclass (as_text, signal thresholds)
  - _score_metric for each metric (standard + inverted)
  - score_fundamentals() end-to-end (mocked analyse())
  - Edge cases: None values, extreme values, partial data
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from analysis.fundamental import (
    FundamentalSnapshot,
    FundamentalsScore,
    MetricResult,
    _score_metric,
    score_fundamentals,
)


# ── Helpers ───────────────────────────────────────────────────────


def _make_snap(**kwargs) -> FundamentalSnapshot:
    """Build a minimal FundamentalSnapshot with given field overrides."""
    defaults = dict(
        symbol="INFY",
        name="Infosys Ltd",
        roe=None,
        roce=None,
        npm=None,
        sales_growth=None,
        profit_growth=None,
        debt_equity=None,
        promoter_holding=None,
        pledged_pct=None,
        dividend_yield=None,
        pe=None,
        pb=None,
        flags=[],
        score=50,
        verdict="NEUTRAL",
        summary="test",
    )
    defaults.update(kwargs)
    return FundamentalSnapshot(**defaults)


# ── MetricResult ──────────────────────────────────────────────────


class TestMetricResult:
    def test_fields_populated(self):
        m = MetricResult(
            metric="ROE",
            value=25.0,
            weight=0.20,
            threshold_met="BULLISH",
            score=0.20,
            label="25.0%",
            detail=">15% — strong return on equity",
        )
        assert m.metric == "ROE"
        assert m.threshold_met == "BULLISH"
        assert m.score == pytest.approx(0.20)


# ── _score_metric ─────────────────────────────────────────────────


class TestScoreMetric:
    # ROE (standard: higher is better, bull≥15, bear<8)
    def test_roe_bullish(self):
        tm, contrib, label, _ = _score_metric("roe", 20.0)
        assert tm == "BULLISH"
        assert contrib == 1.0
        assert "20.0%" in label

    def test_roe_bearish(self):
        tm, contrib, _, _ = _score_metric("roe", 5.0)
        assert tm == "BEARISH"
        assert contrib == -1.0

    def test_roe_neutral(self):
        tm, contrib, _, _ = _score_metric("roe", 10.0)
        assert tm == "NEUTRAL"
        assert contrib == 0.0

    def test_roe_none(self):
        tm, contrib, label, _ = _score_metric("roe", None)
        assert tm == "N/A"
        assert contrib == 0.0
        assert label == "N/A"

    # NPM (bull≥15, bear<5)
    def test_npm_bullish(self):
        tm, contrib, _, _ = _score_metric("npm", 18.0)
        assert tm == "BULLISH" and contrib == 1.0

    def test_npm_bearish(self):
        tm, contrib, _, _ = _score_metric("npm", 3.0)
        assert tm == "BEARISH" and contrib == -1.0

    # Revenue growth (bull≥15, bear<5)
    def test_sales_growth_bullish(self):
        tm, _, _, _ = _score_metric("sales_growth", 20.0)
        assert tm == "BULLISH"

    def test_sales_growth_bearish(self):
        tm, _, _, _ = _score_metric("sales_growth", 2.0)
        assert tm == "BEARISH"

    # Debt/Equity (inverted: lower is better)
    def test_de_bullish_low(self):
        tm, contrib, label, _ = _score_metric("debt_equity", 0.3)
        assert tm == "BULLISH"
        assert contrib == 1.0
        assert "0.30x" in label

    def test_de_bearish_high(self):
        tm, contrib, _, _ = _score_metric("debt_equity", 2.0)
        assert tm == "BEARISH"
        assert contrib == -1.0

    def test_de_neutral_moderate(self):
        tm, contrib, _, _ = _score_metric("debt_equity", 1.0)
        assert tm == "NEUTRAL"
        assert contrib == 0.0

    def test_de_none(self):
        tm, _, _, _ = _score_metric("debt_equity", None)
        assert tm == "N/A"

    # Pledged % (inverted: lower is better)
    def test_pledged_bullish_low(self):
        tm, contrib, _, _ = _score_metric("pledged_pct", 5.0)
        assert tm == "BULLISH" and contrib == 1.0

    def test_pledged_bearish_high(self):
        tm, contrib, _, _ = _score_metric("pledged_pct", 45.0)
        assert tm == "BEARISH" and contrib == -1.0

    def test_pledged_neutral(self):
        tm, contrib, _, _ = _score_metric("pledged_pct", 20.0)
        assert tm == "NEUTRAL" and contrib == 0.0

    # P/E (inverted custom logic)
    def test_pe_bullish_low(self):
        tm, contrib, label, _ = _score_metric("pe", 15.0)
        assert tm == "BULLISH"
        assert contrib == 1.0

    def test_pe_bearish_high(self):
        tm, contrib, _, _ = _score_metric("pe", 50.0)
        assert tm == "BEARISH"
        assert contrib == -1.0

    def test_pe_bearish_negative(self):
        """Negative PE means loss-making."""
        tm, contrib, _, _ = _score_metric("pe", -10.0)
        assert tm == "BEARISH"
        assert contrib == -1.0

    def test_pe_neutral_fair(self):
        tm, contrib, _, _ = _score_metric("pe", 30.0)
        assert tm == "NEUTRAL"
        assert contrib == 0.0

    # Promoter holding (bull≥50, bear<25)
    def test_promoter_bullish(self):
        tm, _, _, _ = _score_metric("promoter_holding", 65.0)
        assert tm == "BULLISH"

    def test_promoter_bearish(self):
        tm, _, _, _ = _score_metric("promoter_holding", 10.0)
        assert tm == "BEARISH"

    # Dividend yield (bull≥2, bear=0)
    def test_div_yield_bullish(self):
        tm, _, _, _ = _score_metric("dividend_yield", 3.0)
        assert tm == "BULLISH"

    def test_div_yield_neutral_zero(self):
        # 0% dividend is NEUTRAL (growth stocks don't pay dividends — not necessarily bad)
        tm, _, _, _ = _score_metric("dividend_yield", 0.0)
        assert tm == "NEUTRAL"

    def test_div_yield_neutral_low(self):
        tm, _, _, _ = _score_metric("dividend_yield", 1.0)
        assert tm == "NEUTRAL"


# ── FundamentalsScore ─────────────────────────────────────────────


class TestFundamentalsScore:
    def _make_score(self, signal: str = "STRONG", overall: float = 0.35) -> FundamentalsScore:
        metrics = {
            "ROE": MetricResult("ROE", 20.0, 0.20, "BULLISH", 0.20, "20%", ""),
        }
        return FundamentalsScore(
            symbol="INFY",
            overall_score=overall,
            signal=signal,
            metrics=metrics,
            data_quality="screener",
        )

    def test_as_text_contains_symbol(self):
        fs = self._make_score()
        text = fs.as_text()
        assert "INFY" in text

    def test_as_text_contains_signal(self):
        fs = self._make_score("STRONG")
        text = fs.as_text()
        assert "STRONG" in text

    def test_as_text_contains_metric_name(self):
        fs = self._make_score()
        text = fs.as_text()
        assert "ROE" in text

    def test_as_text_contains_data_quality(self):
        fs = self._make_score()
        text = fs.as_text()
        assert "screener" in text

    def test_signal_neutral(self):
        fs = self._make_score("NEUTRAL", 0.05)
        assert fs.signal == "NEUTRAL"


# ── score_fundamentals (end-to-end with mocked analyse) ──────────


class TestScoreFundamentals:
    def _mock_snap(self, **kwargs) -> FundamentalSnapshot:
        return _make_snap(**kwargs)

    def test_returns_fundamentals_score(self):
        snap = self._mock_snap(roe=20.0, npm=18.0, debt_equity=0.3, pe=18.0)
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert isinstance(result, FundamentalsScore)

    def test_symbol_matches(self):
        snap = self._mock_snap(symbol="RELIANCE")
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("RELIANCE")
        assert result.symbol == "RELIANCE"

    def test_strong_signal_when_all_metrics_good(self):
        """All metrics bullish → STRONG signal."""
        snap = self._mock_snap(
            roe=25.0,
            npm=20.0,
            sales_growth=18.0,
            debt_equity=0.2,
            promoter_holding=60.0,
            pledged_pct=5.0,
            dividend_yield=2.5,
            pe=16.0,
        )
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("HDFC")
        assert result.signal == "STRONG"
        assert result.overall_score > 0.20

    def test_weak_signal_when_all_metrics_bad(self):
        """All metrics bearish → WEAK signal."""
        snap = self._mock_snap(
            roe=3.0,
            npm=2.0,
            sales_growth=1.0,
            debt_equity=2.5,
            promoter_holding=15.0,
            pledged_pct=50.0,
            dividend_yield=0.0,
            pe=60.0,
        )
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("BADCO")
        assert result.signal == "WEAK"
        assert result.overall_score < -0.20

    def test_neutral_signal_for_mixed_metrics(self):
        """Some good, some bad → NEUTRAL."""
        snap = self._mock_snap(
            roe=20.0,  # bullish
            npm=3.0,  # bearish
            sales_growth=None,
            debt_equity=None,
            pe=30.0,  # neutral
        )
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("MIX")
        # Net score is approximately ROE(+0.20) + NPM(-0.15) + PE(0) = +0.05 → NEUTRAL
        assert result.signal == "NEUTRAL"

    def test_all_none_values_gives_neutral(self):
        """No data → all N/A → score = 0 → NEUTRAL."""
        snap = self._mock_snap()  # all None
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("NODATA")
        assert result.overall_score == pytest.approx(0.0)
        assert result.signal == "NEUTRAL"
        for m in result.metrics.values():
            assert m.threshold_met == "N/A"

    def test_metrics_dict_has_eight_keys(self):
        snap = self._mock_snap()
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert len(result.metrics) == 8

    def test_data_quality_screener_when_roe_and_roce_present(self):
        snap = self._mock_snap(roe=20.0, roce=18.0)
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert result.data_quality == "screener"

    def test_data_quality_yfinance_when_only_pe(self):
        snap = self._mock_snap(pe=22.0)  # no ROE/ROCE
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert result.data_quality == "yfinance"

    def test_data_quality_unavailable_when_no_data(self):
        snap = self._mock_snap()
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert result.data_quality == "unavailable"

    def test_score_bounded_minus_one_to_plus_one(self):
        """Extreme values should not exceed [-1, +1] since weights sum to 1."""
        snap = self._mock_snap(
            roe=50.0,
            npm=40.0,
            sales_growth=50.0,
            debt_equity=0.0,
            promoter_holding=75.0,
            pledged_pct=0.0,
            dividend_yield=10.0,
            pe=5.0,
        )
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        assert -1.0 <= result.overall_score <= 1.0

    def test_as_text_from_score_fundamentals(self):
        snap = self._mock_snap(roe=20.0, npm=18.0)
        with patch("analysis.fundamental.analyse", return_value=snap):
            result = score_fundamentals("INFY")
        text = result.as_text()
        assert "INFY" in text
        assert "ROE" in text
