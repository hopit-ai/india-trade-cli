"""
engine/profile.py
─────────────────
Personal Trading Style Profile — learns from your actual trade outcomes.

Analyzes trade_memory to build a profile of:
  - Risk tolerance (conservative/moderate/aggressive)
  - Win rate by strategy, symbol, market regime
  - Behavioral patterns (cutting winners early, holding losers)
  - Preferred instruments and timeframes
  - Performance by VIX regime, FII flow direction
  - Personalized recommendations

Needs 5+ trade outcomes to start, gets more accurate with more data.

Usage:
    from engine.profile import build_profile, print_profile

    profile = build_profile()
    profile.print_profile()

    # Get context for LLM prompts
    context = profile.to_context()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class TradingProfile:
    """User's personal trading style derived from trade outcomes."""
    # Overview
    total_trades:     int = 0
    trades_with_outcome: int = 0
    overall_win_rate: float = 0.0
    total_pnl:        float = 0.0
    avg_pnl:           float = 0.0

    # Risk tolerance classification
    risk_class:       str = "UNKNOWN"     # CONSERVATIVE / MODERATE / AGGRESSIVE
    risk_score:       float = 50.0        # 0-100 (0=very conservative, 100=very aggressive)
    risk_reasoning:   str = ""

    # Win/loss characteristics
    avg_winner:       float = 0.0         # avg P&L of winning trades
    avg_loser:        float = 0.0         # avg P&L of losing trades (negative)
    win_loss_ratio:   float = 0.0         # avg_winner / abs(avg_loser)
    largest_win:      float = 0.0
    largest_loss:     float = 0.0

    # Behavioral patterns
    cuts_winners_early: bool = False       # avg winner < avg loser
    holds_losers_long:  bool = False       # avg losing hold > avg winning hold
    avg_win_hold:       float = 0.0        # avg hold days for winners
    avg_loss_hold:      float = 0.0        # avg hold days for losers

    # By market regime
    low_vix_win_rate:   float = 0.0        # VIX < 15
    mid_vix_win_rate:   float = 0.0        # VIX 15-20
    high_vix_win_rate:  float = 0.0        # VIX > 20
    best_vix_regime:    str = ""

    # By confidence level
    high_conf_win_rate: float = 0.0        # confidence > 70
    low_conf_win_rate:  float = 0.0        # confidence < 50
    min_useful_confidence: int = 50

    # Top symbols
    best_symbols:       list[dict] = field(default_factory=list)   # [{symbol, win_rate, trades}]
    worst_symbols:      list[dict] = field(default_factory=list)

    # Streaks
    current_streak:     int = 0            # positive = wins, negative = losses
    longest_win_streak: int = 0
    longest_loss_streak: int = 0

    # Recommendations
    recommendations:    list[str] = field(default_factory=list)

    def print_profile(self) -> None:
        if self.trades_with_outcome < 5:
            console.print(
                f"[dim]Need at least 5 trade outcomes for a profile "
                f"(have {self.trades_with_outcome}). "
                f"Use 'memory outcome <ID> WIN|LOSS [pnl]' to record results.[/dim]"
            )
            return

        risk_style = {
            "CONSERVATIVE": "green", "MODERATE": "yellow", "AGGRESSIVE": "red",
        }.get(self.risk_class, "white")
        pnl_style = "green" if self.total_pnl >= 0 else "red"

        lines = [
            f"  [bold]Overview[/bold]",
            f"  Trades         : {self.trades_with_outcome} with outcomes / {self.total_trades} total",
            f"  Win Rate       : {self.overall_win_rate:.0f}%",
            f"  Total P&L      : [{pnl_style}]{self.total_pnl:+,.0f}[/{pnl_style}]",
            f"  Avg P&L/Trade  : [{pnl_style}]{self.avg_pnl:+,.0f}[/{pnl_style}]",
            "",
            f"  [bold]Risk Profile[/bold]",
            f"  Classification : [{risk_style}]{self.risk_class}[/{risk_style}] (score: {self.risk_score:.0f}/100)",
            f"  {self.risk_reasoning}",
            "",
            f"  [bold]Win/Loss Characteristics[/bold]",
            f"  Avg Winner     : [green]{self.avg_winner:+,.0f}[/green]",
            f"  Avg Loser      : [red]{self.avg_loser:+,.0f}[/red]",
            f"  Win/Loss Ratio : {self.win_loss_ratio:.2f}x",
            f"  Largest Win    : [green]{self.largest_win:+,.0f}[/green]",
            f"  Largest Loss   : [red]{self.largest_loss:+,.0f}[/red]",
        ]

        # Behavioral warnings
        if self.cuts_winners_early:
            lines.append(f"\n  [yellow]! You cut winners early[/yellow] "
                         f"(avg win hold: {self.avg_win_hold:.0f}d vs avg loss hold: {self.avg_loss_hold:.0f}d)")
        if self.holds_losers_long:
            lines.append(f"  [yellow]! You hold losers too long[/yellow]")

        # VIX regime
        lines.extend([
            "",
            f"  [bold]By VIX Regime[/bold]",
            f"  Low (<15)  : {self.low_vix_win_rate:.0f}%",
            f"  Mid (15-20): {self.mid_vix_win_rate:.0f}%",
            f"  High (>20) : {self.high_vix_win_rate:.0f}%",
            f"  Best regime: {self.best_vix_regime}",
        ])

        # Confidence
        lines.extend([
            "",
            f"  [bold]By Confidence[/bold]",
            f"  High conf (>70) : {self.high_conf_win_rate:.0f}%",
            f"  Low conf (<50)  : {self.low_conf_win_rate:.0f}%",
            f"  Min useful conf : {self.min_useful_confidence}%",
        ])

        # Streaks
        lines.extend([
            "",
            f"  [bold]Streaks[/bold]",
            f"  Current        : {'W' if self.current_streak > 0 else 'L'}{abs(self.current_streak)}",
            f"  Longest Win    : W{self.longest_win_streak}",
            f"  Longest Loss   : L{self.longest_loss_streak}",
        ])

        console.print(Panel("\n".join(lines),
                            title="[bold cyan]Your Trading Profile[/bold cyan]",
                            border_style="cyan"))

        # Top/worst symbols
        if self.best_symbols:
            table = Table(title="Best Performing Symbols", show_lines=False)
            table.add_column("Symbol", style="bold", width=12)
            table.add_column("Win Rate", justify="right", width=10)
            table.add_column("Trades", justify="right", width=8)
            for s in self.best_symbols[:5]:
                table.add_row(s["symbol"], f"[green]{s['win_rate']:.0f}%[/green]", str(s["trades"]))
            console.print(table)

        if self.worst_symbols:
            table = Table(title="Worst Performing Symbols", show_lines=False)
            table.add_column("Symbol", style="bold", width=12)
            table.add_column("Win Rate", justify="right", width=10)
            table.add_column("Trades", justify="right", width=8)
            for s in self.worst_symbols[:5]:
                table.add_row(s["symbol"], f"[red]{s['win_rate']:.0f}%[/red]", str(s["trades"]))
            console.print(table)

        # Recommendations
        if self.recommendations:
            console.print("\n[bold]Personalized Recommendations:[/bold]")
            for r in self.recommendations:
                console.print(f"  - {r}")
            console.print()

    def to_context(self) -> str:
        """Generate text for LLM prompts."""
        if self.trades_with_outcome < 5:
            return "Insufficient trade history for a personal profile."

        parts = [
            f"Trader Profile (based on {self.trades_with_outcome} trades):",
            f"  Risk class: {self.risk_class} (score: {self.risk_score:.0f}/100)",
            f"  Win rate: {self.overall_win_rate:.0f}%",
            f"  Win/Loss ratio: {self.win_loss_ratio:.2f}x",
            f"  Best VIX regime: {self.best_vix_regime}",
            f"  Min useful confidence: {self.min_useful_confidence}%",
        ]
        if self.cuts_winners_early:
            parts.append("  WARNING: Tends to cut winners early")
        if self.holds_losers_long:
            parts.append("  WARNING: Tends to hold losers too long")
        if self.recommendations:
            parts.append("  Recommendations: " + "; ".join(self.recommendations[:3]))
        return "\n".join(parts)


def build_profile() -> TradingProfile:
    """Build a trading profile from trade_memory outcomes."""
    try:
        from engine.memory import trade_memory
    except ImportError:
        return TradingProfile()

    records = trade_memory._records
    with_outcome = [r for r in records if r.outcome]

    profile = TradingProfile(
        total_trades=len(records),
        trades_with_outcome=len(with_outcome),
    )

    if len(with_outcome) < 5:
        return profile

    # Basic stats
    wins = [r for r in with_outcome if r.outcome == "WIN"]
    losses = [r for r in with_outcome if r.outcome == "LOSS"]
    profile.overall_win_rate = len(wins) / len(with_outcome) * 100

    pnls = [r.actual_pnl for r in with_outcome if r.actual_pnl is not None]
    profile.total_pnl = sum(pnls)
    profile.avg_pnl = profile.total_pnl / len(pnls) if pnls else 0

    # Win/loss characteristics
    win_pnls = [r.actual_pnl for r in wins if r.actual_pnl is not None]
    loss_pnls = [r.actual_pnl for r in losses if r.actual_pnl is not None]

    profile.avg_winner = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    profile.avg_loser = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    profile.win_loss_ratio = (
        abs(profile.avg_winner / profile.avg_loser)
        if profile.avg_loser != 0 else float('inf')
    )
    profile.largest_win = max(win_pnls) if win_pnls else 0
    profile.largest_loss = min(loss_pnls) if loss_pnls else 0

    # Hold time analysis
    win_holds = [r.hold_days for r in wins if r.hold_days is not None]
    loss_holds = [r.hold_days for r in losses if r.hold_days is not None]
    profile.avg_win_hold = sum(win_holds) / len(win_holds) if win_holds else 0
    profile.avg_loss_hold = sum(loss_holds) / len(loss_holds) if loss_holds else 0

    # Behavioral patterns
    if profile.avg_winner and profile.avg_loser:
        profile.cuts_winners_early = abs(profile.avg_winner) < abs(profile.avg_loser) * 0.8
    if win_holds and loss_holds:
        profile.holds_losers_long = profile.avg_loss_hold > profile.avg_win_hold * 1.5

    # By VIX regime
    def _wr(subset):
        if not subset:
            return 0.0
        return sum(1 for r in subset if r.outcome == "WIN") / len(subset) * 100

    low_vix = [r for r in with_outcome if r.vix is not None and r.vix < 15]
    mid_vix = [r for r in with_outcome if r.vix is not None and 15 <= r.vix <= 20]
    high_vix = [r for r in with_outcome if r.vix is not None and r.vix > 20]

    profile.low_vix_win_rate = _wr(low_vix)
    profile.mid_vix_win_rate = _wr(mid_vix)
    profile.high_vix_win_rate = _wr(high_vix)

    rates = {"Low VIX (<15)": profile.low_vix_win_rate,
             "Mid VIX (15-20)": profile.mid_vix_win_rate,
             "High VIX (>20)": profile.high_vix_win_rate}
    profile.best_vix_regime = max(rates, key=rates.get) if any(rates.values()) else "N/A"

    # By confidence
    high_conf = [r for r in with_outcome if r.confidence > 70]
    low_conf = [r for r in with_outcome if r.confidence < 50]
    profile.high_conf_win_rate = _wr(high_conf)
    profile.low_conf_win_rate = _wr(low_conf)

    # Find minimum useful confidence
    for threshold in range(30, 80, 5):
        subset = [r for r in with_outcome if r.confidence >= threshold]
        if subset and _wr(subset) >= 55:
            profile.min_useful_confidence = threshold
            break

    # By symbol
    symbol_stats: dict[str, dict] = {}
    for r in with_outcome:
        if r.symbol not in symbol_stats:
            symbol_stats[r.symbol] = {"wins": 0, "total": 0}
        symbol_stats[r.symbol]["total"] += 1
        if r.outcome == "WIN":
            symbol_stats[r.symbol]["wins"] += 1

    symbol_data = [
        {"symbol": s, "win_rate": d["wins"] / d["total"] * 100, "trades": d["total"]}
        for s, d in symbol_stats.items() if d["total"] >= 2
    ]
    profile.best_symbols = sorted(symbol_data, key=lambda x: -x["win_rate"])[:5]
    profile.worst_symbols = sorted(symbol_data, key=lambda x: x["win_rate"])[:5]

    # Streaks
    streak = 0
    max_win = 0
    max_loss = 0
    cur_win = 0
    cur_loss = 0
    for r in with_outcome:
        if r.outcome == "WIN":
            cur_win += 1
            cur_loss = 0
            max_win = max(max_win, cur_win)
        else:
            cur_loss += 1
            cur_win = 0
            max_loss = max(max_loss, cur_loss)

    profile.current_streak = cur_win if cur_win > 0 else -cur_loss
    profile.longest_win_streak = max_win
    profile.longest_loss_streak = max_loss

    # Risk classification
    risk_score = 50.0
    if profile.overall_win_rate < 40:
        risk_score -= 15
    elif profile.overall_win_rate > 60:
        risk_score += 10
    if profile.win_loss_ratio > 2:
        risk_score += 15  # good R:R = can afford more risk
    elif profile.win_loss_ratio < 1:
        risk_score -= 15
    if profile.cuts_winners_early:
        risk_score -= 10
    if profile.holds_losers_long:
        risk_score -= 10
    if profile.high_vix_win_rate > 60:
        risk_score += 10  # performs well in volatile markets

    risk_score = max(0, min(100, risk_score))
    profile.risk_score = risk_score

    if risk_score >= 65:
        profile.risk_class = "AGGRESSIVE"
        profile.risk_reasoning = "Strong win rate and R:R supports larger positions"
    elif risk_score >= 40:
        profile.risk_class = "MODERATE"
        profile.risk_reasoning = "Balanced performance, standard position sizing recommended"
    else:
        profile.risk_class = "CONSERVATIVE"
        profile.risk_reasoning = "Lower win rate or behavioral issues — reduce position sizes"

    # Recommendations
    recs = []
    if profile.cuts_winners_early:
        recs.append("Let winners run longer — your avg winner is smaller than your avg loser. "
                     "Consider trailing stops instead of fixed targets.")
    if profile.holds_losers_long:
        recs.append("Cut losers faster — your avg losing hold is much longer than winning hold. "
                     "Use strict time-based or ATR-based stops.")
    if profile.low_conf_win_rate < 40 and profile.high_conf_win_rate > 55:
        recs.append(f"Only trade when confidence > {profile.min_useful_confidence}%. "
                     f"Low confidence trades are losing money.")
    if profile.best_vix_regime and "Low" in profile.best_vix_regime:
        recs.append("You perform best in low VIX. Reduce size in high-VIX regimes.")
    elif profile.best_vix_regime and "High" in profile.best_vix_regime:
        recs.append("You perform well in volatile markets — contrarian edge. "
                     "Consider increasing size when others are fearful.")
    if profile.longest_loss_streak >= 4:
        recs.append(f"You've had losing streaks of {profile.longest_loss_streak}. "
                     f"Consider a mandatory cooldown after 3 consecutive losses.")
    if not recs:
        recs.append("Keep doing what you're doing — consistent performance.")

    profile.recommendations = recs
    return profile


def print_profile() -> None:
    """Display trading profile."""
    profile = build_profile()
    profile.print_profile()
