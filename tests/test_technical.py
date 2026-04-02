"""Tests for analysis/technical.py — indicator calculations."""

import numpy as np
import pandas as pd
import pytest

from analysis.technical import rsi, ema, sma, macd, bollinger_bands, atr


class TestRSI:
    def test_rsi_range(self, ohlcv_df):
        """RSI must always be between 0 and 100."""
        result = rsi(ohlcv_df["close"])
        valid = result.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_rsi_oversold_in_downtrend(self, ohlcv_df):
        """RSI should reach low values during the downtrend phase (bars 100-200)."""
        result = rsi(ohlcv_df["close"])
        downtrend_rsi = result.iloc[150:].dropna()
        assert downtrend_rsi.min() < 40, "RSI should drop during downtrend"

    def test_rsi_length_matches_input(self, ohlcv_df):
        result = rsi(ohlcv_df["close"])
        assert len(result) == len(ohlcv_df)


class TestEMA:
    def test_ema_tracks_trend(self, ohlcv_df):
        """EMA should follow the general direction of prices."""
        close = ohlcv_df["close"]
        ema20 = ema(close, 20)
        # EMA at end should be near the last few close prices
        last_ema = ema20.iloc[-1]
        last_close = close.iloc[-1]
        assert abs(last_ema - last_close) < 20  # within reasonable range

    def test_ema_length(self, ohlcv_df):
        result = ema(ohlcv_df["close"], 20)
        assert len(result) == len(ohlcv_df)


class TestSMA:
    def test_sma_value(self):
        """SMA of [1,2,3,4,5] with period 3 → last value = (3+4+5)/3 = 4."""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = sma(s, 3)
        assert result.iloc[-1] == pytest.approx(4.0)

    def test_sma_nan_count(self):
        """First (period-1) values should be NaN."""
        s = pd.Series(range(10), dtype=float)
        result = sma(s, 5)
        assert result.isna().sum() == 4


class TestMACD:
    def test_macd_returns_three_series(self, ohlcv_df):
        macd_line, signal_line, histogram = macd(ohlcv_df["close"])
        assert len(macd_line) == len(ohlcv_df)
        assert len(signal_line) == len(ohlcv_df)
        assert len(histogram) == len(ohlcv_df)

    def test_histogram_is_difference(self, ohlcv_df):
        """Histogram = MACD line - Signal line."""
        macd_line, signal_line, histogram = macd(ohlcv_df["close"])
        diff = (macd_line - signal_line).dropna()
        hist = histogram.dropna()
        common = diff.index.intersection(hist.index)
        np.testing.assert_allclose(hist.loc[common].values, diff.loc[common].values, atol=1e-10)


class TestBollingerBands:
    def test_upper_above_lower(self, ohlcv_df):
        upper, mid, lower = bollinger_bands(ohlcv_df["close"])
        valid_idx = upper.dropna().index
        assert (upper.loc[valid_idx] >= lower.loc[valid_idx]).all()

    def test_mid_is_sma(self, ohlcv_df):
        """Middle band should be SMA(20)."""
        upper, mid, lower = bollinger_bands(ohlcv_df["close"], period=20)
        expected = sma(ohlcv_df["close"], 20)
        common = mid.dropna().index.intersection(expected.dropna().index)
        np.testing.assert_allclose(mid.loc[common].values, expected.loc[common].values, atol=1e-10)


class TestATR:
    def test_atr_positive(self, ohlcv_df):
        """ATR should always be positive."""
        result = atr(ohlcv_df)
        assert (result.dropna() > 0).all()

    def test_atr_length(self, ohlcv_df):
        result = atr(ohlcv_df)
        assert len(result) == len(ohlcv_df)
