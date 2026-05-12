"""
engine/position_sizer.py
────────────────────────
Volatility-adjusted position sizing with portfolio correlation matrix.

Combines:
  - Kelly criterion (half-Kelly cap for safety)
  - ATR-based volatility normalization
  - Portfolio correlation penalty (reduce size when highly correlated with existing holds)
  - Hard capital cap per position

Usage:
    from engine.position_sizer import VolatilityAdjustedSizer, compute_portfolio_var

    sizer = VolatilityAdjustedSizer(total_capital=500_000)
    result = sizer.size_position(
        symbol="RELIANCE",
        win_rate=0.60,
        avg_win_pct=0.05,
        avg_loss_pct=0.03,
        atr_pct=0.018,
        existing_symbols=["INFY", "TCS"],
    )
    print(result.recommended_qty, result.rationale)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from market.history import get_ohlcv


@dataclass
class PositionSizeResult:
    """Output of VolatilityAdjustedSizer.size_position()."""

    symbol: str
    recommended_qty: int  # final integer lots or shares
    recommended_value: float  # INR value of position (qty × price_per_lot)
    position_pct: float  # fraction of total_capital (0–max_position_pct)
    volatility_scalar: float  # 1.0 = no adjustment; <1 = reduced for high vol
    correlation_penalty: float  # 0–1; 0 = no penalty
    kelly_fraction: float  # half-Kelly fraction applied
    rationale: str  # human-readable explanation


class VolatilityAdjustedSizer:
    """
    Position sizing that accounts for:
    1. Asset volatility (ATR as % of price)
    2. Portfolio correlation (reduce size if new position highly correlated with existing)
    3. Kelly criterion (capped at half-Kelly for safety)
    4. Capital limits (max pct per position)
    """

    def __init__(
        self,
        total_capital: float,
        max_position_pct: float = 0.10,
        target_risk_pct: float = 0.01,
    ) -> None:
        """
        total_capital:    total trading capital in INR
        max_position_pct: max single position as fraction of capital (default 10%)
        target_risk_pct:  target risk per trade as fraction of capital (default 1%)
        """
        self.total_capital = total_capital
        self.max_position_pct = max_position_pct
        self.target_risk_pct = target_risk_pct

    # ── Public API ────────────────────────────────────────────────

    def compute_correlation_matrix(
        self,
        symbols: list[str],
        period: str = "3mo",
    ) -> pd.DataFrame:
        """
        Fetch daily returns for each symbol and compute Pearson correlation matrix.

        Returns:
            pd.DataFrame with symbols as both index and columns.
            Diagonal = 1.0, off-diagonal = Pearson r ∈ [-1, 1].
        """
        period_days = _period_to_days(period)
        returns_dict: dict[str, pd.Series] = {}

        for sym in symbols:
            df = get_ohlcv(sym, days=period_days)
            if df is None or df.empty or len(df) < 10:
                continue
            ret = df["close"].pct_change().dropna()
            returns_dict[sym] = ret

        if len(returns_dict) < 2:
            # Return identity matrix with whatever symbols we have
            idx = list(returns_dict.keys()) or symbols
            return pd.DataFrame(np.eye(len(idx)), index=idx, columns=idx)

        # Align on common dates
        returns_df = pd.DataFrame(returns_dict).dropna()
        corr = returns_df.corr(method="pearson")

        # Fill any missing symbols with a row/col of zeros (off-diagonal) + 1 (diagonal)
        for sym in symbols:
            if sym not in corr.columns:
                corr[sym] = 0.0
                corr.loc[sym] = 0.0
                corr.loc[sym, sym] = 1.0

        return corr.loc[symbols, symbols]

    def size_position(
        self,
        symbol: str,
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        atr_pct: float,
        existing_symbols: list[str] | None = None,
        lot_size: int = 1,
        price_per_lot: float = 1.0,
    ) -> PositionSizeResult:
        """
        Compute a volatility-adjusted, correlation-aware position size.

        Steps:
        1. Kelly fraction  = win_rate / avg_loss_pct − (1−win_rate) / avg_win_pct
           Cap at half-Kelly (÷2).
        2. Volatility scalar = target_risk_pct / atr_pct, clamped [0.25, 2.0].
           Zero ATR is treated as very low → scalar capped at 2.0.
        3. Correlation penalty: fetch correlations with existing_symbols,
           penalty = max_pairwise_corr × 0.5  (range [0, 0.5] given corr ∈ [-1,1]).
        4. Final pct = kelly × vol_scalar × (1 − penalty),  clamped [0, max_position_pct].
        5. qty = floor(final_pct × total_capital / price_per_lot), rounded down to lot_size.
        """

        # ── Step 1: Kelly ─────────────────────────────────────────
        raw_kelly = _compute_kelly(win_rate, avg_win_pct, avg_loss_pct)
        half_kelly = max(raw_kelly / 2.0, 0.0)  # negative Kelly → 0 position

        if half_kelly <= 0:
            return PositionSizeResult(
                symbol=symbol,
                recommended_qty=0,
                recommended_value=0.0,
                position_pct=0.0,
                volatility_scalar=_vol_scalar(atr_pct, self.target_risk_pct),
                correlation_penalty=0.0,
                kelly_fraction=half_kelly,
                rationale=(f"Kelly fraction non-positive ({raw_kelly:.4f}); no edge — skip trade."),
            )

        # ── Step 2: Volatility scalar ─────────────────────────────
        vol_scalar = _vol_scalar(atr_pct, self.target_risk_pct)

        # ── Step 3: Correlation penalty ───────────────────────────
        corr_penalty = 0.0
        if existing_symbols:
            all_syms = [symbol] + existing_symbols
            try:
                corr_matrix = self.compute_correlation_matrix(all_syms)
                # Find max |correlation| between new symbol and any existing symbol
                if symbol in corr_matrix.columns:
                    corr_row = corr_matrix.loc[symbol, existing_symbols]
                    # Only use valid (non-NaN) entries
                    valid_corr = corr_row.dropna()
                    if not valid_corr.empty:
                        max_corr = float(valid_corr.abs().max())
                        corr_penalty = max_corr * 0.5
            except Exception:
                pass  # network failure or bad data → no penalty

        # ── Step 4: Final position fraction ───────────────────────
        final_pct = half_kelly * vol_scalar * (1.0 - corr_penalty)
        final_pct = min(final_pct, self.max_position_pct)
        final_pct = max(final_pct, 0.0)

        # ── Step 5: Quantity ──────────────────────────────────────
        if price_per_lot <= 0:
            price_per_lot = 1.0

        raw_qty = math.floor(final_pct * self.total_capital / price_per_lot)
        # Round down to nearest lot
        if lot_size > 1:
            raw_qty = (raw_qty // lot_size) * lot_size

        recommended_value = raw_qty * price_per_lot

        rationale = (
            f"Kelly(raw)={raw_kelly:.4f} → half-Kelly={half_kelly:.4f}; "
            f"vol_scalar={vol_scalar:.3f} (atr_pct={atr_pct:.4f}); "
            f"corr_penalty={corr_penalty:.3f}; "
            f"final_pct={final_pct:.4f} ({final_pct * 100:.2f}% of capital); "
            f"qty={raw_qty} × lot_size={lot_size}."
        )

        return PositionSizeResult(
            symbol=symbol,
            recommended_qty=raw_qty,
            recommended_value=round(recommended_value, 2),
            position_pct=final_pct,
            volatility_scalar=vol_scalar,
            correlation_penalty=corr_penalty,
            kelly_fraction=half_kelly,
            rationale=rationale,
        )


# ── Portfolio VaR ─────────────────────────────────────────────────


def compute_portfolio_var(
    symbols: list[str],
    weights: list[float],
    period: str = "1y",
    confidence: float = 0.95,
) -> dict:
    """
    Compute portfolio Value-at-Risk using historical simulation.

    Args:
        symbols:    List of trading symbols.
        weights:    Portfolio weights (must sum to ≈ 1.0; will be normalised).
        period:     Lookback period string, e.g. "1y", "6mo", "3mo".
        confidence: VaR confidence level (default 0.95 = 95%).

    Returns:
        dict with keys:
            var_1day         – 1-day VaR as a fraction of portfolio value
            var_10day        – 10-day VaR (= var_1day × √10)
            cvar             – Conditional VaR (expected shortfall) at 1-day
            volatility_annual – Annualised portfolio volatility (fraction)
    """
    period_days = _period_to_days(period)

    # Collect return series
    returns_dict: dict[str, pd.Series] = {}
    for sym in symbols:
        df = get_ohlcv(sym, days=period_days)
        if df is not None and not df.empty and len(df) >= 10:
            ret = df["close"].pct_change().dropna()
            returns_dict[sym] = ret

    if not returns_dict:
        return {
            "var_1day": 0.0,
            "var_10day": 0.0,
            "cvar": 0.0,
            "volatility_annual": 0.0,
        }

    # Align symbols present in returns_dict with matching weights
    valid_syms = [s for s in symbols if s in returns_dict]
    raw_weights = np.array([weights[symbols.index(s)] for s in valid_syms], dtype=float)
    if raw_weights.sum() == 0:
        raw_weights = np.ones(len(valid_syms))
    norm_weights = raw_weights / raw_weights.sum()

    # Align on common dates
    returns_df = pd.DataFrame({s: returns_dict[s] for s in valid_syms}).dropna()

    if returns_df.empty:
        return {
            "var_1day": 0.0,
            "var_10day": 0.0,
            "cvar": 0.0,
            "volatility_annual": 0.0,
        }

    # Portfolio returns
    port_returns = returns_df.values @ norm_weights  # shape (T,)

    # Historical simulation VaR
    pct_threshold = (1.0 - confidence) * 100  # e.g. 5 for 95%
    var_1day = float(abs(np.percentile(port_returns, pct_threshold)))
    var_10day = var_1day * math.sqrt(10)

    # CVaR (Expected Shortfall)
    tail_mask = port_returns <= -var_1day
    if tail_mask.any():
        cvar = float(abs(np.mean(port_returns[tail_mask])))
    else:
        cvar = var_1day * 1.2  # fallback estimate

    # Annualised volatility
    daily_vol = float(np.std(port_returns, ddof=1))
    volatility_annual = daily_vol * math.sqrt(252)

    return {
        "var_1day": round(var_1day, 6),
        "var_10day": round(var_10day, 6),
        "cvar": round(cvar, 6),
        "volatility_annual": round(volatility_annual, 6),
    }


# ── Internal helpers ──────────────────────────────────────────────


def _compute_kelly(
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
) -> float:
    """
    Kelly criterion:
        f = win_rate / avg_loss_pct − (1 − win_rate) / avg_win_pct

    Protects against division by zero: returns a large negative number if
    avg_win_pct or avg_loss_pct are zero/negative (indicating no edge).
    """
    if avg_win_pct <= 0 or avg_loss_pct <= 0:
        return -1.0  # no edge
    win_term = win_rate / avg_loss_pct
    loss_term = (1.0 - win_rate) / avg_win_pct
    return win_term - loss_term


def _vol_scalar(atr_pct: float, target_risk_pct: float) -> float:
    """
    Volatility scalar = target_risk_pct / atr_pct,  clamped [0.25, 2.0].
    Zero or very small ATR → scalar pinned at 2.0 (upper cap).
    """
    if atr_pct <= 0:
        return 2.0
    raw = target_risk_pct / atr_pct
    return float(np.clip(raw, 0.25, 2.0))


def _period_to_days(period: str) -> int:
    """Convert a period string (e.g. '3mo', '1y', '6mo') to calendar days."""
    period = period.lower().strip()
    if period.endswith("y"):
        return int(period[:-1]) * 365
    if period.endswith("mo"):
        return int(period[:-2]) * 30
    if period.endswith("m"):
        # ambiguous — treat as months if >= 2 digits else years
        val = int(period[:-1])
        return val * 30
    if period.endswith("d"):
        return int(period[:-1])
    # Default: treat as integer days
    try:
        return int(period)
    except ValueError:
        return 365
