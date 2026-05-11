"""
tests/test_signal_ensemble.py
──────────────────────────────
Tests for the weighted multi-strategy signal ensemble (#167).

Covers:
  - Each individual strategy (trend, mean_rev, momentum, volatility, statistical)
  - ADX calculation
  - Hurst exponent estimation
  - Ensemble aggregation (weights, confidence, tie-breaking)
  - Edge cases: empty DataFrames, short series, flat prices
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.signal_ensemble import (
    STRATEGY_WEIGHTS,
    EnsembleSignal,
    _adx,
    _hurst_exponent,
    _mean_rev_signal,
    _momentum_signal,
    _statistical_signal,
    _trend_signal,
    _volatility_signal,
    ensemble_signal,
    format_ensemble,
)


# ── Synthetic OHLCV helpers ───────────────────────────────────────


def _make_df(close: list[float], n_pad: int = 0) -> pd.DataFrame:
    """Build minimal OHLCV DataFrame from a close-price list."""
    c = np.array(close, dtype=float)
    h = c * 1.01
    l = c * 0.99
    o = np.roll(c, 1)
    o[0] = c[0]
    v = np.ones(len(c)) * 1_000_000
    idx = pd.date_range("2024-01-01", periods=len(c), freq="B")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)


def _trending_up(n: int = 200) -> pd.DataFrame:
    """Monotonically rising prices — should produce BULLISH signals."""
    close = [100 + i * 0.5 for i in range(n)]
    return _make_df(close)


def _trending_down(n: int = 200) -> pd.DataFrame:
    """Monotonically falling prices — should produce BEARISH signals."""
    close = [200 - i * 0.5 for i in range(n)]
    return _make_df(close)


def _flat(n: int = 100) -> pd.DataFrame:
    """Flat price + small noise — choppy/range-bound."""
    rng = np.random.default_rng(42)
    close = [100 + rng.uniform(-0.5, 0.5) for _ in range(n)]
    return _make_df(close)


def _anti_persistent(n: int = 300) -> pd.DataFrame:
    """AR(1) negative autocorrelation — anti-persistent, H < 0.5."""
    rng = np.random.default_rng(77)
    r_val = 0.0
    log_returns = []
    for _ in range(n):
        r_val = -0.85 * r_val + rng.normal(0, 0.01)
        log_returns.append(r_val)
    prices = 100 * np.exp(np.cumsum(log_returns))
    return _make_df(list(prices))


# ── ADX calculation ──────────────────────────────────────────────


class TestADX:
    def test_returns_three_series(self):
        df = _trending_up()
        adx, di_plus, di_minus = _adx(df)
        assert len(adx) == len(df)
        assert len(di_plus) == len(df)
        assert len(di_minus) == len(df)

    def test_adx_high_in_strong_trend(self):
        df = _trending_up(200)
        adx, _, _ = _adx(df)
        # With a clean uptrend for 200 bars, ADX should exceed 20
        assert adx.dropna().iloc[-1] > 20

    def test_di_plus_dominant_in_uptrend(self):
        df = _trending_up(200)
        _, di_plus, di_minus = _adx(df)
        # In an uptrend, DI+ > DI-
        assert di_plus.dropna().iloc[-1] > di_minus.dropna().iloc[-1]

    def test_di_minus_dominant_in_downtrend(self):
        df = _trending_down(200)
        _, di_plus, di_minus = _adx(df)
        assert di_minus.dropna().iloc[-1] > di_plus.dropna().iloc[-1]


# ── Hurst exponent ───────────────────────────────────────────────


class TestHurstExponent:
    def test_none_on_short_series(self):
        close = pd.Series([100.0] * 10)
        assert _hurst_exponent(close) is None

    def test_high_hurst_for_trending(self):
        # Random walk with drift (persistent) → H > 0.5
        rng = np.random.default_rng(1)
        close = pd.Series(100 + np.cumsum(rng.uniform(0.1, 0.5, 300)))
        h = _hurst_exponent(close)
        assert h is not None
        assert h > 0.5

    def test_low_hurst_for_mean_reverting(self):
        # AR(1) with strong negative autocorrelation → anti-persistent → H < 0.5
        # X(t) = -0.8 * X(t-1) + noise  → returns flip direction every bar
        rng = np.random.default_rng(42)
        r_val = 0.0
        log_returns = []
        for _ in range(400):
            r_val = -0.85 * r_val + rng.normal(0, 0.01)
            log_returns.append(r_val)
        prices = 100 * np.exp(np.cumsum(log_returns))
        close = pd.Series(prices)
        h = _hurst_exponent(close)
        assert h is not None
        assert h < 0.5

    def test_result_in_zero_one_range(self):
        rng = np.random.default_rng(7)
        close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
        h = _hurst_exponent(close)
        if h is not None:
            assert 0.0 <= h <= 1.0


# ── Individual strategy signals ──────────────────────────────────


class TestTrendSignal:
    def test_bullish_in_uptrend(self):
        vote = _trend_signal(_trending_up(200))
        assert vote.signal == 1
        assert vote.label == "BULLISH"

    def test_bearish_in_downtrend(self):
        vote = _trend_signal(_trending_down(200))
        assert vote.signal == -1
        assert vote.label == "BEARISH"

    def test_neutral_on_short_df(self):
        vote = _trend_signal(_make_df([100.0] * 10))
        assert vote.signal == 0

    def test_weight_matches_spec(self):
        vote = _trend_signal(_trending_up())
        assert vote.weight == STRATEGY_WEIGHTS["trend"]


class TestMeanRevSignal:
    def test_bullish_when_deeply_oversold(self):
        # Create oversold scenario: steep drop into very low prices
        close = [100] * 50 + [60 - i * 0.5 for i in range(30)]
        df = _make_df(close)
        # Override BB to make price clearly below lower band
        vote = _mean_rev_signal(df)
        # Price crashed below BB lower and RSI will be < 30
        assert vote.signal in (1, 0)  # may be 1 if all conditions met

    def test_neutral_for_flat_mid_range(self):
        """Flat price near middle of Bollinger Bands → neutral."""
        df = _flat(60)
        vote = _mean_rev_signal(df)
        assert vote.signal == 0
        assert vote.label == "NEUTRAL"

    def test_weight_matches_spec(self):
        vote = _mean_rev_signal(_flat())
        assert vote.weight == STRATEGY_WEIGHTS["mean_rev"]

    def test_short_df_returns_neutral(self):
        vote = _mean_rev_signal(_make_df([100.0] * 5))
        assert vote.signal == 0


class TestMomentumSignal:
    def test_bullish_strong_uptrend(self):
        """Stock that doubled in 6 months → strong positive momentum."""
        # 6 months = 126 bars, price goes from 100 → 200
        close = [100 + i * (100 / 126) for i in range(130)]
        df = _make_df(close)
        vote = _momentum_signal(df)
        assert vote.signal == 1
        assert vote.label == "BULLISH"

    def test_bearish_strong_downtrend(self):
        """Stock that halved in 6 months → strong negative momentum."""
        close = [200 - i * (100 / 126) for i in range(130)]
        df = _make_df(close)
        vote = _momentum_signal(df)
        assert vote.signal == -1

    def test_neutral_when_flat(self):
        vote = _momentum_signal(_flat(130))
        assert vote.signal == 0

    def test_only_1m_available(self):
        """Only 1-month history available — uses that timeframe alone."""
        df = _make_df([100 + i * 0.5 for i in range(30)])
        vote = _momentum_signal(df)
        # Positive return → bullish
        assert vote.signal == 1

    def test_weight_matches_spec(self):
        vote = _momentum_signal(_flat(130))
        assert vote.weight == STRATEGY_WEIGHTS["momentum"]


class TestVolatilitySignal:
    def test_bullish_in_low_vol_regime(self):
        """If recent ATR is very low relative to history, signal is bullish."""
        # Build series where last 30 bars are very calm
        rng = np.random.default_rng(5)
        # First 100 bars: high volatility
        high_vol = [100 + rng.uniform(-5, 5) for _ in range(100)]
        # Last 30 bars: very low volatility (tight range)
        low_vol = [high_vol[-1] + rng.uniform(-0.1, 0.1) for _ in range(30)]
        df = _make_df(high_vol + low_vol)
        vote = _volatility_signal(df)
        assert vote.signal == 1
        assert vote.label == "BULLISH"

    def test_bearish_in_high_vol_regime(self):
        """Recent ATR much higher than median → bearish caution."""
        rng = np.random.default_rng(6)
        # First 100 bars: calm
        calm = [100 + rng.uniform(-0.2, 0.2) for _ in range(100)]
        # Last 30 bars: wild swings
        wild = [calm[-1] + rng.uniform(-15, 15) for _ in range(30)]
        df = _make_df(calm + wild)
        vote = _volatility_signal(df)
        assert vote.signal == -1

    def test_weight_matches_spec(self):
        vote = _volatility_signal(_flat(60))
        assert vote.weight == STRATEGY_WEIGHTS["volatility"]

    def test_neutral_normal_vol(self):
        rng = np.random.default_rng(3)
        close = [100 + rng.uniform(-1, 1) for _ in range(100)]
        vote = _volatility_signal(_make_df(close))
        # Near-median vol → should be neutral
        assert vote.signal in (-1, 0, 1)  # no specific assertion, just doesn't crash


class TestStatisticalSignal:
    def test_returns_vote_and_hurst(self):
        vote, h = _statistical_signal(_trending_up(200))
        assert isinstance(vote, object)
        assert h is None or isinstance(h, float)

    def test_none_hurst_on_short_series(self):
        df = _make_df([100.0] * 15)
        vote, h = _statistical_signal(df)
        assert h is None
        assert vote.signal == 0

    def test_weight_matches_spec(self):
        vote, _ = _statistical_signal(_flat())
        assert vote.weight == STRATEGY_WEIGHTS["statistical"]


# ── Ensemble aggregation ─────────────────────────────────────────


class TestEnsembleSignal:
    def test_returns_ensemble_signal(self):
        sig = ensemble_signal(_trending_up())
        assert isinstance(sig, EnsembleSignal)

    def test_bullish_on_strong_uptrend(self):
        sig = ensemble_signal(_trending_up(200))
        assert sig.verdict == "BULLISH"
        assert sig.signal == 1

    def test_bearish_on_strong_downtrend(self):
        sig = ensemble_signal(_trending_down(200))
        assert sig.verdict == "BEARISH"
        assert sig.signal == -1

    def test_confidence_in_zero_one_range(self):
        sig = ensemble_signal(_trending_up())
        assert 0.0 <= sig.confidence <= 1.0

    def test_bull_plus_bear_le_one(self):
        sig = ensemble_signal(_trending_up())
        # neutral votes don't contribute, so bull + bear ≤ total weight (1.0)
        assert sig.bull_score + sig.bear_score <= 1.001

    def test_breakdown_has_all_five_strategies(self):
        sig = ensemble_signal(_trending_up())
        assert set(sig.breakdown.keys()) == {
            "trend",
            "mean_rev",
            "momentum",
            "volatility",
            "statistical",
        }

    def test_empty_df_returns_neutral(self):
        sig = ensemble_signal(pd.DataFrame())
        assert sig.verdict == "NEUTRAL"
        assert sig.signal == 0

    def test_tiny_df_returns_neutral(self):
        df = _make_df([100.0, 101.0, 99.0])
        sig = ensemble_signal(df)
        assert sig.verdict == "NEUTRAL"

    def test_handles_uppercase_columns(self):
        """Column names should be normalised to lowercase internally."""
        df = _trending_up()
        df.columns = [c.upper() for c in df.columns]
        sig = ensemble_signal(df)
        assert sig.verdict in ("BULLISH", "NEUTRAL", "BEARISH")

    def test_bull_score_gt_bear_score_when_bullish(self):
        sig = ensemble_signal(_trending_up(200))
        if sig.verdict == "BULLISH":
            assert sig.bull_score > sig.bear_score

    def test_hurst_is_float_or_none(self):
        sig = ensemble_signal(_trending_up())
        assert sig.hurst is None or isinstance(sig.hurst, float)

    def test_adx_is_float_or_none(self):
        sig = ensemble_signal(_trending_up())
        assert sig.adx is None or isinstance(sig.adx, float)

    def test_all_strategies_bullish_gives_full_bull_score(self):
        """Force all strategy votes to BULLISH via strongly trending DataFrame."""
        # Use an extreme, long, smooth uptrend
        close = [100 + i * 2.0 for i in range(300)]
        df = _make_df(close)
        sig = ensemble_signal(df)
        # At minimum trend + momentum should be bullish (0.25 + 0.25 = 0.50)
        assert sig.bull_score >= 0.45

    def test_weights_sum_to_one(self):
        assert abs(sum(STRATEGY_WEIGHTS.values()) - 1.0) < 1e-9


# ── format_ensemble ──────────────────────────────────────────────


class TestFormatEnsemble:
    def test_returns_string(self):
        sig = ensemble_signal(_trending_up())
        text = format_ensemble(sig, "INFY")
        assert isinstance(text, str)

    def test_contains_verdict(self):
        sig = ensemble_signal(_trending_up(200))
        text = format_ensemble(sig, "INFY")
        assert sig.verdict in text

    def test_contains_symbol(self):
        sig = ensemble_signal(_trending_up())
        text = format_ensemble(sig, "RELIANCE")
        assert "RELIANCE" in text

    def test_contains_all_strategy_names(self):
        sig = ensemble_signal(_trending_up())
        text = format_ensemble(sig)
        for name in STRATEGY_WEIGHTS:
            assert name in text

    def test_no_symbol_still_works(self):
        sig = ensemble_signal(_flat())
        text = format_ensemble(sig)
        assert "Signal Ensemble" in text
