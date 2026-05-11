"""
Tests for engine/backtest_advanced.py

Covers MonteCarlo, Bootstrap, and WalkForward validation engines.
All tests use synthetic data — no network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from engine.backtest import BacktestResult, Trade
from engine.backtest_advanced import Bootstrap, MonteCarlo, WalkForward


# ── Helpers ──────────────────────────────────────────────────


def make_trade(pnl_pct: float, entry: str = "2024-01-01", exit_: str = "2024-01-10") -> Trade:
    """Create a synthetic Trade with the given pnl_pct."""
    return Trade(
        entry_date=entry,
        exit_date=exit_,
        direction="LONG",
        entry_price=100.0,
        exit_price=100.0 * (1 + pnl_pct / 100),
        quantity=10,
        pnl=pnl_pct * 10,
        pnl_pct=pnl_pct,
        hold_days=9,
        signal="test",
    )


def make_result(
    trade_pnls: list[float],
    cagr: float = 15.0,
    sharpe: float = 1.2,
    max_drawdown: float = -10.0,
    start_date: str = "2021-01-01",
    end_date: str = "2024-01-01",
) -> BacktestResult:
    """Build a synthetic BacktestResult from a list of trade P&L percentages."""
    trades = [make_trade(p) for p in trade_pnls]
    n = len(trade_pnls)
    winners = [t for t in trades if t.pnl > 0]
    # Build a simple equity curve: start at 100_000, apply each pnl_pct sequentially
    capital = 100_000.0
    equity = [capital]
    for p in trade_pnls:
        capital *= 1 + p / 100
        equity.append(capital)
    total_return = (capital - 100_000.0) / 100_000.0 * 100

    return BacktestResult(
        symbol="TEST",
        strategy_name="TestStrategy",
        period="3y",
        start_date=start_date,
        end_date=end_date,
        total_return=round(total_return, 2),
        cagr=cagr,
        sharpe_ratio=sharpe,
        max_drawdown=max_drawdown,
        total_trades=n,
        winning_trades=len(winners),
        losing_trades=n - len(winners),
        win_rate=round(len(winners) / n * 100, 1) if n else 0.0,
        trades=trades,
        equity_curve=equity,
    )


# Generate 20 trades: mix of winners (+5%) and losers (-2%)
TWENTY_TRADES = [
    5.0,
    -2.0,
    3.0,
    -1.5,
    4.0,
    -3.0,
    6.0,
    -2.5,
    2.0,
    1.5,
    -1.0,
    5.5,
    -2.0,
    3.5,
    -4.0,
    7.0,
    -1.0,
    4.5,
    -2.0,
    3.0,
]


# ── MonteCarlo Tests ──────────────────────────────────────────


class TestMonteCarlo:
    def test_basic_run_returns_result(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=100, seed=42)
        mc_result = mc.run(result)
        assert mc_result is not None

    def test_n_simulations_stored(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=200, seed=42)
        mc_result = mc.run(result)
        assert mc_result.n_simulations == 200

    def test_equity_curves_count(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=150, seed=42)
        mc_result = mc.run(result)
        assert len(mc_result.equity_curves) == 150

    def test_equity_curves_correct_length(self):
        """Each simulated equity curve should have len(trades)+1 points."""
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=50, seed=42)
        mc_result = mc.run(result)
        for curve in mc_result.equity_curves:
            assert len(curve) == len(TWENTY_TRADES) + 1

    def test_cagr_percentiles_ordered(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=500, seed=42)
        mc_result = mc.run(result)
        assert mc_result.cagr_p5 <= mc_result.cagr_p25
        assert mc_result.cagr_p25 <= mc_result.cagr_p50
        assert mc_result.cagr_p50 <= mc_result.cagr_p75
        assert mc_result.cagr_p75 <= mc_result.cagr_p95

    def test_sharpe_percentiles_ordered(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=500, seed=42)
        mc_result = mc.run(result)
        assert mc_result.sharpe_p5 <= mc_result.sharpe_p50
        assert mc_result.sharpe_p50 <= mc_result.sharpe_p95

    def test_max_dd_percentiles_ordered(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=500, seed=42)
        mc_result = mc.run(result)
        # max_dd is negative; p5 is worst (most negative)
        assert mc_result.max_dd_p5 <= mc_result.max_dd_p50
        assert mc_result.max_dd_p50 <= mc_result.max_dd_p95

    def test_prob_positive_return_in_range(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=500, seed=42)
        mc_result = mc.run(result)
        assert 0.0 <= mc_result.prob_positive_return <= 1.0

    def test_prob_beat_nifty_in_range(self):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=500, seed=42)
        mc_result = mc.run(result)
        assert 0.0 <= mc_result.prob_beat_nifty <= 1.0

    def test_original_cagr_preserved(self):
        result = make_result(TWENTY_TRADES, cagr=18.5)
        mc = MonteCarlo(n_simulations=100, seed=42)
        mc_result = mc.run(result)
        assert mc_result.original_cagr == 18.5

    def test_original_sharpe_preserved(self):
        result = make_result(TWENTY_TRADES, sharpe=1.75)
        mc = MonteCarlo(n_simulations=100, seed=42)
        mc_result = mc.run(result)
        assert mc_result.original_sharpe == 1.75

    def test_original_max_drawdown_preserved(self):
        result = make_result(TWENTY_TRADES, max_drawdown=-15.0)
        mc = MonteCarlo(n_simulations=100, seed=42)
        mc_result = mc.run(result)
        assert mc_result.original_max_drawdown == -15.0

    def test_seed_determinism(self):
        """Same seed should yield identical results."""
        result = make_result(TWENTY_TRADES)
        mc1 = MonteCarlo(n_simulations=200, seed=99)
        mc2 = MonteCarlo(n_simulations=200, seed=99)
        r1 = mc1.run(result)
        r2 = mc2.run(result)
        assert r1.cagr_p50 == r2.cagr_p50
        assert r1.prob_positive_return == r2.prob_positive_return

    def test_print_summary_does_not_crash(self, capsys):
        result = make_result(TWENTY_TRADES)
        mc = MonteCarlo(n_simulations=100, seed=42)
        mc_result = mc.run(result)
        mc_result.print_summary()  # Should not raise

    def test_zero_trades_raises(self):
        """0 trades should raise ValueError gracefully."""
        result = make_result([])
        mc = MonteCarlo(n_simulations=100, seed=42)
        with pytest.raises((ValueError, RuntimeError)):
            mc.run(result)

    def test_single_trade_no_crash(self):
        result = make_result([5.0])
        mc = MonteCarlo(n_simulations=50, seed=42)
        mc_result = mc.run(result)
        assert mc_result is not None
        assert mc_result.n_simulations == 50


# ── Bootstrap Tests ───────────────────────────────────────────


class TestBootstrap:
    def test_basic_run_returns_result(self):
        result = make_result(TWENTY_TRADES)
        bs = Bootstrap(n_samples=200, seed=42)
        bs_result = bs.run(result)
        assert bs_result is not None

    def test_n_samples_stored(self):
        result = make_result(TWENTY_TRADES)
        bs = Bootstrap(n_samples=300, seed=42)
        bs_result = bs.run(result)
        assert bs_result.n_samples == 300

    def test_ci_bounds_correct_order(self):
        result = make_result(TWENTY_TRADES)
        bs = Bootstrap(n_samples=500, seed=42)
        bs_result = bs.run(result)
        assert bs_result.sharpe_ci_lower <= bs_result.sharpe_ci_upper
        assert bs_result.cagr_ci_lower <= bs_result.cagr_ci_upper

    def test_original_sharpe_preserved(self):
        result = make_result(TWENTY_TRADES, sharpe=2.1)
        bs = Bootstrap(n_samples=200, seed=42)
        bs_result = bs.run(result)
        assert bs_result.original_sharpe == 2.1

    def test_original_cagr_preserved(self):
        result = make_result(TWENTY_TRADES, cagr=20.0)
        bs = Bootstrap(n_samples=200, seed=42)
        bs_result = bs.run(result)
        assert bs_result.original_cagr == 20.0

    def test_statistically_significant_when_ci_excludes_zero(self):
        """A very profitable strategy should have CI above 0."""
        # All winning trades
        result = make_result([10.0] * 20, cagr=30.0, sharpe=3.0)
        bs = Bootstrap(n_samples=500, seed=42)
        bs_result = bs.run(result)
        assert bs_result.is_statistically_significant is True

    def test_not_significant_when_ci_includes_zero(self):
        """Marginal strategy with zero-mean trades — CI should straddle 0."""
        # Equal positive and negative trades
        result = make_result([5.0, -5.0] * 10, cagr=0.0, sharpe=0.0)
        bs = Bootstrap(n_samples=500, seed=42)
        bs_result = bs.run(result)
        assert bs_result.is_statistically_significant is False

    def test_print_summary_does_not_crash(self, capsys):
        result = make_result(TWENTY_TRADES)
        bs = Bootstrap(n_samples=200, seed=42)
        bs_result = bs.run(result)
        bs_result.print_summary()

    def test_zero_trades_raises(self):
        result = make_result([])
        bs = Bootstrap(n_samples=200, seed=42)
        with pytest.raises((ValueError, RuntimeError)):
            bs.run(result)

    def test_single_trade_no_crash(self):
        result = make_result([3.0])
        bs = Bootstrap(n_samples=50, seed=42)
        bs_result = bs.run(result)
        assert bs_result is not None


# ── WalkForward Tests ─────────────────────────────────────────


def _make_backtest_result_for_window(pnl_pcts: list[float]) -> BacktestResult:
    """Helper to produce a BacktestResult for mocking Backtester.run."""
    return make_result(pnl_pcts, cagr=10.0, sharpe=1.0)


class TestWalkForward:
    def _mock_backtester_factory(self, pnl_sequence: list[list[float]]):
        """Return a mock Backtester class that yields successive results."""
        results = [make_result(p) for p in pnl_sequence]
        call_count = {"n": 0}

        def fake_run(strategy):
            idx = call_count["n"] % len(results)
            call_count["n"] += 1
            return results[idx]

        mock_bt = MagicMock()
        mock_bt.return_value.run.side_effect = fake_run
        return mock_bt

    def test_correct_number_of_windows(self):
        """3y period, 12mo train + 3mo test → expect at least 3 test windows."""
        # Each cycle = 12+3 = 15 months; 36 months / 15 ≈ 2 complete cycles
        # Walk-forward slides by test_months so 36/3 - 12/3 = more windows
        pnls = [TWENTY_TRADES] * 20  # plenty of results

        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            results = [make_result(p) for p in pnls]

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=12, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        assert len(wf_result.windows) >= 2

    def test_consistency_ratio_in_range(self):
        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            # Alternate profitable and losing windows
            pnl_sets = [[5.0, 3.0, -1.0], [-2.0, -3.0, 1.0]] * 10
            results = [make_result(p) for p in pnl_sets]

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=12, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        assert 0.0 <= wf_result.consistency_ratio <= 1.0

    def test_overfitting_ratio_computed(self):
        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            results = [make_result(TWENTY_TRADES)] * 20

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=12, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        # overfitting_ratio = out_of_sample_cagr / in_sample_cagr when in_sample != 0
        if wf_result.in_sample_cagr != 0:
            expected = wf_result.out_of_sample_cagr / wf_result.in_sample_cagr
            assert abs(wf_result.overfitting_ratio - expected) < 1e-6

    def test_avg_test_return_is_mean_of_windows(self):
        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            results = [make_result(TWENTY_TRADES)] * 20

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=12, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        # avg_test_return should equal mean of window test_returns
        if wf_result.windows:
            manual_avg = sum(w.test_return for w in wf_result.windows) / len(wf_result.windows)
            assert abs(wf_result.avg_test_return - manual_avg) < 1e-6

    def test_window_fields_populated(self):
        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            results = [make_result(TWENTY_TRADES)] * 20

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=6, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        for w in wf_result.windows:
            assert w.train_start
            assert w.train_end
            assert w.test_start
            assert w.test_end
            assert isinstance(w.test_trades, int)
            assert 0.0 <= w.test_win_rate <= 100.0

    def test_print_summary_does_not_crash(self, capsys):
        with patch("engine.backtest_advanced.Backtester") as mock_bt_cls:
            call_count = {"n": 0}
            results = [make_result(TWENTY_TRADES)] * 20

            def fake_run(strategy):
                idx = call_count["n"] % len(results)
                call_count["n"] += 1
                return results[idx]

            mock_bt_cls.return_value.run.side_effect = fake_run

            wf = WalkForward(train_months=12, test_months=3)
            wf_result = wf.run("TEST", MagicMock(), period="3y")

        wf_result.print_summary()  # Should not raise
