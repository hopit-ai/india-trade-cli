"""
Tests for vectorized backtesting engine (#158).
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _make_ohlcv(n=252, seed=42) -> pd.DataFrame:
    """Generate synthetic OHLCV daily data for testing."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    close = 1000.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, size=n))
    high = close * (1 + rng.uniform(0, 0.02, size=n))
    low = close * (1 - rng.uniform(0, 0.02, size=n))
    open_ = close * (1 + rng.normal(0, 0.005, size=n))
    volume = rng.integers(100_000, 1_000_000, size=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


class TestModuleExists:
    def test_module_importable(self):
        from engine.backtest_vectorized import run_vectorized_backtest

        assert callable(run_vectorized_backtest)

    def test_function_signature(self):
        from engine.backtest_vectorized import run_vectorized_backtest
        import inspect

        sig = inspect.signature(run_vectorized_backtest)
        params = set(sig.parameters)
        assert "symbol" in params
        assert "strategy_name" in params


class TestVectorizedEngine:
    def test_rsi_returns_backtest_result(self):
        from engine.backtest_vectorized import vectorized_backtest
        from engine.backtest import BacktestResult

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
        assert isinstance(result, BacktestResult)

    def test_macd_returns_backtest_result(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="macd", symbol="TEST")
        assert result.strategy_name == "macd"

    def test_bollinger_strategy(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="bollinger", symbol="TEST")
        assert result.total_trades >= 0

    def test_ma_cross_strategy(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="ma", symbol="TEST")
        assert result.total_trades >= 0

    def test_returns_correct_symbol(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="INFY")
        assert result.symbol == "INFY"

    def test_equity_curve_starts_near_100(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
        assert result.equity_curve is not None
        assert len(result.equity_curve) > 0
        # Starts near 100 (normalised)
        assert 95 <= result.equity_curve[0] <= 105

    def test_sharpe_ratio_is_finite(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
        import math
        assert math.isfinite(result.sharpe_ratio)

    def test_win_rate_between_0_and_100(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
        assert 0 <= result.win_rate <= 100

    def test_buy_hold_return_is_set(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="rsi", symbol="TEST")
        # Buy & hold return = (last_close / first_close - 1) * 100
        expected_bh = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        assert abs(result.buy_hold_return - expected_bh) < 0.1

    def test_unknown_strategy_falls_back_to_rsi(self):
        from engine.backtest_vectorized import vectorized_backtest

        df = _make_ohlcv()
        result = vectorized_backtest(df, strategy_name="unknown_strategy", symbol="TEST")
        assert result is not None  # shouldn't raise


class TestRunVectorizedBacktest:
    def test_raises_on_unknown_symbol_gracefully(self, monkeypatch):
        """When market data fetch fails, should raise, not hang."""
        import engine.backtest_vectorized as bv_mod

        monkeypatch.setattr(bv_mod, "_fetch_ohlcv", lambda *a, **k: pd.DataFrame())

        with pytest.raises(Exception):
            bv_mod.run_vectorized_backtest("FAKENSTOCK", "rsi", "1y")


class TestFastFlagIntegration:
    def test_backtest_module_has_fast_param(self):
        """Verify run_vectorized_backtest is the entry point used by --fast flag."""
        from engine.backtest_vectorized import run_vectorized_backtest
        import inspect

        sig = inspect.signature(run_vectorized_backtest)
        # Should accept symbol, strategy_name, period
        params = set(sig.parameters)
        assert "symbol" in params
        assert "period" in params
