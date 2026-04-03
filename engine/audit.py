"""
engine/audit.py
───────────────
Decision audit trail — post-mortem analysis for trade outcomes.

When a trade wins or loses, answers:
  - Which analyst was right/wrong?
  - What if we had weighted differently?
  - Was it a setup failure or execution failure?
  - Could we have exited early with better SL logic?

Uses trade_memory records with outcomes.

Usage:
    from engine.audit import audit_trade, print_audit_report

    report = audit_trade("abc12345")   # trade ID from memory
    report.print_report()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class AuditReport:
    """Post-mortem analysis of a single trade."""

    trade_id: str
    symbol: str
    verdict: str  # what we recommended
    outcome: str  # what actually happened
    pnl: Optional[float] = None

    # Analyst accuracy
    analyst_grades: list[dict] = field(default_factory=list)
    # [{analyst, score_at_time, was_correct, grade}]
    most_accurate: str = ""
    most_wrong: str = ""

    # What-if analysis
    alt_verdict: str = ""  # what verdict would have been with different weights
    alt_would_help: bool = False

    # Execution analysis
    entry_quality: str = ""  # "GOOD" / "FAIR" / "POOR" (vs optimal)
    sl_assessment: str = ""  # "TOO_TIGHT" / "ADEQUATE" / "TOO_WIDE"
    hold_assessment: str = ""  # "TOO_SHORT" / "ADEQUATE" / "TOO_LONG"

    # Lessons
    lessons: list[str] = field(default_factory=list)

    def print_report(self) -> None:
        if not self.outcome:
            console.print(
                f"[dim]Trade {self.trade_id} has no outcome recorded. "
                f"Use: memory outcome {self.trade_id} WIN|LOSS [pnl][/dim]"
            )
            return

        pnl_style = "green" if (self.pnl or 0) >= 0 else "red"
        outcome_style = "green" if self.outcome == "WIN" else "red"

        lines = [
            f"  Trade ID  : {self.trade_id}",
            f"  Symbol    : {self.symbol}",
            f"  Verdict   : {self.verdict}",
            f"  Outcome   : [{outcome_style}]{self.outcome}[/{outcome_style}]",
        ]
        if self.pnl is not None:
            lines.append(f"  P&L       : [{pnl_style}]{self.pnl:+,.0f}[/{pnl_style}]")

        console.print(
            Panel("\n".join(lines), title="[bold cyan]Trade Audit[/bold cyan]", border_style="cyan")
        )

        # Analyst grades
        if self.analyst_grades:
            table = Table(title="Analyst Grades", show_lines=False)
            table.add_column("Analyst", style="bold", width=18)
            table.add_column("Score", justify="right", width=8)
            table.add_column("Direction", width=10)
            table.add_column("Correct?", width=10)
            table.add_column("Grade", width=8)

            for ag in self.analyst_grades:
                correct_style = "green" if ag.get("was_correct") else "red"
                direction = (
                    "BULLISH"
                    if ag.get("score_at_time", 0) > 0
                    else "BEARISH"
                    if ag.get("score_at_time", 0) < 0
                    else "NEUTRAL"
                )
                table.add_row(
                    ag.get("analyst", ""),
                    f"{ag.get('score_at_time', 0):+.0f}",
                    direction,
                    f"[{correct_style}]{'YES' if ag.get('was_correct') else 'NO'}[/{correct_style}]",
                    ag.get("grade", ""),
                )

            console.print(table)
            if self.most_accurate:
                console.print(f"  Most accurate : [green]{self.most_accurate}[/green]")
            if self.most_wrong:
                console.print(f"  Most wrong    : [red]{self.most_wrong}[/red]")

        # Execution analysis
        if any([self.entry_quality, self.sl_assessment, self.hold_assessment]):
            console.print("\n[bold]Execution Analysis:[/bold]")
            if self.entry_quality:
                console.print(f"  Entry     : {self.entry_quality}")
            if self.sl_assessment:
                console.print(f"  Stop-Loss : {self.sl_assessment}")
            if self.hold_assessment:
                console.print(f"  Hold Time : {self.hold_assessment}")

        # What-if
        if self.alt_verdict:
            console.print("\n[bold]What-If:[/bold]")
            console.print(f"  With equal weights: {self.alt_verdict}")
            help_str = (
                "[green]YES — would have helped[/green]"
                if self.alt_would_help
                else "[dim]NO — same outcome[/dim]"
            )
            console.print(f"  Would it help?    : {help_str}")

        # Lessons
        if self.lessons:
            console.print("\n[bold]Lessons:[/bold]")
            for l in self.lessons:
                console.print(f"  - {l}")


def audit_trade(trade_id: str) -> AuditReport:
    """
    Run a post-mortem audit on a specific trade from memory.
    """
    try:
        from engine.memory import trade_memory
    except ImportError:
        return AuditReport(trade_id=trade_id, symbol="", verdict="", outcome="")

    record = trade_memory.get_by_id(trade_id)
    if not record:
        return AuditReport(
            trade_id=trade_id,
            symbol="?",
            verdict="?",
            outcome="",
            lessons=[f"Trade ID '{trade_id}' not found in memory"],
        )

    report = AuditReport(
        trade_id=trade_id,
        symbol=record.symbol,
        verdict=record.verdict,
        outcome=record.outcome or "",
        pnl=record.actual_pnl,
    )

    if not record.outcome:
        return report

    is_win = record.outcome == "WIN"
    is_buy = record.verdict in ("BUY", "STRONG_BUY")
    is_sell = record.verdict in ("SELL", "STRONG_SELL")

    # Grade each analyst
    if record.analyst_scores:
        for analyst, score in record.analyst_scores.items():
            was_bullish = score > 0
            was_bearish = score < 0

            # Was this analyst correct?
            if is_buy:
                was_correct = (was_bullish and is_win) or (was_bearish and not is_win)
            elif is_sell:
                was_correct = (was_bearish and is_win) or (was_bullish and not is_win)
            else:
                was_correct = abs(score) < 20  # neutral verdict, low score = correct

            # Grade
            if was_correct and abs(score) > 30:
                grade = "A"
            elif was_correct:
                grade = "B"
            elif abs(score) < 10:
                grade = "C"  # neutral, hard to be wrong
            elif not was_correct and abs(score) > 30:
                grade = "F"
            else:
                grade = "D"

            report.analyst_grades.append(
                {
                    "analyst": analyst,
                    "score_at_time": score,
                    "was_correct": was_correct,
                    "grade": grade,
                }
            )

        # Find best/worst
        correct_analysts = [a for a in report.analyst_grades if a["was_correct"]]
        wrong_analysts = [a for a in report.analyst_grades if not a["was_correct"]]

        if correct_analysts:
            best = max(correct_analysts, key=lambda x: abs(x["score_at_time"]))
            report.most_accurate = best["analyst"]
        if wrong_analysts:
            worst = max(wrong_analysts, key=lambda x: abs(x["score_at_time"]))
            report.most_wrong = worst["analyst"]

    # What-if: equal weights
    if record.analyst_scores:
        avg_score = sum(record.analyst_scores.values()) / len(record.analyst_scores)
        if avg_score > 10:
            report.alt_verdict = "BUY"
        elif avg_score < -10:
            report.alt_verdict = "SELL"
        else:
            report.alt_verdict = "HOLD"

        # Would equal weights have helped?
        if is_win:
            report.alt_would_help = report.alt_verdict == record.verdict
        else:
            report.alt_would_help = report.alt_verdict != record.verdict

    # Hold time assessment
    if record.hold_days is not None:
        if record.hold_days <= 1 and not is_win:
            report.hold_assessment = "TOO_SHORT — may have exited prematurely"
        elif record.hold_days > 30 and not is_win:
            report.hold_assessment = "TOO_LONG — should have cut losses earlier"
        else:
            report.hold_assessment = "ADEQUATE"

    # Lessons
    if not is_win:
        if report.most_wrong:
            wrong_score = next(
                (
                    a["score_at_time"]
                    for a in report.analyst_grades
                    if a["analyst"] == report.most_wrong
                ),
                0,
            )
            report.lessons.append(
                f"{report.most_wrong} was strongly wrong (score: {wrong_score:+.0f}). "
                f"Consider reducing its weight in similar setups."
            )

        if record.confidence and record.confidence < 50:
            report.lessons.append(
                f"Low confidence trade ({record.confidence}%). "
                f"Consider setting a minimum confidence threshold (e.g. 60%)."
            )

        if record.vix and record.vix > 18:
            report.lessons.append(
                f"Trade was taken in high VIX ({record.vix:.1f}). "
                f"Review whether high-VIX trades should use tighter stops."
            )

    if is_win and report.most_accurate:
        report.lessons.append(
            f"{report.most_accurate} was the key signal. "
            f"Similar setups in the future should weight this analyst higher."
        )

    return report


def audit_all() -> list[AuditReport]:
    """Audit all trades with outcomes."""
    try:
        from engine.memory import trade_memory

        records = [r for r in trade_memory._records if r.outcome]
        return [audit_trade(r.id) for r in records]
    except Exception:
        return []


def print_audit(trade_id: str) -> None:
    """Display audit for a single trade."""
    report = audit_trade(trade_id)
    report.print_report()
