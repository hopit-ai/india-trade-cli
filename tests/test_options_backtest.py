"""Tests for engine/options_backtest.py — options-specific backtesting.

Written BEFORE the implementation (TDD). Tests define the spec.
"""

import math
import numpy as np
import pandas as pd
import pytest
from datetime import date, timedelta


# ── Premium estimation tests ─────────────────────────────────

class TestBSPremium:
    """Black-Scholes premium estimation must produce reasonable values."""

    def test_atm_call_premium_positive(self):
        from engine.options_backtest import bs_premium
        # ATM call: spot=100, strike=100, 30 days, 20% IV
        premium = bs_premium(100.0, 100.0, 30, 0.20, "CE")
        assert premium > 0
        assert premium < 10  # ATM 30-day 20% IV shouldn't be > 10% of spot

    def test_atm_put_premium_positive(self):
        from engine.options_backtest import bs_premium
        premium = bs_premium(100.0, 100.0, 30, 0.20, "PE")
        assert premium > 0

    def test_deep_itm_call(self):
        from engine.options_backtest import bs_premium
        # Deep ITM: spot=120, strike=100, should be ~20 + time value
        premium = bs_premium(120.0, 100.0, 30, 0.20, "CE")
        assert premium > 20  # at least intrinsic value

    def test_deep_otm_call_near_zero(self):
        from engine.options_backtest import bs_premium
        # Deep OTM: spot=80, strike=100
        premium = bs_premium(80.0, 100.0, 30, 0.20, "CE")
        assert premium < 1  # near zero

    def test_higher_iv_higher_premium(self):
        from engine.options_backtest import bs_premium
        low_iv = bs_premium(100.0, 100.0, 30, 0.15, "CE")
        high_iv = bs_premium(100.0, 100.0, 30, 0.40, "CE")
        assert high_iv > low_iv

    def test_more_dte_higher_premium(self):
        from engine.options_backtest import bs_premium
        short = bs_premium(100.0, 100.0, 7, 0.20, "CE")
        long = bs_premium(100.0, 100.0, 60, 0.20, "CE")
        assert long > short

    def test_zero_dte_intrinsic_only(self):
        from engine.options_backtest import bs_premium
        # At expiry: premium ≈ intrinsic value
        itm = bs_premium(110.0, 100.0, 0, 0.20, "CE")
        assert itm == pytest.approx(10.0, abs=0.5)
        otm = bs_premium(90.0, 100.0, 0, 0.20, "CE")
        assert otm == pytest.approx(0.0, abs=0.5)


# ── Strategy logic tests ─────────────────────────────────────

class TestStraddleStrategy:
    def test_entry_before_expiry(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy(entry_dte=3)
        # Should enter when DTE <= 3
        legs = s.should_enter(date.today(), spot=100, iv=0.20, dte=3, vix=15)
        assert legs is not None
        assert len(legs) == 2  # CE + PE

    def test_no_entry_far_from_expiry(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy(entry_dte=3)
        legs = s.should_enter(date.today(), spot=100, iv=0.20, dte=10, vix=15)
        assert legs is None

    def test_legs_are_atm(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy()
        legs = s.should_enter(date.today(), spot=22500, iv=0.20, dte=2, vix=15)
        assert legs is not None
        # Both legs should be ATM (strike_offset = 0)
        for leg in legs:
            assert leg["strike_offset"] == 0

    def test_exit_on_expiry(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy()
        assert s.should_exit(date.today(), spot=100, iv=0.20, dte=0,
                             entry_spot=100, days_held=3, unrealised_pnl=-50) is True

    def test_exit_on_stop_loss(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy(stop_loss_pct=50)
        # 60% loss should trigger stop
        assert s.should_exit(date.today(), spot=100, iv=0.20, dte=2,
                             entry_spot=100, days_held=1, unrealised_pnl=-60) is True

    def test_no_exit_within_threshold(self):
        from engine.options_backtest import StraddleStrategy
        s = StraddleStrategy(stop_loss_pct=50)
        # 30% loss should NOT trigger stop
        assert s.should_exit(date.today(), spot=100, iv=0.20, dte=2,
                             entry_spot=100, days_held=1, unrealised_pnl=-30) is False


class TestIronCondorStrategy:
    def test_entry_returns_four_legs(self):
        from engine.options_backtest import IronCondorStrategy
        s = IronCondorStrategy(wing_width=100)
        legs = s.should_enter(date.today(), spot=22500, iv=0.20, dte=5, vix=15)
        assert legs is not None
        assert len(legs) == 4  # sell CE, buy CE, sell PE, buy PE

    def test_legs_structure(self):
        from engine.options_backtest import IronCondorStrategy
        s = IronCondorStrategy(wing_width=100, short_offset=200)
        legs = s.should_enter(date.today(), spot=22500, iv=0.20, dte=5, vix=15)
        # Check we have 2 sells and 2 buys
        sells = [l for l in legs if l["transaction"] == "SELL"]
        buys = [l for l in legs if l["transaction"] == "BUY"]
        assert len(sells) == 2
        assert len(buys) == 2

    def test_no_entry_high_vix(self):
        from engine.options_backtest import IronCondorStrategy
        s = IronCondorStrategy(max_vix=25)
        legs = s.should_enter(date.today(), spot=22500, iv=0.20, dte=5, vix=30)
        assert legs is None  # VIX too high


# ── Backtester integration tests ─────────────────────────────

class TestOptionsBacktester:
    def _make_data(self, n=100, start_price=22000):
        """Create synthetic spot + VIX data for testing."""
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=n, freq="B")
        prices = start_price + np.cumsum(np.random.randn(n) * 100)
        vix = 15 + np.random.randn(n) * 3
        vix = np.clip(vix, 10, 35)

        spot_df = pd.DataFrame({
            "open": prices + np.random.randn(n) * 20,
            "high": prices + np.abs(np.random.randn(n)) * 50,
            "low": prices - np.abs(np.random.randn(n)) * 50,
            "close": prices,
            "volume": np.random.randint(1_000_000, 10_000_000, n),
        }, index=dates)

        vix_df = pd.DataFrame({"close": vix}, index=dates)
        return spot_df, vix_df

    def test_straddle_backtest_runs(self):
        from engine.options_backtest import OptionsBacktester, StraddleStrategy

        spot, vix = self._make_data()
        bt = OptionsBacktester("NIFTY", lot_size=25)
        bt._spot_data = spot
        bt._vix_data = vix
        result = bt.run(StraddleStrategy(entry_dte=3))

        assert result.underlying == "NIFTY"
        assert result.total_trades >= 0
        assert len(result.trades) == result.total_trades

    def test_iron_condor_backtest_runs(self):
        from engine.options_backtest import OptionsBacktester, IronCondorStrategy

        spot, vix = self._make_data()
        bt = OptionsBacktester("NIFTY", lot_size=25)
        bt._spot_data = spot
        bt._vix_data = vix
        result = bt.run(IronCondorStrategy())

        assert result.total_trades >= 0

    def test_zero_trades_no_crash(self):
        """No entry conditions met → 0 trades, no division errors."""
        from engine.options_backtest import OptionsBacktester, IronCondorStrategy

        spot, vix = self._make_data(n=10)
        # Use IronCondorStrategy with max_vix=5 — VIX is always above 5, so no entries
        bt = OptionsBacktester("NIFTY", lot_size=25)
        bt._spot_data = spot
        bt._vix_data = vix
        result = bt.run(IronCondorStrategy(max_vix=5.0))

        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert result.sharpe_ratio == 0.0

    def test_trade_has_legs(self):
        from engine.options_backtest import OptionsBacktester, StraddleStrategy

        spot, vix = self._make_data(n=200)
        bt = OptionsBacktester("NIFTY", lot_size=25)
        bt._spot_data = spot
        bt._vix_data = vix
        result = bt.run(StraddleStrategy(entry_dte=5))

        if result.trades:
            trade = result.trades[0]
            assert len(trade.legs) >= 2
            assert trade.legs[0].option_type in ("CE", "PE")
            assert trade.legs[0].entry_premium > 0

    def test_result_print_no_crash(self):
        from engine.options_backtest import OptionsBacktester, StraddleStrategy

        spot, vix = self._make_data()
        bt = OptionsBacktester("NIFTY", lot_size=25)
        bt._spot_data = spot
        bt._vix_data = vix
        result = bt.run(StraddleStrategy(entry_dte=3))
        # Should not raise
        result.print_summary()
