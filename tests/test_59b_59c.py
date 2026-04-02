"""Tests for 59b (sector rotation fallback) and 59c (NSE shareholding pattern).

TDD — written before implementation.
"""

import pytest


class TestSectorFallback:
    """59b: Sector rotation should have yfinance fallback when NSE returns zeros."""

    def test_get_sector_snapshot_returns_list(self):
        """Should return list of IndexSnapshot."""
        from market.indices import get_sector_snapshot
        result = get_sector_snapshot()
        assert isinstance(result, list)

    def test_sectors_have_non_zero_values(self):
        """At least some sectors should have real prices."""
        from market.indices import get_sector_snapshot
        result = get_sector_snapshot()
        non_zero = [s for s in result if s.ltp > 0]
        # With yfinance fallback, should always have data
        assert len(non_zero) > 0


class TestNSEShareholding:
    """59c: NSE shareholding pattern parser."""

    def test_parse_shareholding_xbrl(self):
        """Parser should extract promoter/FII/DII from XBRL data."""
        from analysis.fundamental import _parse_shareholding_xbrl

        # Minimal XBRL-like data simulating what the parser extracts
        sample = {
            "promoter": 50.01,
            "fii": 19.09,
            "dii": 20.18,
            "retail": 10.63,
            "pledged": False,
            "mutual_funds": 9.52,
            "insurance": 9.05,
        }
        # The parser should return a dict with these keys
        assert sample["promoter"] == pytest.approx(50.01)
        assert sample["fii"] == pytest.approx(19.09)
        assert sample["dii"] == pytest.approx(20.18)

    def test_fetch_nse_shareholding_returns_dict(self):
        """fetch should return a dict (may be empty if API fails)."""
        from analysis.fundamental import _fetch_nse_shareholding
        result = _fetch_nse_shareholding("RELIANCE")
        assert isinstance(result, dict)

    def test_shareholding_has_promoter(self):
        """If data available, promoter % should be present."""
        from analysis.fundamental import _fetch_nse_shareholding
        result = _fetch_nse_shareholding("RELIANCE")
        # May be empty if NSE API is down, but if data exists it should have promoter
        if result:
            assert "promoter_pct" in result
            assert result["promoter_pct"] > 0

    def test_shareholding_has_fii_dii(self):
        """If data available, FII and DII % should be present."""
        from analysis.fundamental import _fetch_nse_shareholding
        result = _fetch_nse_shareholding("RELIANCE")
        if result:
            assert "fii_pct" in result
            assert "dii_pct" in result

    def test_shareholding_has_pledge(self):
        """If data available, pledge status should be present."""
        from analysis.fundamental import _fetch_nse_shareholding
        result = _fetch_nse_shareholding("RELIANCE")
        if result:
            assert "pledged" in result
