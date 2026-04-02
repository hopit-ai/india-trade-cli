"""Tests for engine/backtest.py — strategies, backtester, metrics."""

import numpy as np
import pandas as pd
import pytest

from engine.backtest import (
    Strategy, RSIStrategy, MACrossStrategy, MACDStrategy, BollingerStrategy,
    Backtester, BacktestResult, Trade,
)


class TestRSIStrategy:
    def test_signal_values(self, ohlcv_df):
        """Signals must be in {-1, 0, 1}."""
        s = RSIStrategy(buy_level=30, sell_level=70)
        signals = s.generate_signals(ohlcv_df)
        unique = set(signals.dropna().unique())
        assert unique.issubset({-1, 0, 1})

    def test_signal_length(self, ohlcv_df):
        s = RSIStrategy()
        signals = s.generate_signals(ohlcv_df)
        assert len(signals) == len(ohlcv_df)

    def test_custom_levels(self, ohlcv_df):
        """Wider levels (20/80) should produce fewer signals than default (30/70)."""
        s_wide = RSIStrategy(buy_level=20, sell_level=80)
        s_default = RSIStrategy(buy_level=30, sell_level=70)
        wide_trades = (s_wide.generate_signals(ohlcv_df) != 0).sum()
        default_trades = (s_default.generate_signals(ohlcv_df) != 0).sum()
        assert wide_trades <= default_trades


class TestMACrossStrategy:
    def test_signal_values(self, ohlcv_df):
        s = MACrossStrategy(fast=10, slow=30)
        signals = s.generate_signals(ohlcv_df)
        unique = set(signals.dropna().unique())
        assert unique.issubset({-1, 0, 1})

    def test_generates_at_least_one_signal(self, ohlcv_df):
        """With uptrend + downtrend, should have at least one buy and one sell."""
        s = MACrossStrategy(fast=10, slow=30)
        signals = s.generate_signals(ohlcv_df)
        assert (signals == 1).any(), "No buy signals generated"
        assert (signals == -1).any(), "No sell signals generated"


class TestMACDStrategy:
    def test_signal_values(self, ohlcv_df):
        s = MACDStrategy()
        signals = s.generate_signals(ohlcv_df)
        unique = set(signals.dropna().unique())
        assert unique.issubset({-1, 0, 1})


class TestBollingerStrategy:
    def test_signal_values(self, ohlcv_df):
        s = BollingerStrategy()
        signals = s.generate_signals(ohlcv_df)
        unique = set(signals.dropna().unique())
        assert unique.issubset({-1, 0, 1})


class TestBacktester:
    def test_run_with_mock_data(self, ohlcv_df):
        """Run backtester with injected data (no network)."""
        bt = Backtester("TEST", period="1y")
        bt._df = ohlcv_df  # inject data directly

        result = bt.run(RSIStrategy())
        assert isinstance(result, BacktestResult)
        assert result.symbol == "TEST"
        assert result.total_trades >= 0
        assert len(result.equity_curve) > 0

    def test_zero_trades_no_division_error(self):
        """Flat data → 0 trades → no division by zero."""
        dates = pd.date_range("2025-01-01", periods=50, freq="B")
        flat = pd.DataFrame({
            "open": [100.0] * 50,
            "high": [101.0] * 50,
            "low": [99.0] * 50,
            "close": [100.0] * 50,
            "volume": [1000000] * 50,
        }, index=dates)

        bt = Backtester("FLAT", period="1y")
        bt._df = flat
        result = bt.run(RSIStrategy(buy_level=5, sell_level=95))  # extreme levels → no trades
        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert result.sharpe_ratio == 0.0

    def test_metrics_consistent(self, ohlcv_df):
        """Win + loss trades should sum to total trades."""
        bt = Backtester("TEST", period="1y")
        bt._df = ohlcv_df
        result = bt.run(MACrossStrategy(fast=10, slow=30))
        assert result.winning_trades + result.losing_trades == result.total_trades


class TestBacktestResult:
    def test_print_summary_no_crash(self, ohlcv_df):
        """print_summary should not crash even with edge-case data."""
        bt = Backtester("TEST", period="1y")
        bt._df = ohlcv_df
        result = bt.run(RSIStrategy())
        # Should not raise
        result.print_summary()

    def test_trade_fields(self, ohlcv_df):
        bt = Backtester("TEST", period="1y")
        bt._df = ohlcv_df
        result = bt.run(MACrossStrategy(fast=10, slow=30))
        if result.trades:
            t = result.trades[0]
            assert isinstance(t, Trade)
            assert t.direction in ("LONG", "SHORT")
            assert t.entry_price > 0
            assert t.exit_price > 0
