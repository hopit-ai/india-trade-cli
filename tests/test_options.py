"""Tests for analysis/options.py — Greeks, IV rank, payoff."""

import pytest

from analysis.options import iv_rank, payoff, PayoffLeg


class TestIVRank:
    def test_at_low(self):
        """Current IV at historical low → rank 0."""
        assert iv_rank(10.0, [10.0, 20.0, 30.0, 40.0]) == pytest.approx(0.0)

    def test_at_high(self):
        """Current IV at historical high → rank 100."""
        assert iv_rank(40.0, [10.0, 20.0, 30.0, 40.0]) == pytest.approx(100.0)

    def test_at_midpoint(self):
        """Current IV at midpoint → rank 50."""
        assert iv_rank(25.0, [10.0, 40.0]) == pytest.approx(50.0)

    def test_empty_history(self):
        """No historical data → default 50."""
        assert iv_rank(20.0, []) == pytest.approx(50.0)

    def test_flat_history(self):
        """All same IVs → default 50."""
        assert iv_rank(20.0, [20.0, 20.0, 20.0]) == pytest.approx(50.0)


class TestPayoff:
    def test_single_long_call(self):
        """Long call: max loss = premium, profit unlimited above breakeven."""
        legs = [
            PayoffLeg(
                option_type="CE",
                transaction="BUY",
                strike=100.0,
                premium=5.0,
                lot_size=1,
                lots=1,
            )
        ]
        result = payoff(legs, spot_range=(80, 120), steps=40)
        assert result.max_loss == pytest.approx(-5.0, abs=0.5)
        assert result.max_profit > 0
        # Breakeven should be at strike + premium = 105
        assert any(abs(be - 105.0) < 2.0 for be in result.breakevens)

    def test_single_long_put(self):
        """Long put: max loss = premium."""
        legs = [
            PayoffLeg(
                option_type="PE",
                transaction="BUY",
                strike=100.0,
                premium=5.0,
                lot_size=1,
                lots=1,
            )
        ]
        result = payoff(legs, spot_range=(80, 120), steps=40)
        assert result.max_loss == pytest.approx(-5.0, abs=0.5)

    def test_iron_condor_four_legs(self):
        """Iron condor should have defined max profit and max loss."""
        legs = [
            PayoffLeg("PE", "SELL", 90.0, 3.0, 1, 1),  # sell put
            PayoffLeg("PE", "BUY", 85.0, 1.5, 1, 1),  # buy put (protection)
            PayoffLeg("CE", "SELL", 110.0, 3.0, 1, 1),  # sell call
            PayoffLeg("CE", "BUY", 115.0, 1.5, 1, 1),  # buy call (protection)
        ]
        result = payoff(legs, spot_range=(80, 120), steps=40)
        # Max profit = net premium collected = (3-1.5) + (3-1.5) = 3.0
        assert result.max_profit > 0
        # Max loss should be bounded (not infinite)
        assert result.max_loss > -10.0
