"""
Tests for analysis/ml_analyst.py — ML prediction analyst.

Uses synthetic OHLCV DataFrames (seed=42) and mocked get_ohlcv.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


# ── Helpers ───────────────────────────────────────────────────


def make_ohlcv(n: int = 150, seed: int = 42) -> pd.DataFrame:
    """Return a realistic synthetic OHLCV DataFrame with n rows."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    trend = np.linspace(100, 130, n)
    noise = np.random.randn(n) * 2
    close = trend + noise
    high = close + np.abs(np.random.randn(n)) * 1.5
    low = close - np.abs(np.random.randn(n)) * 1.5
    opn = close + np.random.randn(n) * 0.5
    volume = np.random.randint(500_000, 5_000_000, n).astype(float)
    return pd.DataFrame(
        {"open": opn, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


EXPECTED_FEATURES = [
    "rsi_14",
    "rsi_7",
    "macd_hist",
    "bb_pct_b",
    "atr_pct",
    "volume_ratio",
    "ema_ratio",
    "momentum_5",
    "momentum_20",
    "hl_range_pct",
]


# ── Import after helpers so fixture generation is clear ───────

from analysis.ml_analyst import MLAnalyst, MLPredictor, MLPrediction  # noqa: E402


# ── Module-scoped fixture: train once, reuse across all tests ─


@pytest.fixture(scope="module")
def trained_predictor_and_df():
    """Train a single MLPredictor on 300-row OHLCV once per module.

    Reused by TestTrain and TestPredict to avoid ~26 redundant train()
    calls that each take 200–500 ms (GradientBoosting on 300 rows).
    """
    df = make_ohlcv(300)
    predictor = MLPredictor()
    predictor.train("INFY", df=df)
    return predictor, df


# ── _compute_features tests ──────────────────────────────────


class TestComputeFeatures:
    def setup_method(self):
        self.df = make_ohlcv(150)
        self.predictor = MLPredictor()

    def test_returns_dataframe(self):
        result = self.predictor._compute_features(self.df)
        assert isinstance(result, pd.DataFrame)

    def test_has_all_expected_columns(self):
        result = self.predictor._compute_features(self.df)
        for col in EXPECTED_FEATURES:
            assert col in result.columns, f"Missing column: {col}"

    def test_no_nan_values(self):
        result = self.predictor._compute_features(self.df)
        assert not result.isnull().values.any(), "Feature DataFrame contains NaN values"

    def test_fewer_rows_than_input(self):
        """Warm-up period drops initial rows."""
        result = self.predictor._compute_features(self.df)
        assert len(result) < len(self.df)

    def test_minimum_rows_produced(self):
        """Should produce at least 50 rows from 150-row input."""
        result = self.predictor._compute_features(self.df)
        assert len(result) >= 50

    def test_rsi_range(self):
        result = self.predictor._compute_features(self.df)
        assert result["rsi_14"].min() >= 0
        assert result["rsi_14"].max() <= 100

    def test_volume_ratio_positive(self):
        result = self.predictor._compute_features(self.df)
        assert (result["volume_ratio"] > 0).all()

    def test_atr_pct_positive(self):
        result = self.predictor._compute_features(self.df)
        assert (result["atr_pct"] >= 0).all()

    def test_feature_count(self):
        result = self.predictor._compute_features(self.df)
        assert len(result.columns) == len(EXPECTED_FEATURES)


# ── _compute_target tests ─────────────────────────────────────


class TestComputeTarget:
    def setup_method(self):
        self.predictor = MLPredictor()

    def test_returns_series(self):
        df = make_ohlcv(50)
        result = self.predictor._compute_target(df)
        assert isinstance(result, pd.Series)

    def test_nan_at_end(self):
        """Last forward_days rows should be NaN (no future data)."""
        df = make_ohlcv(50)
        result = self.predictor._compute_target(df, forward_days=5)
        assert result.iloc[-5:].isnull().all()

    def test_non_nan_at_start(self):
        df = make_ohlcv(50)
        result = self.predictor._compute_target(df, forward_days=5)
        assert not result.iloc[0].item() != result.iloc[0].item()  # not NaN

    def test_known_up_sequence(self):
        """Manually constructed rising prices should label as 1."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        close = pd.Series(
            [100.0] * 5 + [103.0] * 5 + [106.0] * 10,  # each chunk > 2% above prev
            index=dates,
        )
        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": [1_000_000.0] * 20,
            },
            index=dates,
        )
        result = self.predictor._compute_target(df, forward_days=5, threshold=0.02)
        # close[5]=103, close[0]=100 → 3% up → label 1
        assert result.iloc[0] == 1

    def test_known_flat_sequence(self):
        """Flat prices should label as 0 (no 2% gain)."""
        dates = pd.date_range("2024-01-01", periods=15, freq="B")
        close = pd.Series([100.0] * 15, index=dates)
        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": [1_000_000.0] * 15,
            },
            index=dates,
        )
        result = self.predictor._compute_target(df, forward_days=5, threshold=0.02)
        assert result.iloc[0] == 0

    def test_binary_values(self):
        """Target should only contain 0, 1, or NaN."""
        df = make_ohlcv(60)
        result = self.predictor._compute_target(df)
        valid = result.dropna()
        assert set(valid.unique()).issubset({0, 1})


# ── train() tests ─────────────────────────────────────────────


class TestTrain:
    """Uses the module-scoped trained_predictor_and_df fixture — one train() per module."""

    @pytest.fixture(autouse=True)
    def _setup(self, trained_predictor_and_df):
        self.predictor, self.df = trained_predictor_and_df

    def test_returns_dict(self):
        result = self.predictor.train("INFY", df=self.df)
        assert isinstance(result, dict)

    def test_dict_has_required_keys(self):
        result = self.predictor.train("INFY", df=self.df)
        assert "accuracy" in result
        assert "samples" in result
        assert "model_type" in result

    def test_accuracy_between_0_and_1(self):
        result = self.predictor.train("INFY", df=self.df)
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_samples_positive(self):
        result = self.predictor.train("INFY", df=self.df)
        assert result["samples"] > 0

    def test_model_set_after_training(self):
        assert self.predictor.model is not None

    def test_model_type_is_string(self):
        result = self.predictor.train("INFY", df=self.df)
        assert isinstance(result["model_type"], str)
        assert result["model_type"] in ("GradientBoosting", "XGBoost")

    def test_train_with_injected_df(self):
        """train() should accept df= kwarg and skip get_ohlcv."""
        result = self.predictor.train("INFY", df=self.df)
        assert "accuracy" in result
        assert self.predictor.model is not None

    def test_feature_names_set(self):
        assert len(self.predictor.feature_names) == len(EXPECTED_FEATURES)


# ── predict() tests ───────────────────────────────────────────


class TestPredict:
    """Uses the module-scoped trained_predictor_and_df fixture — predict() calls only."""

    @pytest.fixture(autouse=True)
    def _setup(self, trained_predictor_and_df):
        self.predictor, self.df = trained_predictor_and_df
        # Cache prediction result for tests that only need to inspect it
        self._pred = self.predictor.predict("INFY", df=self.df)

    def test_predict_before_train_raises(self):
        fresh = MLPredictor()
        with pytest.raises(RuntimeError):
            fresh.predict("INFY", df=self.df)

    def test_predict_returns_mlprediction(self):
        assert isinstance(self._pred, MLPrediction)

    def test_direction_valid(self):
        assert self._pred.direction in ("UP", "DOWN", "NEUTRAL")

    def test_probability_range(self):
        assert 0.0 <= self._pred.probability <= 1.0

    def test_confidence_pct_is_rounded_int(self):
        assert isinstance(self._pred.confidence_pct, int)
        assert 0 <= self._pred.confidence_pct <= 100

    def test_feature_importances_top5(self):
        assert isinstance(self._pred.feature_importances, dict)
        assert len(self._pred.feature_importances) == 5

    def test_feature_importance_keys_are_feature_names(self):
        for key in self._pred.feature_importances:
            assert key in EXPECTED_FEATURES

    def test_training_samples_positive(self):
        assert self._pred.training_samples > 0

    def test_test_accuracy_range(self):
        assert 0.0 <= self._pred.test_accuracy <= 1.0

    def test_symbol_in_result(self):
        assert self._pred.symbol == "INFY"


# ── train_and_predict() tests ─────────────────────────────────


class TestTrainAndPredict:
    def test_returns_mlprediction(self):
        df = make_ohlcv(300)
        predictor = MLPredictor()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            result = predictor.train_and_predict("RELIANCE")
        assert isinstance(result, MLPrediction)

    def test_direction_valid(self):
        df = make_ohlcv(300)
        predictor = MLPredictor()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            result = predictor.train_and_predict("RELIANCE")
        assert result.direction in ("UP", "DOWN", "NEUTRAL")


# ── MLAnalyst tests ───────────────────────────────────────────


class TestMLAnalyst:
    def test_analyze_returns_analyst_report(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        from agent.multi_agent import AnalystReport

        assert isinstance(report, AnalystReport)

    def test_analyst_name_is_ml(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert report.analyst == "ML"

    def test_verdict_is_valid(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert report.verdict in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_confidence_range(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert 0 <= report.confidence <= 100

    def test_key_points_non_empty(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert len(report.key_points) > 0

    def test_data_contains_prediction(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert "direction" in report.data
        assert "probability" in report.data

    def test_error_is_empty_on_success(self):
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            report = analyst.analyze("TCS")
        assert report.error == ""

    def test_handles_exception_gracefully(self):
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", side_effect=Exception("network error")):
            report = analyst.analyze("TCS")
        from agent.multi_agent import AnalystReport

        assert isinstance(report, AnalystReport)
        assert report.analyst == "ML"
        assert report.error != ""

    def test_exception_verdict_is_neutral(self):
        analyst = MLAnalyst()
        with patch("analysis.ml_analyst.get_ohlcv", side_effect=Exception("timeout")):
            report = analyst.analyze("TCS")
        assert report.verdict == "NEUTRAL"

    def test_bullish_when_high_up_probability(self):
        """When direction=UP with probability>0.6, verdict should be BULLISH."""
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        mock_pred = MLPrediction(
            symbol="TCS",
            direction="UP",
            probability=0.75,
            confidence_pct=75,
            feature_importances={
                "rsi_14": 0.3,
                "macd_hist": 0.2,
                "bb_pct_b": 0.2,
                "momentum_5": 0.15,
                "atr_pct": 0.15,
            },
            model_type="GradientBoosting",
            training_samples=200,
            test_accuracy=0.65,
        )
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            with patch.object(MLPredictor, "train_and_predict", return_value=mock_pred):
                report = analyst.analyze("TCS")
        assert report.verdict == "BULLISH"

    def test_bearish_when_high_down_probability(self):
        """When direction=DOWN with probability>0.6, verdict should be BEARISH."""
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        mock_pred = MLPrediction(
            symbol="TCS",
            direction="DOWN",
            probability=0.72,
            confidence_pct=72,
            feature_importances={
                "rsi_14": 0.3,
                "macd_hist": 0.2,
                "bb_pct_b": 0.2,
                "momentum_5": 0.15,
                "atr_pct": 0.15,
            },
            model_type="GradientBoosting",
            training_samples=200,
            test_accuracy=0.65,
        )
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            with patch.object(MLPredictor, "train_and_predict", return_value=mock_pred):
                report = analyst.analyze("TCS")
        assert report.verdict == "BEARISH"

    def test_neutral_when_low_probability(self):
        """When probability <= 0.6, verdict should be NEUTRAL regardless of direction."""
        df = make_ohlcv(300)
        analyst = MLAnalyst()
        mock_pred = MLPrediction(
            symbol="TCS",
            direction="UP",
            probability=0.55,
            confidence_pct=55,
            feature_importances={
                "rsi_14": 0.3,
                "macd_hist": 0.2,
                "bb_pct_b": 0.2,
                "momentum_5": 0.15,
                "atr_pct": 0.15,
            },
            model_type="GradientBoosting",
            training_samples=200,
            test_accuracy=0.60,
        )
        with patch("analysis.ml_analyst.get_ohlcv", return_value=df):
            with patch.object(MLPredictor, "train_and_predict", return_value=mock_pred):
                report = analyst.analyze("TCS")
        assert report.verdict == "NEUTRAL"
