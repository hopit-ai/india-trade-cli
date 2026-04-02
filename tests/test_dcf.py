"""Tests for analysis/dcf.py — DCF valuation model.

TDD — written before implementation.
"""

import pytest


class TestWACC:
    def test_basic_wacc(self):
        from analysis.dcf import compute_wacc
        # Beta=1.0, D/E=0, risk_free=7%, ERP=6.5% → WACC = 13.5% (all equity)
        wacc = compute_wacc(beta=1.0, debt_equity=0.0)
        assert wacc == pytest.approx(13.5, abs=0.5)

    def test_levered_wacc(self):
        from analysis.dcf import compute_wacc
        # With debt, WACC should be lower than cost of equity (debt is cheaper)
        wacc_no_debt = compute_wacc(beta=1.0, debt_equity=0.0)
        wacc_with_debt = compute_wacc(beta=1.0, debt_equity=0.5)
        assert wacc_with_debt < wacc_no_debt

    def test_high_beta_higher_wacc(self):
        from analysis.dcf import compute_wacc
        wacc_low = compute_wacc(beta=0.5, debt_equity=0.3)
        wacc_high = compute_wacc(beta=1.5, debt_equity=0.3)
        assert wacc_high > wacc_low

    def test_zero_beta(self):
        from analysis.dcf import compute_wacc
        # Beta=0 → cost of equity = risk-free rate
        wacc = compute_wacc(beta=0.0, debt_equity=0.0)
        assert wacc == pytest.approx(7.0, abs=0.5)  # risk-free only


class TestDCF:
    def test_positive_fcf_gives_positive_value(self):
        from analysis.dcf import compute_dcf
        result = compute_dcf(
            fcf_cr=1000,           # ₹1000 Cr FCF
            growth_rate=10.0,      # 10% growth
            wacc=12.0,             # 12% WACC
            terminal_growth=4.0,   # 4% terminal
            shares_outstanding=100_000_000,  # 10 Cr shares
            net_debt_cr=500,       # ₹500 Cr net debt
        )
        assert result.intrinsic_value > 0
        assert result.enterprise_value > 0

    def test_higher_growth_higher_value(self):
        from analysis.dcf import compute_dcf
        low = compute_dcf(fcf_cr=1000, growth_rate=5.0, wacc=12.0,
                          shares_outstanding=100_000_000, net_debt_cr=0)
        high = compute_dcf(fcf_cr=1000, growth_rate=20.0, wacc=12.0,
                           shares_outstanding=100_000_000, net_debt_cr=0)
        assert high.intrinsic_value > low.intrinsic_value

    def test_higher_wacc_lower_value(self):
        from analysis.dcf import compute_dcf
        low_wacc = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=10.0,
                               shares_outstanding=100_000_000, net_debt_cr=0)
        high_wacc = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=15.0,
                                shares_outstanding=100_000_000, net_debt_cr=0)
        assert low_wacc.intrinsic_value > high_wacc.intrinsic_value

    def test_negative_fcf_returns_zero(self):
        from analysis.dcf import compute_dcf
        result = compute_dcf(fcf_cr=-500, growth_rate=10.0, wacc=12.0,
                             shares_outstanding=100_000_000, net_debt_cr=0)
        # Negative FCF → intrinsic value should be 0 or negative (company burns cash)
        assert result.intrinsic_value <= 0

    def test_margin_of_safety(self):
        from analysis.dcf import compute_dcf
        result = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=12.0,
                             shares_outstanding=100_000_000, net_debt_cr=0,
                             current_price=50.0)
        # If intrinsic > current → positive margin of safety (undervalued)
        if result.intrinsic_value > 50.0:
            assert result.margin_of_safety > 0
        else:
            assert result.margin_of_safety <= 0

    def test_sensitivity_table(self):
        from analysis.dcf import compute_dcf
        result = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=12.0,
                             shares_outstanding=100_000_000, net_debt_cr=0)
        assert result.sensitivity is not None
        assert len(result.sensitivity) > 0
        # Should be a grid of growth × WACC
        for row in result.sensitivity:
            assert "growth" in row
            assert "wacc" in row
            assert "intrinsic_value" in row

    def test_net_debt_reduces_value(self):
        from analysis.dcf import compute_dcf
        no_debt = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=12.0,
                              shares_outstanding=100_000_000, net_debt_cr=0)
        with_debt = compute_dcf(fcf_cr=1000, growth_rate=10.0, wacc=12.0,
                                shares_outstanding=100_000_000, net_debt_cr=5000)
        assert with_debt.intrinsic_value < no_debt.intrinsic_value


class TestDCFFromSymbol:
    def test_dcf_for_symbol_returns_result(self):
        from analysis.dcf import dcf_for_symbol
        result = dcf_for_symbol("RELIANCE")
        assert isinstance(result, dict)
        # Should have either intrinsic_value or error
        assert "intrinsic_value" in result or "error" in result

    def test_dcf_for_index_returns_error(self):
        from analysis.dcf import dcf_for_symbol
        result = dcf_for_symbol("NIFTY")
        # Indices don't have FCF
        assert "error" in result or result.get("intrinsic_value", 0) <= 0
