"""Tests for analysis/fundamental.py — scoring and parsing logic."""

import pytest

from analysis.fundamental import _score, _safe_float


class TestScore:
    def test_strong_fundamentals(self, strong_fundamentals):
        """High-quality company should score >= 70."""
        score, flags = _score(strong_fundamentals)
        assert score >= 70, f"Strong fundamentals scored {score}, expected >= 70"
        good_flags = [f for f in flags if f.verdict == "GOOD"]
        assert len(good_flags) >= 3

    def test_weak_fundamentals(self, weak_fundamentals):
        """Weak company should score <= 35."""
        score, flags = _score(weak_fundamentals)
        assert score <= 35, f"Weak fundamentals scored {score}, expected <= 35"
        bad_flags = [f for f in flags if f.verdict == "BAD"]
        assert len(bad_flags) >= 2

    def test_neutral_baseline(self):
        """Empty data → baseline score of 50."""
        score, flags = _score({})
        assert score == 50
        assert len(flags) == 0

    def test_high_pe_penalized(self):
        """PE > 40 should be flagged as WARN or BAD."""
        score, flags = _score({"pe": 80.0})
        pe_flags = [f for f in flags if "P/E" in f.metric]
        assert len(pe_flags) > 0
        assert score < 50

    def test_good_roe_rewarded(self):
        """ROE > 15% should add points."""
        score, flags = _score({"roe": 25.0})
        assert score > 50

    def test_high_pledging_penalized(self):
        """Pledged > 25% should be BAD."""
        score, flags = _score({"pledged_pct": 30.0})
        pledge_flags = [f for f in flags if "Pledged" in f.metric]
        assert len(pledge_flags) == 1
        assert pledge_flags[0].verdict == "BAD"
        assert score < 50


class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float({"pe": 25.3}, "pe") == pytest.approx(25.3)

    def test_string_value(self):
        assert _safe_float({"pe": "25.3"}, "pe") == pytest.approx(25.3)

    def test_missing_key(self):
        assert _safe_float({}, "pe") is None

    def test_none_value(self):
        assert _safe_float({"pe": None}, "pe") is None

    def test_multiple_key_fallback(self):
        """Should try multiple keys and return first match."""
        data = {"Price to Earning": 20.0}
        assert _safe_float(data, "pe", "Price to Earning") == pytest.approx(20.0)

    def test_malformed_string(self):
        assert _safe_float({"pe": "N/A"}, "pe") is None
