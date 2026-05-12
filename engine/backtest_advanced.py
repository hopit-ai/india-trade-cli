"""
engine/backtest_advanced.py
────────────────────────────
Advanced backtest validation engines.

Three engines:
  1. MonteCarlo  — shuffle trade returns to build confidence intervals
  2. Bootstrap   — resample equity curve with replacement
  3. WalkForward — rolling train/test split validation

Usage:
    from engine.backtest_advanced import MonteCarlo, Bootstrap, WalkForward
    from engine.backtest import Backtester, RSIStrategy

    bt = Backtester("NIFTY", period="3y")
    result = bt.run(RSIStrategy())

    mc = MonteCarlo(n_simulations=1000)
    mc_result = mc.run(result)
    mc_result.print_summary()

    wf = WalkForward(train_months=12, test_months=3)
    wf_result = wf.run("NIFTY", RSIStrategy(), period="3y")
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from engine.backtest import BacktestResult, Backtester

console = Console()

# ── Result Dataclasses ────────────────────────────────────────


@dataclass
class MonteCarloResult:
    """Results of a Monte Carlo simulation over shuffled trade sequences."""

    n_simulations: int
    original_cagr: float
    original_sharpe: float
    original_max_drawdown: float

    # Percentiles across simulations
    cagr_p5: float
    cagr_p25: float
    cagr_p50: float
    cagr_p75: float
    cagr_p95: float
    sharpe_p5: float
    sharpe_p50: float
    sharpe_p95: float
    max_dd_p5: float
    max_dd_p50: float
    max_dd_p95: float

    prob_positive_return: float  # fraction of simulations with CAGR > 0
    prob_beat_nifty: float  # fraction with CAGR > 12% (typical Nifty CAGR)

    equity_curves: list[list[float]]  # all simulated curves (for optional plotting)

    def print_summary(self) -> None:
        lines = [
            f"  Simulations          : {self.n_simulations}",
            "",
            "  [bold]Original Strategy[/bold]",
            f"  CAGR                 : {self.original_cagr:+.2f}%",
            f"  Sharpe               : {self.original_sharpe:.2f}",
            f"  Max Drawdown         : {self.original_max_drawdown:.2f}%",
            "",
            "  [bold]CAGR Percentiles[/bold]",
            f"  P5 / P25 / P50       : {self.cagr_p5:+.2f}% / {self.cagr_p25:+.2f}% / {self.cagr_p50:+.2f}%",
            f"  P75 / P95            : {self.cagr_p75:+.2f}% / {self.cagr_p95:+.2f}%",
            "",
            "  [bold]Sharpe Percentiles[/bold]",
            f"  P5 / P50 / P95       : {self.sharpe_p5:.2f} / {self.sharpe_p50:.2f} / {self.sharpe_p95:.2f}",
            "",
            "  [bold]Max Drawdown Percentiles[/bold]",
            f"  P5 / P50 / P95       : {self.max_dd_p5:.2f}% / {self.max_dd_p50:.2f}% / {self.max_dd_p95:.2f}%",
            "",
            "  [bold]Probabilities[/bold]",
            f"  P(positive return)   : {self.prob_positive_return * 100:.1f}%",
            f"  P(beat Nifty ~12%)   : {self.prob_beat_nifty * 100:.1f}%",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]Monte Carlo Simulation[/bold cyan]",
                border_style="cyan",
            )
        )


@dataclass
class BootstrapResult:
    """Results of Bootstrap resampling of trades."""

    n_samples: int
    original_sharpe: float
    sharpe_ci_lower: float  # 95% CI lower bound
    sharpe_ci_upper: float
    original_cagr: float
    cagr_ci_lower: float
    cagr_ci_upper: float
    is_statistically_significant: bool  # True if Sharpe CI doesn't include 0

    def print_summary(self) -> None:
        sig_str = "[green]YES[/green]" if self.is_statistically_significant else "[red]NO[/red]"
        lines = [
            f"  Samples              : {self.n_samples}",
            "",
            "  [bold]Sharpe Ratio[/bold]",
            f"  Original             : {self.original_sharpe:.2f}",
            f"  95% CI               : [{self.sharpe_ci_lower:.2f}, {self.sharpe_ci_upper:.2f}]",
            "",
            "  [bold]CAGR[/bold]",
            f"  Original             : {self.original_cagr:+.2f}%",
            f"  95% CI               : [{self.cagr_ci_lower:+.2f}%, {self.cagr_ci_upper:+.2f}%]",
            "",
            f"  Statistically Significant: {sig_str}",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]Bootstrap Confidence Intervals[/bold cyan]",
                border_style="cyan",
            )
        )


@dataclass
class WalkForwardWindow:
    """A single train/test split window."""

    train_start: str
    train_end: str
    test_start: str
    test_end: str
    test_return: float  # % total return in test window
    test_trades: int
    test_win_rate: float


@dataclass
class WalkForwardResult:
    """Results of walk-forward validation."""

    windows: list[WalkForwardWindow]
    avg_test_return: float  # mean test window return
    consistency_ratio: float  # fraction of windows with positive return
    in_sample_cagr: float  # overall in-sample CAGR (mean across train windows)
    out_of_sample_cagr: float  # overall out-of-sample CAGR (mean across test windows)
    overfitting_ratio: float  # out_of_sample_cagr / in_sample_cagr (1.0 = no overfit)

    def print_summary(self) -> None:
        lines = [
            f"  Windows              : {len(self.windows)}",
            f"  Avg Test Return      : {self.avg_test_return:+.2f}%",
            f"  Consistency Ratio    : {self.consistency_ratio * 100:.1f}% of windows profitable",
            f"  In-Sample CAGR       : {self.in_sample_cagr:+.2f}%",
            f"  Out-of-Sample CAGR   : {self.out_of_sample_cagr:+.2f}%",
            f"  Overfitting Ratio    : {self.overfitting_ratio:.2f} (1.0 = ideal)",
        ]
        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]Walk-Forward Validation[/bold cyan]",
                border_style="cyan",
            )
        )

        table = Table(title="Window Results", show_lines=False)
        table.add_column("Train Period", width=24)
        table.add_column("Test Period", width=24)
        table.add_column("Test Return", justify="right", width=12)
        table.add_column("Trades", justify="right", width=8)
        table.add_column("Win%", justify="right", width=8)

        for w in self.windows:
            ret_style = "green" if w.test_return >= 0 else "red"
            table.add_row(
                f"{w.train_start} → {w.train_end}",
                f"{w.test_start} → {w.test_end}",
                f"[{ret_style}]{w.test_return:+.2f}%[/{ret_style}]",
                str(w.test_trades),
                f"{w.test_win_rate:.1f}%",
            )
        console.print(table)


# ── Helper functions ──────────────────────────────────────────


def _equity_curve_from_pnl_pcts(pnl_pcts: list[float], initial: float = 100_000.0) -> list[float]:
    """Rebuild an equity curve by applying trade P&L percentages sequentially."""
    curve = [initial]
    capital = initial
    for p in pnl_pcts:
        capital *= 1 + p / 100
        curve.append(capital)
    return curve


def _cagr_from_equity(curve: list[float], years: float) -> float:
    """Compute CAGR from an equity curve and the number of years."""
    if years <= 0 or curve[0] <= 0:
        return 0.0
    return ((curve[-1] / curve[0]) ** (1 / years) - 1) * 100


def _sharpe_from_equity(curve: list[float]) -> float:
    """Compute annualised Sharpe from an equity curve (252-day convention)."""
    if len(curve) < 2:
        return 0.0
    import pandas as pd

    eq = pd.Series(curve)
    daily_ret = eq.pct_change(fill_method=None).dropna()
    if len(daily_ret) < 2 or daily_ret.std() == 0:
        return 0.0
    return float((daily_ret.mean() / daily_ret.std()) * math.sqrt(252))


def _max_drawdown_from_equity(curve: list[float]) -> float:
    """Compute maximum drawdown (%) from an equity curve."""
    if not curve:
        return 0.0
    import pandas as pd

    eq = pd.Series(curve)
    peak = eq.expanding().max()
    dd = (eq - peak) / peak * 100
    return float(dd.min())


def _years_from_result(result: BacktestResult) -> float:
    """Estimate number of years in a BacktestResult from start/end dates."""
    try:
        start = datetime.strptime(result.start_date[:10], "%Y-%m-%d")
        end = datetime.strptime(result.end_date[:10], "%Y-%m-%d")
        days = (end - start).days
        return max(days / 365.25, 1 / 365.25)
    except Exception:
        return 3.0


# ── MonteCarlo Engine ─────────────────────────────────────────


class MonteCarlo:
    """
    Monte Carlo simulation: shuffle trade order n_simulations times.

    Tests path-dependency — whether strategy performance depends on the
    *sequence* of trades, or just the distribution of returns.
    """

    def __init__(self, n_simulations: int = 1000, seed: int = 42) -> None:
        self.n_simulations = n_simulations
        self.seed = seed

    def run(self, result: BacktestResult) -> MonteCarloResult:
        """Shuffle trades n_simulations times and compute metric distributions."""
        if not result.trades:
            raise ValueError("BacktestResult has no trades — cannot run Monte Carlo simulation.")

        rng = np.random.default_rng(self.seed)
        pnl_pcts = np.array([t.pnl_pct for t in result.trades], dtype=float)
        years = _years_from_result(result)
        initial = 100_000.0

        sim_cagrs: list[float] = []
        sim_sharpes: list[float] = []
        sim_max_dds: list[float] = []
        equity_curves: list[list[float]] = []

        for _ in range(self.n_simulations):
            shuffled = rng.permutation(pnl_pcts).tolist()
            curve = _equity_curve_from_pnl_pcts(shuffled, initial)
            cagr = _cagr_from_equity(curve, years)
            sharpe = _sharpe_from_equity(curve)
            max_dd = _max_drawdown_from_equity(curve)

            sim_cagrs.append(cagr)
            sim_sharpes.append(sharpe)
            sim_max_dds.append(max_dd)
            equity_curves.append(curve)

        arr_cagr = np.array(sim_cagrs)
        arr_sharpe = np.array(sim_sharpes)
        arr_dd = np.array(sim_max_dds)

        prob_positive = float(np.mean(arr_cagr > 0))
        prob_beat_nifty = float(np.mean(arr_cagr > 12.0))

        return MonteCarloResult(
            n_simulations=self.n_simulations,
            original_cagr=result.cagr,
            original_sharpe=result.sharpe_ratio,
            original_max_drawdown=result.max_drawdown,
            cagr_p5=float(np.percentile(arr_cagr, 5)),
            cagr_p25=float(np.percentile(arr_cagr, 25)),
            cagr_p50=float(np.percentile(arr_cagr, 50)),
            cagr_p75=float(np.percentile(arr_cagr, 75)),
            cagr_p95=float(np.percentile(arr_cagr, 95)),
            sharpe_p5=float(np.percentile(arr_sharpe, 5)),
            sharpe_p50=float(np.percentile(arr_sharpe, 50)),
            sharpe_p95=float(np.percentile(arr_sharpe, 95)),
            max_dd_p5=float(np.percentile(arr_dd, 5)),
            max_dd_p50=float(np.percentile(arr_dd, 50)),
            max_dd_p95=float(np.percentile(arr_dd, 95)),
            prob_positive_return=prob_positive,
            prob_beat_nifty=prob_beat_nifty,
            equity_curves=equity_curves,
        )


# ── Bootstrap Engine ──────────────────────────────────────────


class Bootstrap:
    """
    Bootstrap resampling: resample trades WITH replacement n_samples times.

    Computes 95% confidence intervals for Sharpe and CAGR.
    """

    def __init__(self, n_samples: int = 1000, seed: int = 42) -> None:
        self.n_samples = n_samples
        self.seed = seed

    def run(self, result: BacktestResult) -> BootstrapResult:
        """Resample trades with replacement and compute metric CIs."""
        if not result.trades:
            raise ValueError("BacktestResult has no trades — cannot run Bootstrap resampling.")

        rng = np.random.default_rng(self.seed)
        pnl_pcts = np.array([t.pnl_pct for t in result.trades], dtype=float)
        n = len(pnl_pcts)
        years = _years_from_result(result)
        initial = 100_000.0

        sim_sharpes: list[float] = []
        sim_cagrs: list[float] = []

        for _ in range(self.n_samples):
            idxs = rng.integers(0, n, size=n)
            sample = pnl_pcts[idxs].tolist()
            curve = _equity_curve_from_pnl_pcts(sample, initial)
            sim_sharpes.append(_sharpe_from_equity(curve))
            sim_cagrs.append(_cagr_from_equity(curve, years))

        arr_sharpe = np.array(sim_sharpes)
        arr_cagr = np.array(sim_cagrs)

        sharpe_lo = float(np.percentile(arr_sharpe, 2.5))
        sharpe_hi = float(np.percentile(arr_sharpe, 97.5))
        cagr_lo = float(np.percentile(arr_cagr, 2.5))
        cagr_hi = float(np.percentile(arr_cagr, 97.5))

        # Significant if Sharpe CI doesn't straddle zero
        is_significant = sharpe_lo > 0 or sharpe_hi < 0

        return BootstrapResult(
            n_samples=self.n_samples,
            original_sharpe=result.sharpe_ratio,
            sharpe_ci_lower=sharpe_lo,
            sharpe_ci_upper=sharpe_hi,
            original_cagr=result.cagr,
            cagr_ci_lower=cagr_lo,
            cagr_ci_upper=cagr_hi,
            is_statistically_significant=is_significant,
        )


# ── WalkForward Engine ────────────────────────────────────────


class WalkForward:
    """
    Walk-Forward validation: rolling train/test windows.

    For each window, trains on `train_months` of data, then tests on
    `test_months` of out-of-sample data. Windows slide forward by
    `test_months` each step.
    """

    def __init__(self, train_months: int = 12, test_months: int = 3) -> None:
        self.train_months = train_months
        self.test_months = test_months

    def run(
        self,
        symbol: str,
        strategy,
        period: str = "3y",
        exchange: str = "NSE",
    ) -> WalkForwardResult:
        """
        Execute walk-forward validation.

        Splits the historical period into overlapping train/test windows.
        For each window calls Backtester.run() on the test slice.
        Windows with too few data points are skipped gracefully.
        """
        period_days = {
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "3y": 1095,
            "5y": 1825,
        }
        total_days = period_days.get(period, 1095)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=total_days)

        train_days = self.train_months * 30
        test_days = self.test_months * 30

        windows: list[WalkForwardWindow] = []
        train_results: list[BacktestResult] = []

        current = start_date
        while True:
            train_start = current
            train_end = current + timedelta(days=train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)

            if test_end > end_date:
                break

            # Approximate period string for the window lengths
            train_period = _days_to_period(train_days)
            test_period = _days_to_period(test_days)

            # Run backtest on TRAIN window
            try:
                bt_train = Backtester(symbol=symbol, exchange=exchange, period=train_period)
                bt_train._df = None  # will be loaded from date range
                train_result = _run_for_window(bt_train, strategy, train_start, train_end)
                train_results.append(train_result)
            except Exception:
                train_result = None

            # Run backtest on TEST window (out-of-sample)
            try:
                bt_test = Backtester(symbol=symbol, exchange=exchange, period=test_period)
                bt_test._df = None
                test_result = _run_for_window(bt_test, strategy, test_start, test_end)

                windows.append(
                    WalkForwardWindow(
                        train_start=train_start.strftime("%Y-%m-%d"),
                        train_end=train_end.strftime("%Y-%m-%d"),
                        test_start=test_start.strftime("%Y-%m-%d"),
                        test_end=test_end.strftime("%Y-%m-%d"),
                        test_return=test_result.total_return,
                        test_trades=test_result.total_trades,
                        test_win_rate=test_result.win_rate,
                    )
                )
            except Exception:
                # Skip windows with insufficient data
                pass

            current += timedelta(days=test_days)

        if not windows:
            raise RuntimeError(
                f"No valid walk-forward windows for {symbol} over {period}. "
                "Try a longer period or shorter window sizes."
            )

        avg_test_return = sum(w.test_return for w in windows) / len(windows)
        profitable_windows = sum(1 for w in windows if w.test_return > 0)
        consistency_ratio = profitable_windows / len(windows)

        in_sample_cagr = (
            sum(r.cagr for r in train_results) / len(train_results) if train_results else 0.0
        )
        out_of_sample_cagr = avg_test_return  # proxy: mean test window return

        if in_sample_cagr != 0:
            overfitting_ratio = out_of_sample_cagr / in_sample_cagr
        else:
            overfitting_ratio = 1.0

        return WalkForwardResult(
            windows=windows,
            avg_test_return=round(avg_test_return, 2),
            consistency_ratio=round(consistency_ratio, 4),
            in_sample_cagr=round(in_sample_cagr, 2),
            out_of_sample_cagr=round(out_of_sample_cagr, 2),
            overfitting_ratio=round(overfitting_ratio, 4),
        )


# ── Internal helpers ──────────────────────────────────────────


def _days_to_period(days: int) -> str:
    """Map an approximate number of days to a Backtester period string."""
    if days <= 35:
        return "1mo"
    if days <= 100:
        return "3mo"
    if days <= 200:
        return "6mo"
    if days <= 400:
        return "1y"
    if days <= 800:
        return "2y"
    if days <= 1200:
        return "3y"
    return "5y"


def _run_for_window(
    bt: Backtester,
    strategy,
    start: datetime,
    end: datetime,
) -> BacktestResult:
    """
    Run Backtester for a specific date window.

    Injects a date-filtered DataFrame into the Backtester so it only
    uses data in [start, end]. Falls back to bt.run() if the data
    loader doesn't support date-range filtering.
    """
    try:
        from market.history import get_ohlcv

        days = (end - start).days
        df = get_ohlcv(
            symbol=bt.symbol,
            exchange=bt.exchange,
            interval="day",
            days=days,
            from_date=start,
            to_date=end,
        )
        if df is not None and not df.empty:
            df = df.dropna(subset=["close"])
            # Clip to requested window
            df = df[df.index >= str(start.date())]
            df = df[df.index <= str(end.date())]
            if len(df) >= 5:
                bt._df = df
    except Exception:
        pass

    return bt.run(strategy)
