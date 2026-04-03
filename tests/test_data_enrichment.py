"""Tests for enriched fundamental data (issue #59).

TDD — written before implementation. Tests define the spec for
all new data fields in FundamentalSnapshot.
"""



class TestFundamentalSnapshotFields:
    """Verify FundamentalSnapshot has all new fields."""

    def test_sector_industry_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "sector")
        assert hasattr(snap, "industry")

    def test_governance_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "overall_risk")
        assert hasattr(snap, "audit_risk")
        assert hasattr(snap, "board_risk")

    def test_forward_estimates_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "forward_pe")
        assert hasattr(snap, "next_earnings_date")
        assert hasattr(snap, "earnings_estimate")

    def test_margin_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "operating_margin")
        assert hasattr(snap, "gross_margin")
        assert hasattr(snap, "ebitda_margin")

    def test_cash_debt_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "total_cash_cr")
        assert hasattr(snap, "total_debt_cr")

    def test_valuation_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "price_to_sales")
        assert hasattr(snap, "ev_to_revenue")

    def test_dividend_fields_exist(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "payout_ratio")
        assert hasattr(snap, "five_yr_avg_div_yield")

    def test_insider_field_exists(self):
        from analysis.fundamental import FundamentalSnapshot
        snap = FundamentalSnapshot(symbol="TEST")
        assert hasattr(snap, "insider_transactions")


class TestScoringWithNewData:
    """Verify scoring logic uses new data correctly."""

    def test_high_governance_risk_penalized(self):
        from analysis.fundamental import _score
        score, flags = _score({"overall_risk": 10, "audit_risk": 9})
        risk_flags = [f for f in flags if "risk" in f.metric.lower() or "governance" in f.metric.lower()]
        assert len(risk_flags) > 0

    def test_low_governance_risk_ok(self):
        from analysis.fundamental import _score
        score, flags = _score({"overall_risk": 3})
        risk_flags = [f for f in flags if "governance" in f.metric.lower()]
        # Low risk should not generate a negative flag
        assert all(f.verdict != "BAD" for f in risk_flags)

    def test_earnings_soon_flagged(self):
        from analysis.fundamental import _score
        from datetime import date, timedelta
        soon = (date.today() + timedelta(days=3)).isoformat()
        score, flags = _score({"next_earnings_date": soon})
        earnings_flags = [f for f in flags if "earning" in f.metric.lower()]
        assert len(earnings_flags) > 0

    def test_high_payout_ratio_warned(self):
        from analysis.fundamental import _score
        score, flags = _score({"payout_ratio": 0.95})
        payout_flags = [f for f in flags if "payout" in f.metric.lower()]
        assert len(payout_flags) > 0
        assert payout_flags[0].verdict in ("WARN", "BAD")

    def test_insider_selling_flagged(self):
        from analysis.fundamental import _score
        score, flags = _score({
            "insider_net_shares": -500000,
            "insider_summary": "Net selling: 500K shares in last 3 months",
        })
        insider_flags = [f for f in flags if "insider" in f.metric.lower()]
        assert len(insider_flags) > 0


class TestMostActiveStocks:
    """Test NSE Most Active Stocks module."""

    def test_import(self):
        from market.active_stocks import get_most_active
        # Should not crash on import
        assert callable(get_most_active)

    def test_returns_list(self):
        from market.active_stocks import get_most_active
        result = get_most_active()
        assert isinstance(result, list)
        # May be empty if NSE API is down, but should never crash


class TestSectorFallback:
    """Test sector rotation yfinance fallback."""

    def test_sector_snapshot_returns_dict(self):
        from market.indices import get_sector_snapshot
        result = get_sector_snapshot()
        assert isinstance(result, (dict, list))
