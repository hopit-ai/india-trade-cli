"""
Tests for engine/backtest_regime.py — regime labelling and per-regime performance.

All tests use synthetic data — no network calls, no yfinance.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from engine.backtest import BacktestResult, Trade
from engine.backtest_regime import (
    BacktestRegimeResult,
    RegimeStats,
    RegimeType,
    _sharpe_from_returns,
    analyse_by_regime,
    label_regimes,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_trade(entry_date: str, pnl_pct: float, hold_days: int = 10) -> Trade:
    """Create a minimal synthetic Trade for testing."""
    return Trade(
        entry_date=entry_date,
        exit_date="2024-06-01",
        direction="LONG",
        entry_price=100.0,
        exit_price=100.0 * (1 + pnl_pct / 100),
        quantity=10,
        pnl=pnl_pct * 10,
        pnl_pct=pnl_pct,
        hold_days=hold_days,
        signal="TEST",
    )


def _make_backtest_result(trades: list[Trade]) -> BacktestResult:
    """Wrap a list of trades in a minimal BacktestResult."""
    return BacktestResult(
        symbol="TEST",
        strategy_name="MockStrategy",
        period="1y",
        start_date="2023-01-01",
        end_date="2024-01-01",
        total_return=5.0,
        cagr=5.0,
        sharpe_ratio=0.8,
        max_drawdown=-10.0,
        total_trades=len(trades),
        winning_trades=sum(1 for t in trades if t.pnl > 0),
        losing_trades=sum(1 for t in trades if t.pnl <= 0),
        win_rate=50.0,
        trades=trades,
        equity_curve=[100_000.0] * (len(trades) + 1),
    )


def _bull_price_series(n: int = 300) -> pd.Series:
    """Rising prices well above any 200-day SMA."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    prices = pd.Series(np.linspace(200, 400, n), index=dates)
    return prices


def _bear_price_series(n: int = 300) -> pd.Series:
    """Falling prices well below any 200-day SMA."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    prices = pd.Series(np.linspace(400, 100, n), index=dates)
    return prices


def _sideways_price_series(n: int = 300) -> pd.Series:
    """Flat prices oscillating around the SMA — sideways regime."""
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    base = 100.0
    # Tiny oscillation — stays within ±1% of start, never diverges 3%
    noise = np.sin(np.linspace(0, 6 * np.pi, n)) * 0.5
    prices = pd.Series(base + noise, index=dates)
    return prices


# ── label_regimes() ───────────────────────────────────────────────────────────


class TestLabelRegimes:
    def test_returns_series(self):
        prices = _bull_price_series()
        labels = label_regimes(prices)
        assert isinstance(labels, pd.Series)

    def test_index_matches_input(self):
        prices = _bull_price_series()
        labels = label_regimes(prices)
        assert labels.index.equals(prices.index)

    def test_values_are_regime_strings(self):
        prices = _bull_price_series()
        labels = label_regimes(prices)
        valid = {RegimeType.BULL, RegimeType.BEAR, RegimeType.SIDEWAYS}
        non_null = labels.dropna()
        assert set(non_null.unique()).issubset(valid)

    def test_bull_regime_dominant_in_bull_series(self):
        """A strongly rising series should be mostly BULL after SMA warmup."""
        prices = _bull_price_series(n=300)
        labels = label_regimes(prices, sma_period=50)
        # After warmup, expect majority BULL
        counts = labels.value_counts()
        assert counts.get(RegimeType.BULL, 0) > counts.get(RegimeType.BEAR, 0)

    def test_bear_regime_dominant_in_bear_series(self):
        """A strongly falling series should be mostly BEAR."""
        prices = _bear_price_series(n=300)
        labels = label_regimes(prices, sma_period=50)
        counts = labels.value_counts()
        assert counts.get(RegimeType.BEAR, 0) > counts.get(RegimeType.BULL, 0)

    def test_sideways_regime_present_in_flat_series(self):
        """A flat series should produce at least some SIDEWAYS labels."""
        prices = _sideways_price_series(n=300)
        labels = label_regimes(prices, sma_period=50)
        assert (labels == RegimeType.SIDEWAYS).sum() > 0

    def test_short_series_no_crash(self):
        """Series shorter than sma_period should return all SIDEWAYS (NaN SMA → sideways)."""
        prices = pd.Series(
            [100.0, 101.0, 99.0],
            index=pd.date_range("2024-01-01", periods=3, freq="B"),
        )
        labels = label_regimes(prices, sma_period=200)
        assert len(labels) == 3
        # No raises — all should be SIDEWAYS (SMA is NaN)
        assert all(v == RegimeType.SIDEWAYS for v in labels)

    def test_custom_sideways_threshold(self):
        """A tighter threshold should classify more bars as BULL/BEAR."""
        prices = _bull_price_series(n=300)
        tight_labels = label_regimes(prices, sma_period=50, sideways_threshold=0.001)
        loose_labels = label_regimes(prices, sma_period=50, sideways_threshold=0.10)
        tight_bull = (tight_labels == RegimeType.BULL).sum()
        loose_bull = (loose_labels == RegimeType.BULL).sum()
        assert tight_bull >= loose_bull


# ── RegimeStats dataclass ─────────────────────────────────────────────────────


class TestRegimeStats:
    def test_fields_and_types(self):
        stats = RegimeStats(
            regime=RegimeType.BULL,
            trade_count=5,
            win_count=3,
            win_rate=60.0,
            avg_return=2.5,
            total_return=12.5,
            avg_hold_days=8.0,
            sharpe=1.2,
            best_trade=5.0,
            worst_trade=-1.0,
            regime_pct=40.0,
        )
        assert stats.regime == RegimeType.BULL
        assert isinstance(stats.trade_count, int)
        assert isinstance(stats.win_rate, float)
        assert isinstance(stats.sharpe, float)

    def test_zero_trades_allowed(self):
        stats = RegimeStats(
            regime=RegimeType.BEAR,
            trade_count=0,
            win_count=0,
            win_rate=0.0,
            avg_return=0.0,
            total_return=0.0,
            avg_hold_days=0.0,
            sharpe=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            regime_pct=20.0,
        )
        assert stats.trade_count == 0


# ── BacktestRegimeResult ──────────────────────────────────────────────────────


class TestBacktestRegimeResult:
    def _make_result(self) -> BacktestRegimeResult:
        bull_stats = RegimeStats(
            regime=RegimeType.BULL,
            trade_count=6,
            win_count=5,
            win_rate=83.3,
            avg_return=3.0,
            total_return=18.0,
            avg_hold_days=10.0,
            sharpe=1.5,
            best_trade=8.0,
            worst_trade=-1.0,
            regime_pct=50.0,
        )
        bear_stats = RegimeStats(
            regime=RegimeType.BEAR,
            trade_count=4,
            win_count=1,
            win_rate=25.0,
            avg_return=-2.0,
            total_return=-8.0,
            avg_hold_days=15.0,
            sharpe=-0.5,
            best_trade=2.0,
            worst_trade=-5.0,
            regime_pct=30.0,
        )
        sideways_stats = RegimeStats(
            regime=RegimeType.SIDEWAYS,
            trade_count=0,
            win_count=0,
            win_rate=0.0,
            avg_return=0.0,
            total_return=0.0,
            avg_hold_days=0.0,
            sharpe=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            regime_pct=20.0,
        )
        dummy_result = _make_backtest_result([_make_trade("2023-06-01", 3.0)])
        dates = pd.date_range("2023-01-01", periods=5, freq="B")
        regime_labels = pd.Series(
            [
                RegimeType.BULL,
                RegimeType.BEAR,
                RegimeType.SIDEWAYS,
                RegimeType.BULL,
                RegimeType.BULL,
            ],
            index=dates,
        )
        return BacktestRegimeResult(
            symbol="TEST",
            strategy_name="MockStrategy",
            period="1y",
            regimes={
                RegimeType.BULL: bull_stats,
                RegimeType.BEAR: bear_stats,
                RegimeType.SIDEWAYS: sideways_stats,
            },
            overall_result=dummy_result,
            regime_labels=regime_labels,
        )

    def test_construction(self):
        r = self._make_result()
        assert r.symbol == "TEST"
        assert RegimeType.BULL in r.regimes
        assert RegimeType.BEAR in r.regimes
        assert RegimeType.SIDEWAYS in r.regimes

    def test_best_regime(self):
        r = self._make_result()
        assert r.best_regime() == RegimeType.BULL  # 83.3% win rate

    def test_worst_regime(self):
        r = self._make_result()
        # SIDEWAYS has 0% (0 trades → win_rate=0), BEAR has 25%
        assert r.worst_regime() in (RegimeType.SIDEWAYS, RegimeType.BEAR)

    def test_print_summary_no_crash(self, capsys):
        r = self._make_result()
        r.print_summary()  # must not raise


# ── analyse_by_regime() ───────────────────────────────────────────────────────


def _build_prices_with_regimes() -> pd.Series:
    """
    600 business days: first 300 bull (rising), last 300 bear (falling).
    Plenty for SMA-200.
    """
    dates = pd.date_range("2021-01-01", periods=600, freq="B")
    bull_part = np.linspace(100, 300, 300)
    bear_part = np.linspace(300, 80, 300)
    prices = pd.Series(np.concatenate([bull_part, bear_part]), index=dates)
    return prices


class TestAnalyseByRegime:
    def _trades_spanning_both_regimes(self) -> list[Trade]:
        """10 trades: 5 in bull zone (early 2021), 5 in bear zone (late 2023)."""
        bull_trades = [
            _make_trade(f"2021-0{m}-15", pnl_pct=p)
            for m, p in zip([3, 4, 5, 6, 7], [5.0, 3.0, -1.0, 4.0, 2.0])
        ]
        bear_trades = [
            _make_trade(f"2022-0{m}-15", pnl_pct=p)
            for m, p in zip([1, 2, 3, 4, 5], [-3.0, -2.0, 1.0, -4.0, -1.0])
        ]
        return bull_trades + bear_trades

    def test_returns_backtest_regime_result(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        assert isinstance(regime_result, BacktestRegimeResult)

    def test_symbol_and_strategy_preserved(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        assert regime_result.symbol == "TEST"
        assert regime_result.strategy_name == "MockStrategy"

    def test_all_three_regimes_present(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        assert RegimeType.BULL in regime_result.regimes
        assert RegimeType.BEAR in regime_result.regimes
        assert RegimeType.SIDEWAYS in regime_result.regimes

    def test_trade_count_sums_to_total(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        total = sum(s.trade_count for s in regime_result.regimes.values())
        assert total == len(trades)

    def test_win_rate_computed_correctly(self):
        """win_count must match actual positive-pnl trades in each regime."""
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        for rtype, stats in regime_result.regimes.items():
            if stats.trade_count > 0:
                # win_rate should be consistent with win_count / trade_count
                expected_wr = round(stats.win_count / stats.trade_count * 100, 1)
                assert stats.win_rate == expected_wr

    def test_zero_trade_regime_handled_gracefully(self):
        """A regime with 0 trades must produce RegimeStats with 0s, not crash."""
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        for rtype, stats in regime_result.regimes.items():
            if stats.trade_count == 0:
                assert stats.win_rate == 0.0
                assert stats.avg_return == 0.0
                assert stats.sharpe == 0.0

    def test_regime_labels_series_returned(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        assert isinstance(regime_result.regime_labels, pd.Series)
        assert len(regime_result.regime_labels) > 0

    def test_prices_none_fetches_from_yfinance(self):
        """When prices=None, yfinance should be called (mocked here)."""
        trades = [_make_trade("2023-06-15", 2.0)]
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()

        with patch("engine.backtest_regime.yf") as mock_yf:
            mock_ticker = mock_yf.Ticker.return_value
            mock_ticker.history.return_value = pd.DataFrame(
                {"Close": prices.values},
                index=prices.index,
            )
            regime_result = analyse_by_regime(result, prices=None)
        assert isinstance(regime_result, BacktestRegimeResult)

    def test_best_and_worst_regime_types(self):
        trades = self._trades_spanning_both_regimes()
        result = _make_backtest_result(trades)
        prices = _build_prices_with_regimes()
        regime_result = analyse_by_regime(result, prices=prices)
        best = regime_result.best_regime()
        worst = regime_result.worst_regime()
        assert best in RegimeType.__members__.values()
        assert worst in RegimeType.__members__.values()


# ── _sharpe_from_returns() ────────────────────────────────────────────────────


class TestSharpeFromReturns:
    def test_positive_sharpe_for_consistent_gains(self):
        # Varying positive returns — mean > 0, std > 0 → positive Sharpe
        returns = [1.0, 1.5, 2.0, 1.2, 1.8, 0.8, 1.3, 1.6, 1.1, 1.9]
        s = _sharpe_from_returns(returns)
        assert s > 0

    def test_negative_sharpe_for_consistent_losses(self):
        # Varying negative returns — mean < 0, std > 0 → negative Sharpe
        returns = [-1.0, -1.5, -2.0, -1.2, -1.8, -0.8, -1.3, -1.6, -1.1, -1.9]
        s = _sharpe_from_returns(returns)
        assert s < 0

    def test_zero_sharpe_for_empty_list(self):
        assert _sharpe_from_returns([]) == 0.0

    def test_zero_sharpe_for_single_return(self):
        # Std dev of a single value is 0 → Sharpe undefined → return 0
        assert _sharpe_from_returns([5.0]) == 0.0

    def test_known_value(self):
        """All returns equal → std = 0 → Sharpe should be 0 (no variation)."""
        returns = [2.0, 2.0, 2.0, 2.0]
        s = _sharpe_from_returns(returns)
        assert s == 0.0

    def test_annualisation(self):
        """Sharpe with periods_per_year=1 should differ from default 252."""
        returns = [1.0, 2.0, -0.5, 1.5, 0.5]
        s_annual = _sharpe_from_returns(returns, periods_per_year=252)
        s_unit = _sharpe_from_returns(returns, periods_per_year=1)
        assert s_annual != s_unit
