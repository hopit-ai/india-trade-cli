"""
Tests for percentage-based position sizing — resolve_position_size (#157).
"""

from __future__ import annotations

import pytest


class TestResolvePositionSizePct:
    """Percentage spec: '5%' → 5% of capital / price."""

    def test_5pct_of_200k_at_1400(self):
        from engine.trade_executor import resolve_position_size

        # 5% of ₹2,00,000 = ₹10,000 / ₹1,400 = 7.14 → 7
        qty = resolve_position_size("5%", capital=200_000, price=1400.0)
        assert qty == 7

    def test_10pct_of_100k_at_500(self):
        from engine.trade_executor import resolve_position_size

        # 10% of ₹1,00,000 = ₹10,000 / ₹500 = 20
        qty = resolve_position_size("10%", capital=100_000, price=500.0)
        assert qty == 20

    def test_returns_int(self):
        from engine.trade_executor import resolve_position_size

        qty = resolve_position_size("5%", capital=100_000, price=1000.0)
        assert isinstance(qty, int)

    def test_zero_pct_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError, match="0"):
            resolve_position_size("0%", capital=100_000, price=1000.0)

    def test_over_100pct_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError, match="100"):
            resolve_position_size("150%", capital=100_000, price=1000.0)

    def test_fractional_pct(self):
        from engine.trade_executor import resolve_position_size

        # 2.5% of ₹1,00,000 = ₹2,500 / ₹500 = 5
        qty = resolve_position_size("2.5%", capital=100_000, price=500.0)
        assert qty == 5

    def test_too_small_pct_raises(self):
        """1% of ₹1,000 at ₹50,000 → can't afford even 1 share."""
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError):
            resolve_position_size("1%", capital=1_000, price=50_000.0)


class TestResolvePositionSizeINR:
    """INR amount spec: '10000' → ₹10,000 / price shares."""

    def test_inr_10000_at_500(self):
        from engine.trade_executor import resolve_position_size

        # ₹10,000 / ₹500 = 20 shares (10000/500=20 ≥ 2 heuristic)
        qty = resolve_position_size("10000", capital=200_000, price=500.0)
        assert qty == 20

    def test_inr_50000_at_1000(self):
        from engine.trade_executor import resolve_position_size

        qty = resolve_position_size("50000", capital=200_000, price=1000.0)
        assert qty == 50

    def test_inr_returns_int(self):
        from engine.trade_executor import resolve_position_size

        qty = resolve_position_size("5000", capital=100_000, price=100.0)
        assert isinstance(qty, int)


class TestResolvePositionSizeShares:
    """Direct share count: '50' → 50 shares."""

    def test_small_number_treated_as_shares(self):
        """When value/price < 2, treat as share count."""
        from engine.trade_executor import resolve_position_size

        # 1 share at ₹1400 → ratio = 1/1400 < 2, treat as shares
        qty = resolve_position_size("1", capital=200_000, price=1400.0)
        assert qty == 1

    def test_50_shares(self):
        from engine.trade_executor import resolve_position_size

        # 50 shares at ₹1400 → ratio = 50/1400 ≈ 0.036 < 2, treat as shares
        qty = resolve_position_size("50", capital=200_000, price=1400.0)
        assert qty == 50


class TestResolvePositionSizeEdgeCases:
    def test_invalid_string_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises((ValueError, Exception)):
            resolve_position_size("abc", capital=100_000, price=1000.0)

    def test_zero_price_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError):
            resolve_position_size("5%", capital=100_000, price=0.0)

    def test_negative_price_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError):
            resolve_position_size("5%", capital=100_000, price=-100.0)

    def test_negative_value_raises(self):
        from engine.trade_executor import resolve_position_size

        with pytest.raises(ValueError):
            resolve_position_size("-50", capital=100_000, price=1000.0)
