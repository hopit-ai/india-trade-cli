"""Tests for options analytics: bulk deals, OI profile, IV smile, GEX, scanner.

TDD — written before implementation.
Covers issues #33, #47, #48, #49, #58.
"""

import pandas as pd


# ── #58: Bulk/Block Deals ────────────────────────────────────

class TestBulkDeals:
    def test_classify_entity_fii(self):
        from market.bulk_deals import classify_entity
        assert classify_entity("GOLDMAN SACHS FPI") == "FII"
        assert classify_entity("MORGAN STANLEY ASIA PTE LTD") == "FII"

    def test_classify_entity_mf(self):
        from market.bulk_deals import classify_entity
        assert classify_entity("SBI MUTUAL FUND") == "MF"
        assert classify_entity("HDFC ASSET MANAGEMENT") == "MF"

    def test_classify_entity_insurance(self):
        from market.bulk_deals import classify_entity
        assert classify_entity("LIC OF INDIA") == "DII"

    def test_classify_entity_unknown(self):
        from market.bulk_deals import classify_entity
        assert classify_entity("RANDOM PERSON") == "OTHER"

    def test_get_block_deals_returns_list(self):
        from market.bulk_deals import get_block_deals
        result = get_block_deals()
        assert isinstance(result, list)

    def test_get_bulk_deals_returns_list(self):
        from market.bulk_deals import get_bulk_deals
        result = get_bulk_deals(days=5)
        assert isinstance(result, list)


# ── #49: OI Profile ──────────────────────────────────────────

class TestOIProfile:
    def test_classify_oi_change(self):
        from market.oi_profile import classify_oi_change
        assert classify_oi_change(price_up=True, oi_up=True) == "LONG_BUILDUP"
        assert classify_oi_change(price_up=True, oi_up=False) == "SHORT_COVERING"
        assert classify_oi_change(price_up=False, oi_up=True) == "SHORT_BUILDUP"
        assert classify_oi_change(price_up=False, oi_up=False) == "LONG_UNWINDING"

    def test_find_max_oi_strikes(self):
        from market.oi_profile import find_max_oi_strikes
        chain_data = [
            {"strike": 22000, "ce_oi": 100000, "pe_oi": 500000},
            {"strike": 22500, "ce_oi": 800000, "pe_oi": 200000},
            {"strike": 23000, "ce_oi": 300000, "pe_oi": 100000},
        ]
        max_call, max_put = find_max_oi_strikes(chain_data)
        assert max_call == 22500  # highest CE OI
        assert max_put == 22000   # highest PE OI

    def test_get_oi_profile_returns_dict(self):
        from market.oi_profile import get_oi_profile
        result = get_oi_profile("NIFTY")
        assert isinstance(result, dict)


# ── #47: IV Smile ────────────────────────────────────────────

class TestIVSmile:
    def test_compute_iv_smile_returns_dataframe(self):
        from analysis.volatility_surface import compute_iv_smile
        # May return empty if no broker, but should not crash
        result = compute_iv_smile("NIFTY")
        assert isinstance(result, (pd.DataFrame, type(None)))

    def test_classify_skew(self):
        from analysis.volatility_surface import classify_skew
        # OTM put IV > ATM IV = negative skew (crash protection)
        assert classify_skew(otm_put_iv=25.0, atm_iv=18.0, otm_call_iv=20.0) == "PUT_SKEW"
        # OTM call IV > ATM IV = positive skew (rally expectation)
        assert classify_skew(otm_put_iv=18.0, atm_iv=18.0, otm_call_iv=25.0) == "CALL_SKEW"
        # Symmetric
        assert classify_skew(otm_put_iv=19.0, atm_iv=18.0, otm_call_iv=19.0) == "SYMMETRIC"

    def test_classify_term_structure(self):
        from analysis.volatility_surface import classify_term_structure
        # Near IV < Far IV = contango (normal)
        assert classify_term_structure(near_iv=14.0, far_iv=18.0) == "CONTANGO"
        # Near IV > Far IV = backwardation (event risk)
        assert classify_term_structure(near_iv=22.0, far_iv=16.0) == "BACKWARDATION"
        # Similar = flat
        assert classify_term_structure(near_iv=15.0, far_iv=15.5) == "FLAT"


# ── #48: GEX Analysis ────────────────────────────────────────

class TestGEX:
    def test_compute_gex_per_strike(self):
        from analysis.gex import compute_gex_at_strike
        # Call side: positive GEX (dealers long gamma from selling calls to retail)
        gex_ce = compute_gex_at_strike(
            oi=100000, gamma=0.001, spot=22500, lot_size=25, is_call=True
        )
        assert gex_ce > 0

        # Put side: negative GEX (dealers short gamma from selling puts)
        gex_pe = compute_gex_at_strike(
            oi=100000, gamma=0.001, spot=22500, lot_size=25, is_call=False
        )
        assert gex_pe < 0

    def test_find_gex_flip_point(self):
        from analysis.gex import find_gex_flip
        # Strikes with GEX values transitioning from positive to negative
        gex_by_strike = [
            (22000, 500),
            (22200, 300),
            (22400, 100),
            (22500, -50),
            (22600, -200),
        ]
        flip = find_gex_flip(gex_by_strike)
        assert flip is not None
        assert 22400 <= flip <= 22500

    def test_classify_gex_regime(self):
        from analysis.gex import classify_gex_regime
        assert classify_gex_regime(total_gex=500) == "POSITIVE"    # pinning
        assert classify_gex_regime(total_gex=-300) == "NEGATIVE"   # trending
        assert classify_gex_regime(total_gex=5) == "NEUTRAL"

    def test_get_gex_analysis_returns_dict(self):
        from analysis.gex import get_gex_analysis
        result = get_gex_analysis("NIFTY")
        assert isinstance(result, dict)


# ── #33: Options Scanner ─────────────────────────────────────

class TestOptionsScanner:
    def test_scanner_returns_dict(self):
        from market.options_scanner import scan_options
        # Full scan is slow — just verify it returns correct structure
        result = scan_options(symbols=["NIFTY"], quick=True)
        assert isinstance(result, dict)
        assert "high_iv" in result
        assert "unusual_oi" in result

    def test_filter_high_iv(self):
        from market.options_scanner import filter_high_iv
        stocks = [
            {"symbol": "A", "iv_rank": 85},
            {"symbol": "B", "iv_rank": 40},
            {"symbol": "C", "iv_rank": 72},
        ]
        filtered = filter_high_iv(stocks, threshold=60)
        assert len(filtered) == 2
        assert filtered[0]["symbol"] == "A"  # sorted by IV rank desc

    def test_filter_unusual_oi(self):
        from market.options_scanner import filter_unusual_oi
        strikes = [
            {"strike": 22000, "oi_change_pct": 50},
            {"strike": 22500, "oi_change_pct": 250},
            {"strike": 23000, "oi_change_pct": 30},
        ]
        filtered = filter_unusual_oi(strikes, threshold=100)
        assert len(filtered) == 1
        assert filtered[0]["strike"] == 22500
