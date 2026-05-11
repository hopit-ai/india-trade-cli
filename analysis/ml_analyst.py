"""
analysis/ml_analyst.py
───────────────────────
ML-based price direction predictor using gradient boosting.

Features computed from OHLCV:
  - RSI(14), RSI(7)
  - MACD histogram
  - BB %B (position within Bollinger Bands)
  - ATR % (ATR / close * 100)
  - Volume ratio (today / 20d avg)
  - EMA20/EMA50 ratio
  - Price momentum: (close - close[5]) / close[5]
  - Price momentum: (close - close[20]) / close[20]
  - High-Low range as % of close

Target: 1 if close[5] > close[0] * 1.02 (up >2% in 5 days), else 0

Compatible with agent/multi_agent.py BaseAnalyst interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agent.multi_agent import AnalystReport

import numpy as np
import pandas as pd

from analysis.technical import rsi, ema, macd, bollinger_bands, atr
from market.history import get_ohlcv


# ── Data model ────────────────────────────────────────────────


@dataclass
class MLPrediction:
    symbol: str
    direction: str  # "UP" | "DOWN" | "NEUTRAL"
    probability: float  # 0–1, model confidence for predicted direction
    confidence_pct: int  # probability * 100, rounded
    feature_importances: dict  # top 5 features
    model_type: str  # "GradientBoosting" | "XGBoost"
    training_samples: int
    test_accuracy: float  # accuracy on held-out 20% test set


# ── Predictor ─────────────────────────────────────────────────


class MLPredictor:
    """
    Train a GradientBoosting classifier on a symbol's historical OHLCV.
    Predict next 5-day direction.
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 3):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.model = None
        self.feature_names: list[str] = []
        self._try_xgboost = True
        self._train_meta: dict = {}

    # ── Feature engineering ───────────────────────────────────

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return DataFrame with one row per trading day, columns = feature names.
        Drops rows with NaN (warm-up period for indicators).
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # RSI
        rsi_14 = rsi(close, period=14)
        rsi_7 = rsi(close, period=7)

        # MACD histogram
        _, _, macd_hist = macd(close)

        # Bollinger %B
        bb_upper, bb_mid, bb_lower = bollinger_bands(close)
        bb_range = bb_upper - bb_lower
        bb_pct_b = (close - bb_lower) / bb_range.replace(0, np.nan)

        # ATR %
        atr_series = atr(df)
        atr_pct = atr_series / close * 100

        # Volume ratio (today / 20-day avg)
        vol_ma20 = volume.rolling(20).mean()
        volume_ratio = volume / vol_ma20.replace(0, np.nan)

        # EMA20 / EMA50 ratio
        ema20 = ema(close, 20)
        ema50 = ema(close, 50)
        ema_ratio = ema20 / ema50.replace(0, np.nan)

        # Price momentum
        momentum_5 = (close - close.shift(5)) / close.shift(5).replace(0, np.nan)
        momentum_20 = (close - close.shift(20)) / close.shift(20).replace(0, np.nan)

        # High-Low range as % of close
        hl_range_pct = (high - low) / close * 100

        feats = pd.DataFrame(
            {
                "rsi_14": rsi_14,
                "rsi_7": rsi_7,
                "macd_hist": macd_hist,
                "bb_pct_b": bb_pct_b,
                "atr_pct": atr_pct,
                "volume_ratio": volume_ratio,
                "ema_ratio": ema_ratio,
                "momentum_5": momentum_5,
                "momentum_20": momentum_20,
                "hl_range_pct": hl_range_pct,
            },
            index=df.index,
        )

        return feats.dropna()

    # ── Target construction ───────────────────────────────────

    def _compute_target(
        self,
        df: pd.DataFrame,
        forward_days: int = 5,
        threshold: float = 0.02,
    ) -> pd.Series:
        """
        1 if close[i+forward_days] > close[i] * (1 + threshold), else 0.
        NaN for last forward_days rows.
        """
        close = df["close"]
        future_close = close.shift(-forward_days)
        target = (future_close > close * (1 + threshold)).astype(float)
        target.iloc[-forward_days:] = np.nan
        return target

    # ── Model building ────────────────────────────────────────

    def _build_model(self):
        """Return an XGBoost or sklearn GradientBoostingClassifier."""
        if self._try_xgboost:
            try:
                import xgboost as xgb  # noqa: F401

                clf = xgb.XGBClassifier(
                    n_estimators=self.n_estimators,
                    max_depth=self.max_depth,
                    use_label_encoder=False,
                    eval_metric="logloss",
                    random_state=42,
                    verbosity=0,
                )
                return clf, "XGBoost"
            except ImportError:
                pass

        from sklearn.ensemble import GradientBoostingClassifier

        clf = GradientBoostingClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=42,
        )
        return clf, "GradientBoosting"

    # ── Training ──────────────────────────────────────────────

    def train(
        self,
        symbol: str,
        exchange: str = "NSE",
        period: str = "2y",
        df: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Fetch OHLCV, compute features + targets, train model.
        80/20 chronological train/test split.
        Returns {"accuracy": float, "samples": int, "model_type": str}.
        """
        if df is None:
            # Convert period string to days
            period_days = {"1y": 365, "2y": 730, "3y": 1095, "5y": 1825}
            days = period_days.get(period, 730)
            df = get_ohlcv(symbol=symbol, exchange=exchange, days=days)

        feats = self._compute_features(df)
        target = self._compute_target(df)

        # Align features and target on common index
        target_aligned = target.reindex(feats.index)
        valid_mask = target_aligned.notna()
        X = feats[valid_mask].values
        y = target_aligned[valid_mask].values.astype(int)

        # Chronological 80/20 split
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        clf, model_type = self._build_model()
        clf.fit(X_train, y_train)

        self.model = clf
        self.feature_names = list(feats.columns)
        self._train_meta = {
            "model_type": model_type,
            "samples": len(X_train),
            "accuracy": float(clf.score(X_test, y_test)) if len(X_test) > 0 else 0.0,
        }

        return self._train_meta.copy()

    # ── Prediction ────────────────────────────────────────────

    def predict(
        self,
        symbol: str,
        exchange: str = "NSE",
        df: Optional[pd.DataFrame] = None,
    ) -> MLPrediction:
        """
        Predict next 5-day direction for symbol.
        Must call train() first (or raises RuntimeError).
        """
        if self.model is None:
            raise RuntimeError("MLPredictor has not been trained yet. Call train() first.")

        if df is None:
            df = get_ohlcv(symbol=symbol, exchange=exchange, days=730)

        feats = self._compute_features(df)
        last_row = feats.iloc[[-1]].values  # shape (1, n_features)

        # Probability for class 1 (UP)
        proba = self.model.predict_proba(last_row)[0]
        p_up = float(proba[1]) if len(proba) > 1 else float(proba[0])
        p_down = 1.0 - p_up

        # Direction + probability
        if p_up > p_down:
            direction = "UP"
            probability = p_up
        else:
            direction = "DOWN"
            probability = p_down

        # Feature importances (top 5)
        importances = self.model.feature_importances_
        imp_dict = dict(zip(self.feature_names, importances.tolist()))
        top5 = dict(sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)[:5])

        return MLPrediction(
            symbol=symbol,
            direction=direction,
            probability=probability,
            confidence_pct=round(probability * 100),
            feature_importances=top5,
            model_type=self._train_meta.get("model_type", "GradientBoosting"),
            training_samples=self._train_meta.get("samples", 0),
            test_accuracy=self._train_meta.get("accuracy", 0.0),
        )

    # ── Convenience ───────────────────────────────────────────

    def train_and_predict(
        self,
        symbol: str,
        exchange: str = "NSE",
        period: str = "2y",
    ) -> MLPrediction:
        """Convenience: train then predict in one call."""
        df = get_ohlcv(symbol=symbol, exchange=exchange, days=730)
        self.train(symbol, exchange=exchange, period=period, df=df)
        return self.predict(symbol, exchange=exchange, df=df)


# ── MLAnalyst (BaseAnalyst-compatible) ────────────────────────


class MLAnalyst:
    """
    ML analyst compatible with agent/multi_agent.py BaseAnalyst interface.

    Import standalone:
        from analysis.ml_analyst import MLAnalyst
        report = MLAnalyst().analyze("INFY")
    """

    def analyze(self, symbol: str, exchange: str = "NSE") -> "AnalystReport":
        """
        Train MLPredictor, predict, return AnalystReport.

        Verdict: "BULLISH" if direction=="UP" and probability > 0.6
                 "BEARISH" if direction=="DOWN" and probability > 0.6
                 "NEUTRAL" otherwise

        Import AnalystReport from agent.multi_agent at call time to avoid circular imports.
        """
        from agent.multi_agent import AnalystReport

        try:
            predictor = MLPredictor()
            prediction = predictor.train_and_predict(symbol, exchange=exchange)

            # Determine verdict
            if prediction.direction == "UP" and prediction.probability > 0.6:
                verdict = "BULLISH"
            elif prediction.direction == "DOWN" and prediction.probability > 0.6:
                verdict = "BEARISH"
            else:
                verdict = "NEUTRAL"

            # Build key points
            key_points = [
                f"ML model predicts {prediction.direction} with "
                f"{prediction.confidence_pct}% confidence",
                f"Model: {prediction.model_type}, Test accuracy: {prediction.test_accuracy:.1%}",
                f"Trained on {prediction.training_samples} samples",
            ]

            # Top feature as a key point
            if prediction.feature_importances:
                top_feat, top_val = next(iter(prediction.feature_importances.items()))
                key_points.append(f"Top feature: {top_feat} (importance: {top_val:.3f})")

            return AnalystReport(
                analyst="ML",
                verdict=verdict,
                confidence=prediction.confidence_pct,
                score=round((prediction.probability - 0.5) * 200),  # -100 to +100
                key_points=key_points,
                data={
                    "direction": prediction.direction,
                    "probability": prediction.probability,
                    "model_type": prediction.model_type,
                    "training_samples": prediction.training_samples,
                    "test_accuracy": prediction.test_accuracy,
                    "feature_importances": prediction.feature_importances,
                },
                error="",
            )

        except Exception as exc:
            from agent.multi_agent import AnalystReport

            return AnalystReport(
                analyst="ML",
                verdict="NEUTRAL",
                confidence=0,
                score=0,
                key_points=[],
                data={},
                error=str(exc),
            )
