"""
Tests for percentage-based position sizing (#157).
"""

from __future__ import annotations

import pytest


class TestSizeByPct:
    def test_basic_pct_calculation(self):
        from engine.trade_executor import size_by_pct

        # 5% of ₹1,00,000 at ₹1,400 = ₹5,000 / ₹1,400 = 3.57 → floor to 3
        qty = size_by_pct("INFY", 5.0, 100_000, limit_price=1400.0)
        assert qty == 3

    def test_10pct_of_100k_at_500(self):
        from engine.trade_executor import size_by_pct

        # 10% of ₹1,00,000 at ₹500 = ₹10,000 / ₹500 = 20
        qty = size_by_pct("INFY", 10.0, 100_000, limit_price=500.0)
        assert qty == 20

    def test_returns_integer(self):
        from engine.trade_executor import size_by_pct

        qty = size_by_pct("INFY", 2.5, 100_000, limit_price=1000.0)
        assert isinstance(qty, int)

    def test_zero_quantity_raises(self):
        from engine.trade_executor import size_by_pct

        # 1% of ₹1,000 at ₹50,000 = ₹10 / ₹50,000 → 0 shares → error
        with pytest.raises(ValueError, match="too small"):
            size_by_pct("INFY", 1.0, 1_000, limit_price=50_000.0)

    def test_exceeds_max_position_pct_raises(self, monkeypatch):
        from engine.trade_executor import size_by_pct

        monkeypatch.setenv("MAX_POSITION_PCT", "20")
        with pytest.raises(ValueError, match="exceeds"):
            size_by_pct("INFY", 25.0, 100_000, limit_price=1000.0)

    def test_exactly_at_max_position_pct_ok(self, monkeypatch):
        from engine.trade_executor import size_by_pct

        monkeypatch.setenv("MAX_POSITION_PCT", "20")
        # 20% of ₹1,00,000 at ₹1,000 = 20 shares
        qty = size_by_pct("INFY", 20.0, 100_000, limit_price=1000.0)
        assert qty == 20

    def test_100pct_with_no_limit_cap(self, monkeypatch):
        from engine.trade_executor import size_by_pct

        monkeypatch.delenv("MAX_POSITION_PCT", raising=False)
        # Without MAX_POSITION_PCT env, default cap is 100%
        qty = size_by_pct("INFY", 50.0, 100_000, limit_price=1000.0)
        assert qty == 50


class TestGetTradingCapital:
    def test_default_is_100k(self, monkeypatch):
        from engine.trade_executor import get_trading_capital

        monkeypatch.delenv("TRADING_CAPITAL", raising=False)
        assert get_trading_capital() == 100_000

    def test_reads_from_env(self, monkeypatch):
        from engine.trade_executor import get_trading_capital

        monkeypatch.setenv("TRADING_CAPITAL", "500000")
        assert get_trading_capital() == 500_000

    def test_float_env_value(self, monkeypatch):
        from engine.trade_executor import get_trading_capital

        monkeypatch.setenv("TRADING_CAPITAL", "250000.50")
        assert get_trading_capital() == 250_000.50


class TestParsePctArg:
    def test_pct_string_detected(self):
        from engine.trade_executor import parse_qty_or_pct

        qty, is_pct = parse_qty_or_pct("5%")
        assert is_pct is True
        assert qty == 5.0

    def test_integer_string_not_pct(self):
        from engine.trade_executor import parse_qty_or_pct

        qty, is_pct = parse_qty_or_pct("100")
        assert is_pct is False
        assert qty == 100

    def test_float_pct(self):
        from engine.trade_executor import parse_qty_or_pct

        qty, is_pct = parse_qty_or_pct("2.5%")
        assert is_pct is True
        assert qty == 2.5

    def test_zero_pct_raises(self):
        from engine.trade_executor import parse_qty_or_pct

        with pytest.raises(ValueError):
            parse_qty_or_pct("0%")

    def test_negative_pct_raises(self):
        from engine.trade_executor import parse_qty_or_pct

        with pytest.raises(ValueError):
            parse_qty_or_pct("-5%")
