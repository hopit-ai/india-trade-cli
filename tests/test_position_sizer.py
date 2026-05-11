"""
tests/test_position_sizer.py
─────────────────────────────
Tests for engine/position_sizer.py — VolatilityAdjustedSizer and compute_portfolio_var.

All get_ohlcv calls are mocked; no real network calls.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from engine.position_sizer import (
    PositionSizeResult,
    VolatilityAdjustedSizer,
    compute_portfolio_var,
)


# ── Helpers ─────────────────────────────────────────────────────


def _make_ohlcv(n: int = 252, seed: int = 42, base: float = 100.0) -> pd.DataFrame:
    """Generate deterministic OHLCV DataFrame (daily)."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    returns = np.random.randn(n) * 0.01  # ~1% daily vol
    close = base * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.005)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.005)
    opn = close * (1 + np.random.randn(n) * 0.002)
    volume = np.random.randint(100_000, 1_000_000, n).astype(float)
    return pd.DataFrame(
        {"open": opn, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def _make_correlated_ohlcv(
    n: int = 252, seed: int = 0, base: float = 100.0, corr_factor: float = 0.0
) -> pd.DataFrame:
    """OHLCV where close is partly driven by a shared factor (for correlation tests)."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    common = np.random.randn(n) * 0.01
    idio = np.random.randn(n) * 0.01
    returns = corr_factor * common + (1 - corr_factor) * idio
    close = base * np.cumprod(1 + returns)
    high = close * 1.005
    low = close * 0.995
    opn = close
    volume = np.ones(n) * 500_000
    return pd.DataFrame(
        {"open": opn, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ── PositionSizeResult ───────────────────────────────────────────


class TestPositionSizeResult:
    def test_construction(self):
        result = PositionSizeResult(
            symbol="RELIANCE",
            recommended_qty=10,
            recommended_value=25000.0,
            position_pct=0.05,
            volatility_scalar=0.8,
            correlation_penalty=0.1,
            kelly_fraction=0.15,
            rationale="Test rationale",
        )
        assert result.symbol == "RELIANCE"
        assert result.recommended_qty == 10
        assert result.recommended_value == 25000.0
        assert result.position_pct == 0.05
        assert result.volatility_scalar == 0.8
        assert result.correlation_penalty == 0.1
        assert result.kelly_fraction == 0.15
        assert result.rationale == "Test rationale"

    def test_zero_qty_allowed(self):
        result = PositionSizeResult(
            symbol="INFY",
            recommended_qty=0,
            recommended_value=0.0,
            position_pct=0.0,
            volatility_scalar=0.25,
            correlation_penalty=0.0,
            kelly_fraction=0.0,
            rationale="No position",
        )
        assert result.recommended_qty == 0
        assert result.recommended_value == 0.0


# ── VolatilityAdjustedSizer construction ────────────────────────


class TestVolatilityAdjustedSizerInit:
    def test_defaults(self):
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        assert sizer.total_capital == 500_000
        assert sizer.max_position_pct == 0.10
        assert sizer.target_risk_pct == 0.01

    def test_custom_params(self):
        sizer = VolatilityAdjustedSizer(
            total_capital=1_000_000,
            max_position_pct=0.05,
            target_risk_pct=0.02,
        )
        assert sizer.max_position_pct == 0.05
        assert sizer.target_risk_pct == 0.02


# ── Kelly fraction calculation ───────────────────────────────────


class TestKellyFraction:
    """
    Kelly formula used: f = (win_rate / avg_loss_pct) - ((1 - win_rate) / avg_win_pct)
    Half-Kelly cap applied.
    """

    def _kelly(self, win_rate, avg_win_pct, avg_loss_pct):
        return win_rate / avg_loss_pct - (1 - win_rate) / avg_win_pct

    def test_positive_kelly(self):
        """60% win rate, 5% avg win, 3% avg loss → positive Kelly."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000)
        raw_kelly = self._kelly(0.6, 0.05, 0.03)
        assert raw_kelly > 0

        result = sizer.size_position(
            symbol="TEST",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.02,
        )
        # Half-Kelly applied: kelly_fraction in result should be ≤ raw_kelly/2
        assert result.kelly_fraction <= raw_kelly / 2 + 1e-9

    def test_negative_kelly_gives_zero_position(self):
        """Negative Kelly (bad edge) → recommended_qty = 0."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000)
        result = sizer.size_position(
            symbol="TEST",
            win_rate=0.3,
            avg_win_pct=0.02,
            avg_loss_pct=0.10,
            atr_pct=0.02,
        )
        assert result.recommended_qty == 0
        assert result.kelly_fraction <= 0

    def test_win_rate_zero_gives_zero_position(self):
        """win_rate=0 → Kelly is fully negative → no position."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000)
        result = sizer.size_position(
            symbol="TEST",
            win_rate=0.0,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.02,
        )
        assert result.recommended_qty == 0

    def test_win_rate_one_gives_positive_position(self):
        """win_rate=1 → only win term, no loss term → positive Kelly."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000)
        result = sizer.size_position(
            symbol="TEST",
            win_rate=1.0,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.02,
        )
        assert result.kelly_fraction > 0


# ── Volatility scalar ────────────────────────────────────────────


class TestVolatilityScalar:
    def test_high_atr_reduces_size(self):
        """High ATR % → volatility_scalar < 1 → smaller position."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000, target_risk_pct=0.01)
        result_low = sizer.size_position(
            symbol="A", win_rate=0.6, avg_win_pct=0.05, avg_loss_pct=0.03, atr_pct=0.01
        )
        result_high = sizer.size_position(
            symbol="A", win_rate=0.6, avg_win_pct=0.05, avg_loss_pct=0.03, atr_pct=0.05
        )
        assert result_high.volatility_scalar < result_low.volatility_scalar
        assert result_high.recommended_qty <= result_low.recommended_qty

    def test_scalar_capped_at_2(self):
        """Very low ATR → scalar should be capped at 2.0."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000, target_risk_pct=0.01)
        result = sizer.size_position(
            symbol="A",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.0001,  # extremely low ATR
        )
        assert result.volatility_scalar <= 2.0

    def test_scalar_floor_at_025(self):
        """Very high ATR → scalar should be at least 0.25."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000, target_risk_pct=0.01)
        result = sizer.size_position(
            symbol="A",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.50,  # extremely high ATR
        )
        assert result.volatility_scalar >= 0.25

    def test_zero_atr_does_not_crash(self):
        """ATR of 0 should not raise an exception; result should be valid."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000)
        result = sizer.size_position(
            symbol="A",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.0,
        )
        # Should not crash and volatility_scalar should be at its max cap
        assert result.volatility_scalar <= 2.0
        assert result.recommended_qty >= 0


# ── Position cap ─────────────────────────────────────────────────


class TestPositionCap:
    def test_position_capped_at_max_pct(self):
        """Position must never exceed max_position_pct of capital."""
        sizer = VolatilityAdjustedSizer(total_capital=100_000, max_position_pct=0.10)
        result = sizer.size_position(
            symbol="BIGSYM",
            win_rate=0.99,
            avg_win_pct=0.20,
            avg_loss_pct=0.01,
            atr_pct=0.001,  # very low ATR → huge scalar
            lot_size=1,
        )
        assert result.position_pct <= 0.10 + 1e-9

    def test_custom_max_pct_respected(self):
        """Custom 5% cap must be honored."""
        sizer = VolatilityAdjustedSizer(total_capital=1_000_000, max_position_pct=0.05)
        result = sizer.size_position(
            symbol="SYM",
            win_rate=0.9,
            avg_win_pct=0.10,
            avg_loss_pct=0.01,
            atr_pct=0.001,
        )
        assert result.position_pct <= 0.05 + 1e-9


# ── Lot size rounding ────────────────────────────────────────────


class TestLotSizeRounding:
    def test_lot_size_respected(self):
        """Qty must be a multiple of lot_size."""
        sizer = VolatilityAdjustedSizer(total_capital=1_000_000)
        for lot in [1, 25, 50, 75]:
            result = sizer.size_position(
                symbol="NIFTY",
                win_rate=0.6,
                avg_win_pct=0.05,
                avg_loss_pct=0.03,
                atr_pct=0.02,
                lot_size=lot,
            )
            if result.recommended_qty > 0:
                assert result.recommended_qty % lot == 0


# ── Correlation penalty ──────────────────────────────────────────


class TestCorrelationPenalty:
    def _make_patch(self, corr_factor: float):
        """Return a mock for get_ohlcv that uses shared + idiosyncratic returns."""
        common_ret = np.random.RandomState(0).randn(252) * 0.01

        def fake_get_ohlcv(symbol, *args, **kwargs):
            np.random.seed(hash(symbol) % 2**32 % 10000)
            idio = np.random.randn(252) * 0.01
            returns = corr_factor * common_ret + (1 - corr_factor) * idio
            close = 100 * np.cumprod(1 + returns)
            dates = pd.date_range("2024-01-01", periods=252, freq="B")
            return pd.DataFrame(
                {
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": np.ones(252) * 1e6,
                },
                index=dates,
            )

        return fake_get_ohlcv

    def test_high_correlation_reduces_size(self):
        """With highly correlated existing positions, penalty should reduce size."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)

        # Low correlation case
        with patch("engine.position_sizer.get_ohlcv", self._make_patch(0.1)):
            result_low_corr = sizer.size_position(
                symbol="NEWSTOCK",
                win_rate=0.6,
                avg_win_pct=0.05,
                avg_loss_pct=0.03,
                atr_pct=0.02,
                existing_symbols=["EXISTING1", "EXISTING2"],
            )

        # High correlation case
        with patch("engine.position_sizer.get_ohlcv", self._make_patch(0.95)):
            result_high_corr = sizer.size_position(
                symbol="NEWSTOCK",
                win_rate=0.6,
                avg_win_pct=0.05,
                avg_loss_pct=0.03,
                atr_pct=0.02,
                existing_symbols=["EXISTING1", "EXISTING2"],
            )

        # High corr → bigger penalty → smaller size
        assert result_high_corr.correlation_penalty >= result_low_corr.correlation_penalty
        assert result_high_corr.recommended_qty <= result_low_corr.recommended_qty

    def test_no_existing_symbols_zero_penalty(self):
        """Without existing_symbols, correlation_penalty must be 0."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        result = sizer.size_position(
            symbol="STOCK",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.02,
            existing_symbols=None,
        )
        assert result.correlation_penalty == 0.0

    def test_empty_existing_symbols_zero_penalty(self):
        """Empty list of existing_symbols → no penalty."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        result = sizer.size_position(
            symbol="STOCK",
            win_rate=0.6,
            avg_win_pct=0.05,
            avg_loss_pct=0.03,
            atr_pct=0.02,
            existing_symbols=[],
        )
        assert result.correlation_penalty == 0.0

    def test_penalty_range(self):
        """Correlation penalty must be in [0, 1]."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)

        def fake_get_ohlcv(symbol, *args, **kwargs):
            return _make_ohlcv(seed=hash(symbol) % 9999)

        with patch("engine.position_sizer.get_ohlcv", fake_get_ohlcv):
            result = sizer.size_position(
                symbol="NEWSTOCK",
                win_rate=0.6,
                avg_win_pct=0.05,
                avg_loss_pct=0.03,
                atr_pct=0.02,
                existing_symbols=["A", "B"],
            )
        assert 0.0 <= result.correlation_penalty <= 1.0


# ── compute_correlation_matrix ───────────────────────────────────


class TestComputeCorrelationMatrix:
    def test_matrix_shape(self):
        """Matrix should be n×n for n symbols."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        symbols = ["A", "B", "C"]

        def fake_get_ohlcv(symbol, *args, **kwargs):
            return _make_ohlcv(seed=ord(symbol[0]))

        with patch("engine.position_sizer.get_ohlcv", fake_get_ohlcv):
            corr = sizer.compute_correlation_matrix(symbols)

        assert corr.shape == (3, 3)
        assert list(corr.columns) == symbols
        assert list(corr.index) == symbols

    def test_diagonal_is_one(self):
        """Diagonal of correlation matrix must be 1.0."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        symbols = ["X", "Y"]

        def fake_get_ohlcv(symbol, *args, **kwargs):
            return _make_ohlcv(seed=ord(symbol[0]))

        with patch("engine.position_sizer.get_ohlcv", fake_get_ohlcv):
            corr = sizer.compute_correlation_matrix(symbols)

        for sym in symbols:
            assert abs(corr.loc[sym, sym] - 1.0) < 1e-9

    def test_matrix_symmetric(self):
        """Correlation matrix must be symmetric."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        symbols = ["P", "Q", "R"]

        def fake_get_ohlcv(symbol, *args, **kwargs):
            return _make_ohlcv(seed=ord(symbol[0]))

        with patch("engine.position_sizer.get_ohlcv", fake_get_ohlcv):
            corr = sizer.compute_correlation_matrix(symbols)

        for i, s1 in enumerate(symbols):
            for s2 in symbols[i + 1 :]:
                assert abs(corr.loc[s1, s2] - corr.loc[s2, s1]) < 1e-9

    def test_highly_correlated_symbols(self):
        """Identical return series → correlation = 1.0."""
        sizer = VolatilityAdjustedSizer(total_capital=500_000)
        df_identical = _make_ohlcv(seed=7)

        def fake_get_ohlcv(symbol, *args, **kwargs):
            return df_identical.copy()

        with patch("engine.position_sizer.get_ohlcv", fake_get_ohlcv):
            corr = sizer.compute_correlation_matrix(["X", "Y"])

        # Off-diagonal should be ~1.0 for identical series
        assert abs(corr.loc["X", "Y"] - 1.0) < 1e-6


# ── compute_portfolio_var ────────────────────────────────────────


class TestComputePortfolioVar:
    def _fake_get_ohlcv(self, symbol, *args, **kwargs):
        return _make_ohlcv(seed=hash(symbol) % 9999)

    def test_returns_required_keys(self):
        """Result dict must contain var_1day, var_10day, cvar, volatility_annual."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(
                symbols=["RELIANCE", "INFY"],
                weights=[0.5, 0.5],
            )
        assert "var_1day" in result
        assert "var_10day" in result
        assert "cvar" in result
        assert "volatility_annual" in result

    def test_var_10day_larger_than_1day(self):
        """10-day VaR must be ≥ 1-day VaR (square-root-of-time rule)."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(
                symbols=["A", "B"],
                weights=[0.6, 0.4],
            )
        assert result["var_10day"] >= result["var_1day"]

    def test_cvar_larger_than_var(self):
        """CVaR (expected shortfall) must be ≥ VaR at the same confidence level."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(
                symbols=["C", "D"],
                weights=[0.5, 0.5],
                confidence=0.95,
            )
        assert result["cvar"] >= result["var_1day"]

    def test_single_symbol(self):
        """Single-symbol portfolio should still work."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(symbols=["SOLO"], weights=[1.0])
        assert result["var_1day"] >= 0.0
        assert result["volatility_annual"] > 0.0

    def test_values_are_positive(self):
        """VaR, CVaR, and annualized vol should all be non-negative."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(
                symbols=["E", "F"],
                weights=[0.4, 0.6],
            )
        assert result["var_1day"] >= 0
        assert result["var_10day"] >= 0
        assert result["cvar"] >= 0
        assert result["volatility_annual"] >= 0

    def test_custom_confidence(self):
        """99% confidence VaR should be larger than 95% confidence VaR."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            r95 = compute_portfolio_var(["G", "H"], [0.5, 0.5], confidence=0.95)
            r99 = compute_portfolio_var(["G", "H"], [0.5, 0.5], confidence=0.99)
        assert r99["var_1day"] >= r95["var_1day"]

    def test_returns_dict(self):
        """Return type must be a dict."""
        with patch("engine.position_sizer.get_ohlcv", self._fake_get_ohlcv):
            result = compute_portfolio_var(["I"], [1.0])
        assert isinstance(result, dict)
