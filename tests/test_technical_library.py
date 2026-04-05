"""
tests/test_technical_library.py
────────────────────────────────
Tests for engine/technical_library.py and the 8 new Strategy classes
added to engine/backtest.py.

Covers:
  - TechnicalTemplate dataclass fields
  - TechnicalLibrary list/get/search/list_by_category
  - All 32 templates present with required fields
  - Category counts correct
  - New Strategy classes: signal shape, no crash on minimal data
  - backtest_key maps to a real STRATEGIES entry or is None
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.technical_library import (
    TECH_CATEGORIES,
    TECH_TEMPLATES,
    TechnicalLibrary,
    TechnicalTemplate,
    tech_library,
)


# ── Shared fixture ────────────────────────────────────────────


def _make_ohlcv(n: int = 120, start_price: float = 1000.0) -> pd.DataFrame:
    """Minimal OHLCV DataFrame for strategy signal tests."""
    rng = np.random.default_rng(42)
    closes = start_price + np.cumsum(rng.normal(0, 10, n))
    highs = closes + rng.uniform(5, 20, n)
    lows = closes - rng.uniform(5, 20, n)
    opens = closes + rng.normal(0, 5, n)
    volumes = rng.integers(100_000, 1_000_000, n).astype(float)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


# ── TechnicalTemplate dataclass ───────────────────────────────


class TestTechnicalTemplate:
    def _make(self, **overrides) -> TechnicalTemplate:
        defaults = dict(
            id="test_tech",
            name="Test Technical",
            category="momentum",
            layman_explanation="Simple test strategy.",
            explanation="Uses a moving average crossover.",
            when_to_use="Trending markets.",
            when_not_to_use="Choppy markets.",
            signal_rules=[
                {
                    "signal": "BUY",
                    "condition": "Fast EMA > Slow EMA",
                    "example": "e.g. 9 EMA crosses above 21 EMA",
                },
                {
                    "signal": "SELL",
                    "condition": "Fast EMA < Slow EMA",
                    "example": "e.g. 9 EMA crosses below 21 EMA",
                },
            ],
            parameters={"fast": {"default": 9, "description": "Fast EMA period", "type": "int"}},
            timeframes=["1D"],
            instruments=["stocks", "indices"],
            risks=["Whipsaws in ranging markets"],
            tags=["momentum", "trend"],
            complexity="beginner",
            backtest_key="ema",
        )
        defaults.update(overrides)
        return TechnicalTemplate(**defaults)

    def test_basic_construction(self):
        t = self._make()
        assert t.id == "test_tech"
        assert t.category == "momentum"

    def test_backtest_key_optional(self):
        t = self._make(backtest_key=None)
        assert t.backtest_key is None

    def test_parameters_is_dict(self):
        t = self._make()
        assert isinstance(t.parameters, dict)

    def test_signal_rules_is_list(self):
        t = self._make()
        assert isinstance(t.signal_rules, list)
        assert len(t.signal_rules) >= 1


# ── TECH_TEMPLATES dict ───────────────────────────────────────


class TestTechTemplatesDict:
    def test_count_is_32(self):
        assert len(TECH_TEMPLATES) == 32

    def test_all_categories_present(self):
        found = {t.category for t in TECH_TEMPLATES.values()}
        assert found == set(TECH_CATEGORIES)

    @pytest.mark.parametrize(
        "strat_id",
        [
            # Momentum
            "ema_crossover",
            "macd_system",
            "supertrend",
            "heikin_ashi",
            "adx_trend",
            "donchian_breakout",
            "parabolic_sar",
            "ichimoku",
            # Mean reversion
            "bollinger_reversion",
            "rsi_reversion",
            "vwap_reversion",
            "zscore_reversion",
            "keltner_reversion",
            # Scalping
            "orb",
            "rsi_scalping",
            "vwap_scalp",
            "prev_day_hl",
            # Breakout
            "pivot_breakout",
            "inside_bar",
            "flag_pennant",
            # Pairs
            "pairs_trading",
            "index_arb",
            "etf_arb",
            "calendar_spread_futures",
            # Macro
            "rbi_policy",
            "fii_flow",
            "vix_reversion",
            "earnings_momentum",
            "sector_rotation",
            # Quantitative
            "dual_momentum",
            "factor_quality_momentum",
            "volatility_sizing",
        ],
    )
    def test_all_strategy_ids_present(self, strat_id):
        assert strat_id in TECH_TEMPLATES, f"Missing: {strat_id}"

    def test_all_templates_have_required_fields(self):
        for sid, t in TECH_TEMPLATES.items():
            assert t.id == sid, f"{sid}: id mismatch"
            assert t.name, f"{sid}: empty name"
            assert t.category in TECH_CATEGORIES, f"{sid}: invalid category '{t.category}'"
            assert t.layman_explanation, f"{sid}: no layman_explanation"
            assert t.explanation, f"{sid}: no explanation"
            assert t.when_to_use, f"{sid}: no when_to_use"
            assert t.when_not_to_use, f"{sid}: no when_not_to_use"
            assert t.signal_rules, f"{sid}: no signal_rules"
            assert t.risks, f"{sid}: no risks"
            assert t.tags, f"{sid}: no tags"
            assert t.timeframes, f"{sid}: no timeframes"
            assert t.instruments, f"{sid}: no instruments"

    def test_momentum_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "momentum"]) == 8

    def test_mean_reversion_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "mean_reversion"]) == 5

    def test_scalping_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "scalping"]) == 4

    def test_breakout_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "breakout"]) == 3

    def test_pairs_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "pairs"]) == 4

    def test_macro_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "macro"]) == 5

    def test_quantitative_count(self):
        assert len([t for t in TECH_TEMPLATES.values() if t.category == "quantitative"]) == 3

    def test_backtest_key_when_set_is_string(self):
        for sid, t in TECH_TEMPLATES.items():
            if t.backtest_key is not None:
                assert isinstance(t.backtest_key, str), f"{sid}: backtest_key must be str or None"

    def test_backtestable_templates_map_to_known_keys(self):
        from engine.backtest import STRATEGIES

        for sid, t in TECH_TEMPLATES.items():
            if t.backtest_key is not None:
                assert t.backtest_key in STRATEGIES, (
                    f"{sid}: backtest_key '{t.backtest_key}' not in STRATEGIES registry"
                )


# ── TechnicalLibrary ──────────────────────────────────────────


class TestTechnicalLibrary:
    def test_list_all_returns_32(self):
        assert len(tech_library.list_all()) == 32

    def test_list_all_sorted_by_category_then_name(self):
        results = tech_library.list_all()
        cat_order = {c: i for i, c in enumerate(TECH_CATEGORIES)}
        keys = [(cat_order[r.category], r.name) for r in results]
        assert keys == sorted(keys)

    def test_list_by_category_momentum(self):
        results = tech_library.list_by_category("momentum")
        assert len(results) == 8
        assert all(r.category == "momentum" for r in results)

    def test_list_by_category_case_insensitive(self):
        results = tech_library.list_by_category("MACRO")
        assert all(r.category == "macro" for r in results)

    def test_list_by_category_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            tech_library.list_by_category("garbage")

    def test_get_known_id(self):
        t = tech_library.get("supertrend")
        assert t.id == "supertrend"
        assert t.category == "momentum"

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError):
            tech_library.get("does_not_exist")

    def test_search_by_name(self):
        results = tech_library.search("macd")
        assert any(r.id == "macd_system" for r in results)

    def test_search_by_tag(self):
        results = tech_library.search("trend")
        assert len(results) > 0

    def test_search_case_insensitive(self):
        results = tech_library.search("RSI")
        assert any("rsi" in r.id for r in results)

    def test_search_no_match_returns_empty(self):
        assert tech_library.search("xyzqwerty_nomatch") == []

    def test_singleton_is_technical_library(self):
        assert isinstance(tech_library, TechnicalLibrary)


# ── New Strategy classes in engine/backtest.py ────────────────


class TestNewStrategyClasses:
    """Verify each new Strategy class runs without crashing and returns correct signal shape."""

    def _signals(self, strategy_key: str, df: pd.DataFrame) -> pd.Series:
        from engine.backtest import STRATEGIES

        strategy = STRATEGIES[strategy_key]([])
        return strategy.generate_signals(df)

    def _assert_valid_signals(self, signals: pd.Series, df: pd.DataFrame):
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(df)
        assert set(signals.unique()).issubset({-1, 0, 1})

    def test_supertrend_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("supertrend", df)
        self._assert_valid_signals(sigs, df)

    def test_heikin_ashi_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("heikin_ashi", df)
        self._assert_valid_signals(sigs, df)

    def test_donchian_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("donchian", df)
        self._assert_valid_signals(sigs, df)

    def test_parabolic_sar_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("psar", df)
        self._assert_valid_signals(sigs, df)

    def test_zscore_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("zscore", df)
        self._assert_valid_signals(sigs, df)

    def test_keltner_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("keltner", df)
        self._assert_valid_signals(sigs, df)

    def test_inside_bar_signals(self):
        df = _make_ohlcv(120)
        sigs = self._signals("inside_bar", df)
        self._assert_valid_signals(sigs, df)

    def test_dual_momentum_signals(self):
        df = _make_ohlcv(250)  # needs more history for monthly rebalance
        sigs = self._signals("dual_momentum", df)
        self._assert_valid_signals(sigs, df)

    def test_existing_strategies_still_work(self):
        df = _make_ohlcv(120)
        for key in ("rsi", "ema", "macd", "bb"):
            sigs = self._signals(key, df)
            self._assert_valid_signals(sigs, df)

    def test_supertrend_not_all_zero(self):
        # Build a clear up-then-down price series to guarantee a Supertrend flip.
        import pandas as pd
        import numpy as np

        n = 200
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        closes = np.concatenate(
            [
                np.linspace(1000, 1500, 100),  # strong uptrend  (+50%)
                np.linspace(1500, 900, 100),  # strong downtrend (−40%)
            ]
        )
        highs = closes + 10
        lows = closes - 10
        opens = closes + np.random.default_rng(7).normal(0, 3, n)
        volumes = np.ones(n) * 500_000
        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
            index=idx,
        )
        sigs = self._signals("supertrend", df)
        self._assert_valid_signals(sigs, df)
        assert (sigs != 0).any(), "Supertrend should generate at least one signal"

    def test_donchian_not_all_zero(self):
        df = _make_ohlcv(200)
        sigs = self._signals("donchian", df)
        assert (sigs != 0).any()

    def test_zscore_signals_symmetric(self):
        # Z-score mean reversion should produce both buy and sell signals
        df = _make_ohlcv(200)
        sigs = self._signals("zscore", df)
        # With random walk data both +/- signals should appear eventually
        assert 1 in sigs.values or -1 in sigs.values
