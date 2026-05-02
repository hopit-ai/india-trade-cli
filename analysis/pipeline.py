"""
analysis/pipeline.py
────────────────────
Stage 1 of the two-stage analysis pipeline (#176).

Runs all 7 analyst agents deterministically (no LLM), packages their
results into an AnalysisContext, and produces a compact signal block
suitable for feeding into Stage 2 LLM prompts.

Key properties:
  - Zero LLM imports — this module is pure Python
  - compact_signals is ≤ 300 tokens regardless of analyst count
  - should_skip_debate flags high-agreement scenarios to skip 5 debate calls
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# ── Thresholds ───────────────────────────────────────────────

FAST_PATH_AGREEMENT_THRESHOLD: int = 75  # % analyst agreement to skip debate
FAST_PATH_SCORE_THRESHOLD: float = 25.0  # |weighted_total| to skip debate


# ── AnalysisContext ──────────────────────────────────────────


@dataclass
class AnalysisContext:
    """
    Immutable output of Stage 1. Fed into every Stage 2 LLM call.

    compact_signals replaces 7× AnalystReport.summary_text() in prompts.
    should_skip_debate=True means analysts strongly agree → skip 5 debate calls.
    """

    symbol: str
    exchange: str
    reports: list[Any]  # list[AnalystReport] — typed loosely to avoid circular
    scorecard: Any  # AnalystScorecard
    compact_signals: str  # pre-formatted table, ≤ 300 tokens
    should_skip_debate: bool  # True → fast-path synthesis
    ltp: float = 0.0  # last traded price (from TechnicalAnalyst data)


# ── Compact signal builder ───────────────────────────────────


def build_compact_signals(
    symbol: str,
    exchange: str,
    reports: list[Any],
    ltp: float,
) -> str:
    """
    Build the compact pre-computed signal block fed into all Stage 2 prompts.

    Replaces verbose summary_text() (~150 tokens per analyst × 7 = ~1,050 tokens)
    with a structured table (~200 tokens total).

    No LLM involved — pure string formatting.
    """
    from agent.multi_agent import compute_scorecard

    scorecard = compute_scorecard(reports)

    # Price header
    price_str = f"₹{ltp:,.2f}" if ltp else "N/A"
    lines = [
        f"SYMBOL: {symbol} ({exchange}) | Price: {price_str}",
        "",
        "PRE-COMPUTED SIGNALS — reference only, do not recompute:",
    ]

    # Signal rows — one line per analyst
    col_w = 18  # analyst name column width
    for r in reports:
        if r.error:
            lines.append(f"  {r.analyst:<{col_w}} FAILED ({r.error[:40]})")
            continue

        # Take first key metric line (or empty)
        metric = r.key_points[0] if r.key_points else ""
        if len(metric) > 38:
            metric = metric[:35] + "..."

        verdict_icon = {"BULLISH": "▲", "BEARISH": "▼", "NEUTRAL": "─"}.get(r.verdict, "?")
        lines.append(
            f"  {r.analyst:<{col_w}} {verdict_icon} {r.verdict:<8} "
            f"score:{r.score:+.0f}  conf:{r.confidence}%  {metric}"
        )

    # Scorecard summary
    lines.append("")
    lines.append(
        f"Scorecard: {scorecard.verdict} "
        f"(weighted: {scorecard.weighted_total:+.1f}, "
        f"agreement: {scorecard.agreement:.0f}%)"
    )

    # Conflicts (only if present)
    if scorecard.conflicts:
        lines.append(f"Conflicts: {' | '.join(scorecard.conflicts)}")
    else:
        lines.append("Conflicts: none (analysts agree)")

    return "\n".join(lines)


# ── Fast-path decision ───────────────────────────────────────


def should_use_fast_path(scorecard: Any) -> bool:
    """
    Return True when analysts agree strongly enough to skip the debate phase.

    Conditions (both must hold):
      1. agreement >= FAST_PATH_AGREEMENT_THRESHOLD  (e.g. 75% analysts same direction)
      2. |weighted_total| >= FAST_PATH_SCORE_THRESHOLD  (signal is not noise)
    """
    agreement_ok = scorecard.agreement >= FAST_PATH_AGREEMENT_THRESHOLD
    score_ok = abs(scorecard.weighted_total) >= FAST_PATH_SCORE_THRESHOLD
    return agreement_ok and score_ok


# ── Stage 1 entry point ──────────────────────────────────────


def run_analysis_pipeline(
    symbol: str,
    exchange: str,
    registry: Any,
    parallel: bool = True,
) -> AnalysisContext:
    """
    Run all 7 analyst agents deterministically and return an AnalysisContext.

    This is Stage 1 — no LLM involved. The AnalysisContext is then passed
    to MultiAgentAnalyzer for Stage 2 synthesis.

    Args:
        symbol:   Stock ticker (e.g. "RELIANCE")
        exchange: Exchange code (e.g. "NSE")
        registry: ToolRegistry instance with market data tools
        parallel: Run analysts in parallel threads (default True)

    Returns:
        AnalysisContext with pre-computed scores, compact_signals, and
        should_skip_debate flag.
    """
    from agent.multi_agent import (
        TechnicalAnalyst,
        FundamentalAnalyst,
        OptionsAnalyst,
        NewsMacroAnalyst,
        SentimentAnalyst,
        SectorRotationAnalyst,
        RiskAnalyst,
        compute_scorecard,
    )

    analysts = [
        TechnicalAnalyst(registry),
        FundamentalAnalyst(registry),
        OptionsAnalyst(registry),
        NewsMacroAnalyst(registry),  # keyword-mode, no LLM
        SentimentAnalyst(registry),
        SectorRotationAnalyst(registry),
        RiskAnalyst(registry),
    ]

    # Run analysts
    if parallel:
        reports = _run_parallel(analysts, symbol, exchange)
    else:
        reports = _run_sequential(analysts, symbol, exchange)

    # Scorecard
    scorecard = compute_scorecard(reports)

    # Extract LTP from TechnicalAnalyst data
    ltp = 0.0
    for r in reports:
        if r.analyst == "Technical" and not r.error:
            ltp = r.data.get("ltp", 0.0) or r.data.get("close", 0.0) or 0.0
            break

    # Compact signal block
    compact = build_compact_signals(symbol, exchange, reports, ltp)

    # Fast-path decision
    skip_debate = should_use_fast_path(scorecard)

    return AnalysisContext(
        symbol=symbol,
        exchange=exchange,
        reports=reports,
        scorecard=scorecard,
        compact_signals=compact,
        should_skip_debate=skip_debate,
        ltp=ltp,
    )


# ── Internal helpers ─────────────────────────────────────────


def _run_parallel(analysts: list[Any], symbol: str, exchange: str) -> list[Any]:
    """Run analysts concurrently using ThreadPoolExecutor."""
    import concurrent.futures

    reports: list[Any] = [None] * len(analysts)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(analysts)) as pool:
        futures = {pool.submit(a.analyze, symbol, exchange): i for i, a in enumerate(analysts)}
        for fut in concurrent.futures.as_completed(futures):
            idx = futures[fut]
            try:
                reports[idx] = fut.result()
            except Exception as exc:
                from agent.multi_agent import AnalystReport

                reports[idx] = AnalystReport(
                    analyst=analysts[idx].name,
                    verdict="UNKNOWN",
                    confidence=0,
                    score=0,
                    error=str(exc),
                )

    return reports


def _run_sequential(analysts: list[Any], symbol: str, exchange: str) -> list[Any]:
    """Run analysts one by one (used in tests / low-resource environments)."""
    from agent.multi_agent import AnalystReport

    reports = []
    for a in analysts:
        try:
            reports.append(a.analyze(symbol, exchange))
        except Exception as exc:
            reports.append(
                AnalystReport(
                    analyst=a.name,
                    verdict="UNKNOWN",
                    confidence=0,
                    score=0,
                    error=str(exc),
                )
            )
    return reports
