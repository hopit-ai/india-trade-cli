"""
Shared fixtures for the test suite.

All fixtures produce deterministic, synthetic data — no network calls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """200-row OHLCV DataFrame with deterministic prices.

    Pattern: uptrend for first 100 bars, downtrend for next 100.
    This lets us test indicators in both regimes.
    """
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2025-01-01", periods=n, freq="B")

    # Uptrend then downtrend
    trend = np.concatenate([
        np.linspace(100, 150, 100),
        np.linspace(150, 110, 100),
    ])
    noise = np.random.randn(n) * 2
    close = trend + noise

    high = close + np.abs(np.random.randn(n)) * 1.5
    low = close - np.abs(np.random.randn(n)) * 1.5
    opn = close + np.random.randn(n) * 0.5
    volume = np.random.randint(500_000, 5_000_000, n)

    return pd.DataFrame({
        "open": opn,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def strong_fundamentals() -> dict:
    """High-quality company fundamentals — should score STRONG."""
    return {
        "name": "Test Corp",
        "pe": 18.0,
        "pb": 3.0,
        "roe": 22.0,
        "roce": 25.0,
        "npm": 15.0,
        "sales_growth": 15.0,
        "profit_growth": 20.0,
        "debt_equity": 0.3,
        "current_ratio": 2.0,
        "promoter_holding": 55.0,
        "pledged_pct": 0.0,
        "dividend_yield": 2.0,
    }


@pytest.fixture
def weak_fundamentals() -> dict:
    """Weak company fundamentals — should score WEAK or AVOID."""
    return {
        "name": "Bad Corp",
        "pe": 80.0,
        "pb": 0.5,
        "roe": 5.0,
        "roce": 6.0,
        "npm": 2.0,
        "sales_growth": -5.0,
        "profit_growth": -10.0,
        "debt_equity": 2.5,
        "current_ratio": 0.6,
        "promoter_holding": 20.0,
        "pledged_pct": 30.0,
        "dividend_yield": 0.0,
    }
