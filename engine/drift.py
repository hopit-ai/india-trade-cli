"""
engine/drift.py
───────────────
Model drift detection — tracks whether analysis accuracy is degrading.

Detects:
  - Win rate declining over time
  - Analyst accuracy per VIX regime
  - Analyst disagreement patterns
  - Strategy performance decay

Requires trade outcomes in trade_memory (engine/memory.py).

Usage:
    from engine.drift import detect_drift, print_drift_report
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class DriftReport:
    """Model drift analysis results."""
    total_trades:       int = 0
    trades_with_outcome: int = 0

    # Win rate trend
    recent_win_rate:    float = 0.0      # last 10 trades
    older_win_rate:     float = 0.0      # trades before last 10
    win_rate_trend:     str = "STABLE"   # IMPROVING / DECLINING / STABLE
    win_rate_delta:     float = 0.0      # recent - older

    # By VIX regime
    low_vix_win_rate:   float = 0.0      # VIX < 15
    high_vix_win_rate:  float = 0.0      # VIX > 18
    best_vix_regime:    str = ""

    # By verdict type
    buy_accuracy:       float = 0.0
    sell_accuracy:      float = 0.0
    hold_accuracy:      float = 0.0

    # Analyst-level drift
    analyst_accuracy:   dict = field(default_factory=dict)  # analyst → win rate when they were bullish
    worst_analyst:      str = ""
    best_analyst:       str = ""

    # Alerts
    alerts:             list[str] = field(default_factory=list)

    def print_report(self) -> None:
        if self.trades_with_outcome < 5:
            console.print(
                f"[dim]Need at least 5 trade outcomes for drift analysis "
                f"(have {self.trades_with_outcome}). "
                f"Use 'memory outcome <ID> WIN|LOSS' to record results.[/dim]"
            )
            return

        trend_style = {
            "IMPROVING": "green", "DECLINING": "red", "STABLE": "yellow",
        }.get(self.win_rate_trend, "white")

        lines = [
            f"  Trades Analyzed   : {self.trades_with_outcome} / {self.total_trades}",
            "",
            f"  [bold]Win Rate Trend[/bold]",
            f"  Recent (last 10)  : {self.recent_win_rate:.0f}%",
            f"  Older             : {self.older_win_rate:.0f}%",
            f"  Trend             : [{trend_style}]{self.win_rate_trend} ({self.win_rate_delta:+.0f}%)[/{trend_style}]",
            "",
            f"  [bold]By VIX Regime[/bold]",
            f"  Low VIX (<15)     : {self.low_vix_win_rate:.0f}%",
            f"  High VIX (>18)    : {self.high_vix_win_rate:.0f}%",
            f"  Best regime       : {self.best_vix_regime}",
            "",
            f"  [bold]By Verdict[/bold]",
            f"  BUY accuracy      : {self.buy_accuracy:.0f}%",
            f"  SELL accuracy     : {self.sell_accuracy:.0f}%",
        ]

        if self.best_analyst:
            lines.extend([
                "",
                f"  [bold]Analyst Accuracy[/bold]",
                f"  Best analyst      : [green]{self.best_analyst}[/green]",
                f"  Worst analyst     : [red]{self.worst_analyst}[/red]",
            ])

        console.print(Panel("\n".join(lines),
                            title="[bold cyan]Model Drift Report[/bold cyan]",
                            border_style="cyan"))

        if self.analyst_accuracy:
            table = Table(title="Analyst Accuracy (when they were bullish, did stock go up?)")
            table.add_column("Analyst", style="bold", width=18)
            table.add_column("Accuracy", justify="right", width=10)
            table.add_column("Trades", justify="right", width=8)

            for analyst, data in sorted(self.analyst_accuracy.items(),
                                        key=lambda x: -x[1].get("accuracy", 0)):
                acc = data.get("accuracy", 0)
                n = data.get("count", 0)
                style = "green" if acc >= 60 else "red" if acc < 40 else "yellow"
                table.add_row(analyst, f"[{style}]{acc:.0f}%[/{style}]", str(n))
            console.print(table)

        if self.alerts:
            console.print("\n[bold yellow]Drift Alerts:[/bold yellow]")
            for a in self.alerts:
                console.print(f"  [yellow]! {a}[/yellow]")


def detect_drift() -> DriftReport:
    """Analyze trade memory for model drift."""
    try:
        from engine.memory import trade_memory
    except ImportError:
        return DriftReport()

    records = trade_memory._records
    with_outcome = [r for r in records if r.outcome]
    report = DriftReport(
        total_trades=len(records),
        trades_with_outcome=len(with_outcome),
    )

    if len(with_outcome) < 5:
        return report

    # Win rate trend
    wins = [r for r in with_outcome if r.outcome == "WIN"]
    overall_wr = len(wins) / len(with_outcome) * 100

    recent = with_outcome[-10:]
    older = with_outcome[:-10] if len(with_outcome) > 10 else []

    recent_wins = sum(1 for r in recent if r.outcome == "WIN")
    report.recent_win_rate = recent_wins / len(recent) * 100 if recent else 0

    if older:
        older_wins = sum(1 for r in older if r.outcome == "WIN")
        report.older_win_rate = older_wins / len(older) * 100
    else:
        report.older_win_rate = report.recent_win_rate

    report.win_rate_delta = report.recent_win_rate - report.older_win_rate
    if report.win_rate_delta > 10:
        report.win_rate_trend = "IMPROVING"
    elif report.win_rate_delta < -10:
        report.win_rate_trend = "DECLINING"
    else:
        report.win_rate_trend = "STABLE"

    # By VIX regime
    low_vix = [r for r in with_outcome if r.vix is not None and r.vix < 15]
    high_vix = [r for r in with_outcome if r.vix is not None and r.vix > 18]

    if low_vix:
        report.low_vix_win_rate = sum(1 for r in low_vix if r.outcome == "WIN") / len(low_vix) * 100
    if high_vix:
        report.high_vix_win_rate = sum(1 for r in high_vix if r.outcome == "WIN") / len(high_vix) * 100

    if report.low_vix_win_rate > report.high_vix_win_rate:
        report.best_vix_regime = "Low VIX (<15)"
    elif report.high_vix_win_rate > report.low_vix_win_rate:
        report.best_vix_regime = "High VIX (>18)"
    else:
        report.best_vix_regime = "No difference"

    # By verdict
    buys = [r for r in with_outcome if r.verdict in ("BUY", "STRONG_BUY")]
    sells = [r for r in with_outcome if r.verdict in ("SELL", "STRONG_SELL")]

    if buys:
        report.buy_accuracy = sum(1 for r in buys if r.outcome == "WIN") / len(buys) * 100
    if sells:
        report.sell_accuracy = sum(1 for r in sells if r.outcome == "WIN") / len(sells) * 100

    # Analyst-level accuracy
    analyst_stats: dict[str, dict] = {}
    for r in with_outcome:
        if not r.analyst_scores:
            continue
        for analyst, score in r.analyst_scores.items():
            if analyst not in analyst_stats:
                analyst_stats[analyst] = {"correct": 0, "total": 0}
            analyst_stats[analyst]["total"] += 1
            # "Correct" = analyst was bullish (score > 0) and outcome was WIN,
            # or analyst was bearish (score < 0) and outcome was LOSS
            if (score > 0 and r.outcome == "WIN") or (score < 0 and r.outcome == "LOSS"):
                analyst_stats[analyst]["correct"] += 1

    for analyst, stats in analyst_stats.items():
        acc = stats["correct"] / stats["total"] * 100 if stats["total"] > 0 else 0
        report.analyst_accuracy[analyst] = {"accuracy": round(acc, 1), "count": stats["total"]}

    if report.analyst_accuracy:
        best = max(report.analyst_accuracy.items(), key=lambda x: x[1]["accuracy"])
        worst = min(report.analyst_accuracy.items(), key=lambda x: x[1]["accuracy"])
        report.best_analyst = best[0]
        report.worst_analyst = worst[0]

    # Alerts
    if report.win_rate_trend == "DECLINING" and report.win_rate_delta < -15:
        report.alerts.append(
            f"Win rate declining sharply: {report.older_win_rate:.0f}% → {report.recent_win_rate:.0f}%"
        )

    if report.worst_analyst and report.analyst_accuracy.get(report.worst_analyst, {}).get("accuracy", 50) < 35:
        report.alerts.append(
            f"{report.worst_analyst} analyst accuracy below 35% — consider reducing its weight"
        )

    if report.buy_accuracy > 0 and report.buy_accuracy < 40:
        report.alerts.append(
            f"BUY signals only {report.buy_accuracy:.0f}% accurate — model may be too bullish"
        )

    return report


def print_drift_report() -> None:
    """Display drift analysis."""
    report = detect_drift()
    report.print_report()
