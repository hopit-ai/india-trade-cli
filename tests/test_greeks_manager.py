"""Tests for engine/greeks_manager.py — delta hedge, roll suggestions, dashboard.

Written BEFORE the implementation (TDD).
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


# ── Mock PortfolioGreeks for testing without broker ──────────

def _mock_greeks(net_delta=0, net_theta=0, net_vega=0, net_gamma=0, positions=None):
    """Build a mock PortfolioGreeks-like object."""
    from engine.greeks_manager import _PortfolioGreeksLike
    return _PortfolioGreeksLike(
        net_delta=net_delta,
        net_theta=net_theta,
        net_vega=net_vega,
        net_gamma=net_gamma,
        positions_with_greeks=positions or [],
        by_underlying={},
    )


# ── Delta Hedge Tests ────────────────────────────────────────

class TestDeltaHedge:
    def test_positive_delta_suggests_sell(self):
        """Net delta +500 → suggest selling to reduce."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=500, target_delta=0, lot_size=25
        )
        assert result.gap == pytest.approx(-500)
        assert len(result.suggestions) > 0
        assert any(s["action"] == "SELL" for s in result.suggestions)

    def test_negative_delta_suggests_buy(self):
        """Net delta -300 → suggest buying to reduce."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=-300, target_delta=0, lot_size=25
        )
        assert result.gap == pytest.approx(300)
        assert any(s["action"] == "BUY" for s in result.suggestions)

    def test_zero_delta_no_hedge(self):
        """Already delta-neutral → no suggestions."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=0, target_delta=0, lot_size=25
        )
        assert len(result.suggestions) == 0

    def test_small_delta_within_threshold(self):
        """Small delta within tolerance → no hedge needed."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=10, target_delta=0, lot_size=25, tolerance=15
        )
        assert len(result.suggestions) == 0

    def test_custom_target(self):
        """Target delta +100 with current +400 → reduce by 300."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=400, target_delta=100, lot_size=25
        )
        assert result.gap == pytest.approx(-300)

    def test_lot_calculation(self):
        """Gap of 500 with lot_size=25 → ~20 lots of futures."""
        from engine.greeks_manager import compute_delta_hedge
        result = compute_delta_hedge(
            net_delta=500, target_delta=0, lot_size=25
        )
        fut = [s for s in result.suggestions if "FUT" in s.get("instrument", "")]
        if fut:
            assert fut[0]["lots"] == 20  # 500 / 25 = 20


# ── Roll Suggestion Tests ────────────────────────────────────

class TestRollSuggestions:
    def test_expiring_position_suggests_roll(self):
        from engine.greeks_manager import compute_roll_suggestions
        positions = [{
            "symbol": "NIFTY25APR23000CE",
            "underlying": "NIFTY",
            "expiry": (date.today() + timedelta(days=1)).isoformat(),
            "strike": 23000,
            "option_type": "CE",
            "qty": 25,
            "ltp": 50.0,
        }]
        result = compute_roll_suggestions(positions, dte_threshold=3)
        assert len(result) == 1
        assert result[0].current_dte <= 3
        assert result[0].recommendation in ("ROLL", "LET EXPIRE", "CLOSE")

    def test_far_expiry_no_roll(self):
        from engine.greeks_manager import compute_roll_suggestions
        positions = [{
            "symbol": "NIFTY25MAY23000CE",
            "underlying": "NIFTY",
            "expiry": (date.today() + timedelta(days=30)).isoformat(),
            "strike": 23000,
            "option_type": "CE",
            "qty": 25,
            "ltp": 150.0,
        }]
        result = compute_roll_suggestions(positions, dte_threshold=3)
        assert len(result) == 0

    def test_empty_positions(self):
        from engine.greeks_manager import compute_roll_suggestions
        result = compute_roll_suggestions([], dte_threshold=3)
        assert len(result) == 0


# ── Dashboard Tests ──────────────────────────────────────────

class TestGreeksDashboard:
    def test_high_theta_warning(self):
        from engine.greeks_manager import build_dashboard
        dash = build_dashboard(net_delta=50, net_theta=-800, net_vega=200, net_gamma=0.3)
        assert any("theta" in w.lower() or "850" in w or "800" in w for w in dash.warnings)
        assert dash.risk_level in ("MODERATE", "HIGH", "CRITICAL")

    def test_high_delta_warning(self):
        from engine.greeks_manager import build_dashboard
        dash = build_dashboard(net_delta=500, net_theta=-100, net_vega=50, net_gamma=0.1)
        assert any("delta" in w.lower() for w in dash.warnings)

    def test_clean_state_no_warnings(self):
        from engine.greeks_manager import build_dashboard
        dash = build_dashboard(net_delta=10, net_theta=-50, net_vega=20, net_gamma=0.05)
        assert dash.risk_level == "LOW"
        assert len(dash.warnings) == 0

    def test_critical_gamma(self):
        from engine.greeks_manager import build_dashboard
        dash = build_dashboard(net_delta=100, net_theta=-200, net_vega=100, net_gamma=2.0)
        assert any("gamma" in w.lower() for w in dash.warnings)

    def test_dashboard_always_has_actions_for_warnings(self):
        from engine.greeks_manager import build_dashboard
        dash = build_dashboard(net_delta=500, net_theta=-1000, net_vega=500, net_gamma=1.5)
        # If there are warnings, there should be actions
        if dash.warnings:
            assert len(dash.actions) > 0
