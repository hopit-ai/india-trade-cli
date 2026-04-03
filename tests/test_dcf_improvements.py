"""Tests for DCF improvements (#75): reverse DCF, FCF quality, bank P/BV, scenarios.

TDD — written before implementation.
"""


# ── Phase 1: Reverse DCF ─────────────────────────────────────


class TestReverseDCF:
    def test_reverse_dcf_finds_implied_growth(self):
        from analysis.dcf import reverse_dcf

        # If intrinsic at 10% growth = 500, and stock trades at 1000,
        # implied growth must be > 10%
        result = reverse_dcf(
            fcf_cr=1000,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            current_price=1500.0,
        )
        assert result is not None
        assert result > 5.0  # needs meaningful growth to justify 1500

    def test_reverse_dcf_low_price_low_growth(self):
        from analysis.dcf import reverse_dcf

        result = reverse_dcf(
            fcf_cr=1000,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            current_price=200.0,
        )
        assert result is not None
        assert result < 10.0  # low price justified by low growth

    def test_reverse_dcf_negative_fcf_returns_none(self):
        from analysis.dcf import reverse_dcf

        result = reverse_dcf(
            fcf_cr=-500,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            current_price=100.0,
        )
        assert result is None  # can't compute with negative FCF


class TestTerminalValueTransparency:
    def test_terminal_pct_shown(self):
        from analysis.dcf import compute_dcf

        result = compute_dcf(
            fcf_cr=1000,
            growth_rate=10.0,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
        )
        assert hasattr(result, "terminal_pct")
        assert 0 < result.terminal_pct < 100

    def test_terminal_dominates_at_low_growth(self):
        from analysis.dcf import compute_dcf

        result = compute_dcf(
            fcf_cr=1000,
            growth_rate=2.0,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
        )
        # Low growth → terminal value is a larger % of EV
        assert result.terminal_pct > 50


class TestFCFQuality:
    def test_fcf_quality_check(self):
        from analysis.dcf import check_fcf_quality

        result = check_fcf_quality(
            fcf=1000,
            operating_cashflow=1200,
            capex=-200,
            prev_capex=-300,
        )
        assert "quality" in result
        assert result["quality"] in ("HIGH", "MEDIUM", "LOW")

    def test_high_quality_fcf(self):
        from analysis.dcf import check_fcf_quality

        result = check_fcf_quality(
            fcf=1100,
            operating_cashflow=1200,
            capex=-100,
            prev_capex=-100,  # stable capex, FCF ~92% of OCF
        )
        assert result["quality"] == "HIGH"

    def test_low_quality_declining_capex(self):
        from analysis.dcf import check_fcf_quality

        result = check_fcf_quality(
            fcf=1000,
            operating_cashflow=1200,
            capex=-100,
            prev_capex=-500,  # capex dropped 80% — FCF inflated
        )
        assert result["quality"] == "LOW"


# ── Phase 2: Bank P/BV Model ─────────────────────────────────


class TestBankValuation:
    def test_detect_bank(self):
        from analysis.dcf import is_bank_stock

        assert is_bank_stock("Financial Services", "Banks—Regional") is True
        assert is_bank_stock("Technology", "Software") is False
        assert is_bank_stock("Financial Services", "Insurance") is False

    def test_bank_pbv_model(self):
        from analysis.dcf import compute_bank_pbv

        result = compute_bank_pbv(
            book_value_per_share=500.0,
            roe=15.0,
            cost_of_equity=13.5,
            current_price=800.0,
        )
        assert result["justified_pbv"] > 0
        assert result["fair_value"] > 0
        assert "verdict" in result

    def test_bank_high_roe_premium(self):
        from analysis.dcf import compute_bank_pbv

        low_roe = compute_bank_pbv(book_value_per_share=500, roe=10.0, cost_of_equity=13.5)
        high_roe = compute_bank_pbv(book_value_per_share=500, roe=20.0, cost_of_equity=13.5)
        assert high_roe["fair_value"] > low_roe["fair_value"]


# ── Phase 4: Multi-scenario ──────────────────────────────────


class TestMultiScenario:
    def test_scenarios_returns_three(self):
        from analysis.dcf import compute_scenarios

        result = compute_scenarios(
            fcf_cr=1000,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            base_growth=10.0,
        )
        assert "bull" in result
        assert "base" in result
        assert "bear" in result

    def test_bull_higher_than_bear(self):
        from analysis.dcf import compute_scenarios

        result = compute_scenarios(
            fcf_cr=1000,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            base_growth=10.0,
        )
        assert result["bull"]["intrinsic_value"] > result["base"]["intrinsic_value"]
        assert result["base"]["intrinsic_value"] > result["bear"]["intrinsic_value"]

    def test_scenarios_have_labels(self):
        from analysis.dcf import compute_scenarios

        result = compute_scenarios(
            fcf_cr=1000,
            wacc=12.0,
            shares_outstanding=100_000_000,
            net_debt_cr=0,
            base_growth=10.0,
        )
        assert result["bull"]["label"] == "Bull"
        assert result["bear"]["label"] == "Bear"
