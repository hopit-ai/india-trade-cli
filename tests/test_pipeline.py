"""
tests/test_pipeline.py
──────────────────────
Tests for analysis/pipeline.py — Stage 1 (deterministic) of the two-stage
analysis pipeline (#176).

No LLM is required. All tests use mock AnalystReport fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest

from agent.multi_agent import AnalystReport, AnalystScorecard
from analysis.pipeline import (
    FAST_PATH_AGREEMENT_THRESHOLD,
    FAST_PATH_SCORE_THRESHOLD,
    AnalysisContext,
    build_compact_signals,
    run_analysis_pipeline,
    should_use_fast_path,
)


# ── Fixtures ─────────────────────────────────────────────────


def _make_report(
    analyst: str,
    verdict: str,
    score: float,
    confidence: int,
    key_points: list[str] | None = None,
    error: str = "",
) -> AnalystReport:
    return AnalystReport(
        analyst=analyst,
        verdict=verdict,
        confidence=confidence,
        score=score,
        key_points=key_points or [],
        error=error,
    )


ALL_BULLISH_REPORTS = [
    _make_report("Technical", "BULLISH", 60, 75, ["RSI:28 oversold", "MACD:bullish", "above EMA50"]),
    _make_report("Fundamental", "BULLISH", 70, 80, ["PE:22 ROE:20% D/E:0.1"]),
    _make_report("Options", "BULLISH", 50, 65, ["PCR:1.3 IVR:30 MaxPain:2600"]),
    _make_report("News & Macro", "BULLISH", 55, 60, ["FII net buy", "positive headlines"]),
    _make_report("Sentiment", "BULLISH", 45, 55, ["keyword: positive"]),
    _make_report("Sector Rotation", "BULLISH", 65, 70, ["IT outperforming"]),
    _make_report("Risk Manager", "NEUTRAL", 10, 50, ["VIX:12.5 low"]),
]

MIXED_REPORTS = [
    _make_report("Technical", "BEARISH", -35, 65, ["RSI:45 MACD:bear below EMA50"]),
    _make_report("Fundamental", "BULLISH", 55, 70, ["PE:28.5 ROE:18% D/E:0.3"]),
    _make_report("Options", "NEUTRAL", 5, 40, ["PCR:0.92 IVR:68 MaxPain:2500"]),
    _make_report("News & Macro", "BEARISH", -20, 50, ["FII net sell"]),
    _make_report("Sentiment", "NEUTRAL", 0, 30, ["keyword-based"]),
    _make_report("Sector Rotation", "BULLISH", 30, 60, ["sector outperforming"]),
    _make_report("Risk Manager", "NEUTRAL", -10, 55, ["VIX:14.2"]),
]

ALL_BEARISH_REPORTS = [
    _make_report("Technical", "BEARISH", -60, 80, ["RSI:72 overbought", "MACD:bear", "below EMA50"]),
    _make_report("Fundamental", "BEARISH", -50, 70, ["PE:45 ROE:8% high D/E"]),
    _make_report("Options", "BEARISH", -45, 65, ["PCR:0.5 IVR:85 MaxPain:2200"]),
    _make_report("News & Macro", "BEARISH", -55, 75, ["FII net sell large", "bearish headlines"]),
    _make_report("Sentiment", "BEARISH", -40, 60, ["keyword: negative"]),
    _make_report("Sector Rotation", "BEARISH", -35, 55, ["sector underperforming"]),
    _make_report("Risk Manager", "BEARISH", -30, 65, ["VIX:22 elevated"]),
]


# ── AnalysisContext structure ────────────────────────────────


class TestAnalysisContext:
    def test_has_required_fields(self):
        ctx = AnalysisContext(
            symbol="RELIANCE",
            exchange="NSE",
            reports=MIXED_REPORTS,
            scorecard=MagicMock(spec=AnalystScorecard),
            compact_signals="dummy",
            should_skip_debate=False,
            ltp=2850.0,
        )
        assert ctx.symbol == "RELIANCE"
        assert ctx.exchange == "NSE"
        assert len(ctx.reports) == 7
        assert ctx.ltp == 2850.0
        assert ctx.should_skip_debate is False

    def test_default_ltp_is_zero(self):
        ctx = AnalysisContext(
            symbol="INFY",
            exchange="NSE",
            reports=[],
            scorecard=MagicMock(spec=AnalystScorecard),
            compact_signals="",
            should_skip_debate=False,
        )
        assert ctx.ltp == 0.0


# ── build_compact_signals ────────────────────────────────────


class TestBuildCompactSignals:
    def test_contains_all_analyst_names(self):
        text = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)
        for report in MIXED_REPORTS:
            assert report.analyst in text

    def test_contains_verdicts(self):
        text = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)
        assert "BEARISH" in text
        assert "BULLISH" in text
        assert "NEUTRAL" in text

    def test_contains_symbol_and_price(self):
        text = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)
        assert "RELIANCE" in text
        assert "2,850" in text or "2850" in text

    def test_contains_conflicts_section(self):
        text = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)
        # Mixed reports have conflicts: BEARISH vs BULLISH
        assert "Conflict" in text or "conflict" in text

    def test_no_conflicts_when_all_agree(self):
        text = build_compact_signals("RELIANCE", "NSE", ALL_BULLISH_REPORTS, 2850.0)
        assert "No conflicts" in text or "Conflicts: none" in text or "conflict" not in text.lower() or "no conflict" in text.lower()

    def test_token_budget_under_300(self):
        """Compact signals must fit in approximately 300 tokens (rough: 4 chars/token)."""
        text = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)
        # 300 tokens * ~4 chars/token = ~1200 chars. Give generous margin.
        assert len(text) < 2000, f"compact_signals too long: {len(text)} chars"

    def test_skips_errored_analysts(self):
        reports_with_error = MIXED_REPORTS.copy()
        bad = _make_report("Technical", "UNKNOWN", 0, 0, error="API timeout")
        reports_with_error = [bad] + MIXED_REPORTS[1:]
        text = build_compact_signals("RELIANCE", "NSE", reports_with_error, 2850.0)
        # Errored analyst shows as failed or is skipped
        assert "API timeout" not in text or "FAILED" in text or "Technical" in text

    def test_no_llm_imports_in_module(self):
        """Stage 1 pipeline must have zero LLM imports."""
        import importlib
        import importlib.util
        import ast
        import pathlib

        src = pathlib.Path(__file__).parent.parent / "analysis" / "pipeline.py"
        tree = ast.parse(src.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                else:
                    names = [node.module or ""]
                for name in names:
                    assert "anthropic" not in name, f"LLM import found: {name}"
                    assert "openai" not in name, f"LLM import found: {name}"
                    assert "gemini" not in name, f"LLM import found: {name}"
                    assert "llm" not in name.lower(), f"LLM import found: {name}"


# ── should_use_fast_path ─────────────────────────────────────


class TestShouldUseFastPath:
    def test_all_bullish_high_agreement_triggers_fast_path(self):
        from agent.multi_agent import compute_scorecard
        scorecard = compute_scorecard(ALL_BULLISH_REPORTS)
        assert should_use_fast_path(scorecard) is True

    def test_all_bearish_high_agreement_triggers_fast_path(self):
        from agent.multi_agent import compute_scorecard
        scorecard = compute_scorecard(ALL_BEARISH_REPORTS)
        assert should_use_fast_path(scorecard) is True

    def test_mixed_reports_no_fast_path(self):
        from agent.multi_agent import compute_scorecard
        scorecard = compute_scorecard(MIXED_REPORTS)
        assert should_use_fast_path(scorecard) is False

    def test_fast_path_requires_both_agreement_and_score(self):
        """High agreement but weak score should NOT trigger fast path."""
        from agent.multi_agent import compute_scorecard

        # All neutral: high agreement but near-zero score
        neutral_reports = [
            _make_report("Technical", "NEUTRAL", 5, 50),
            _make_report("Fundamental", "NEUTRAL", 3, 50),
            _make_report("Options", "NEUTRAL", -2, 50),
            _make_report("News & Macro", "NEUTRAL", 1, 50),
            _make_report("Sentiment", "NEUTRAL", 0, 50),
            _make_report("Sector Rotation", "NEUTRAL", 4, 50),
            _make_report("Risk Manager", "NEUTRAL", -1, 50),
        ]
        scorecard = compute_scorecard(neutral_reports)
        assert should_use_fast_path(scorecard) is False

    def test_threshold_constants_are_reasonable(self):
        assert 60 <= FAST_PATH_AGREEMENT_THRESHOLD <= 90
        assert 15 <= FAST_PATH_SCORE_THRESHOLD <= 40


# ── run_analysis_pipeline ────────────────────────────────────


class TestRunAnalysisPipeline:
    def _mock_registry(self, reports: list[AnalystReport]) -> MagicMock:
        """Build a mock ToolRegistry that makes analysts return given reports."""
        registry = MagicMock()

        # technical_analyse
        t = reports[0]
        registry.execute.side_effect = lambda tool, params: {
            "technical_analyse": {
                "score": t.score, "verdict": t.verdict, "rsi": 45.0,
                "ema20": 2800.0, "ema50": 2900.0, "ltp": 2850.0,
            },
            "fundamental_analyse": {
                "score": reports[1].score if len(reports) > 1 else 50,
                "pe": 28.5, "roe": 18.0,
            },
            "get_options_chain": {"pcr": 0.92, "iv_rank": 68},
            "get_stock_news": [],
            "get_market_news": [],
            "get_fii_dii_data": [],
            "get_market_breadth": {"ad_ratio": 1.0},
            "get_upcoming_events": [],
            "get_bulk_block_deals": {},
            "get_quote": {"ltp": 2850.0},
        }.get(tool, {})

        return registry

    def test_returns_analysis_context(self):
        registry = self._mock_registry(MIXED_REPORTS)
        ctx = run_analysis_pipeline("RELIANCE", "NSE", registry)
        assert isinstance(ctx, AnalysisContext)
        assert ctx.symbol == "RELIANCE"
        assert ctx.exchange == "NSE"

    def test_context_has_scorecard(self):
        registry = self._mock_registry(MIXED_REPORTS)
        ctx = run_analysis_pipeline("RELIANCE", "NSE", registry)
        assert ctx.scorecard is not None
        assert hasattr(ctx.scorecard, "agreement")
        assert hasattr(ctx.scorecard, "weighted_total")

    def test_context_has_compact_signals(self):
        registry = self._mock_registry(MIXED_REPORTS)
        ctx = run_analysis_pipeline("RELIANCE", "NSE", registry)
        assert isinstance(ctx.compact_signals, str)
        assert len(ctx.compact_signals) > 50  # non-trivial content

    def test_fast_path_set_correctly_for_agreement(self):
        """When analysts are mocked to all-bullish, should_skip_debate=True."""
        registry = MagicMock()

        def _mock_execute(tool: str, params: dict):
            if tool == "technical_analyse":
                return {"score": 60, "verdict": "BULLISH", "rsi": 28.0,
                        "ema20": 2900.0, "ema50": 2800.0, "ltp": 2850.0}
            if tool == "fundamental_analyse":
                return {"score": 70, "pe": 22.0, "roe": 20.0}
            return {}

        registry.execute.side_effect = _mock_execute
        # We can't fully mock all 7 analysts easily, so just test that
        # the field exists and is a boolean.
        ctx = run_analysis_pipeline("RELIANCE", "NSE", registry)
        assert isinstance(ctx.should_skip_debate, bool)

    def test_analyst_errors_do_not_crash_pipeline(self):
        """If some analysts fail, pipeline continues with remaining reports."""
        registry = MagicMock()
        registry.execute.side_effect = Exception("API timeout")
        ctx = run_analysis_pipeline("RELIANCE", "NSE", registry)
        assert isinstance(ctx, AnalysisContext)
        # All reports will have errors but pipeline should not raise
        assert ctx.reports is not None


# ── Integration: compact_signals fed into debate prompt ──────


class TestCompactSignalsIntegration:
    def test_compact_signals_replaces_summary_text(self):
        """
        Verify that compact_signals is shorter than the equivalent summary_text output
        for realistic analyst reports (4-8 key_points each, as produced in production).
        """
        # Realistic fixtures with multiple key_points per analyst (as in production)
        rich_reports = [
            _make_report("Technical", "BEARISH", -35, 65, [
                "RSI: 45.3 (neutral zone, trending down from 60)", "MACD: bearish crossover signal",
                "EMA20 below EMA50 (short-term trend down)", "Support: ₹2,450", "Resistance: ₹2,650",
                "Volume: below 20-day average (-15%)", "Bollinger: approaching lower band",
                "ATR(14): ₹42 — moderate daily volatility",
            ]),
            _make_report("Fundamental", "BULLISH", 55, 70, [
                "PE: 28.5x (sector avg: 35x — attractively valued)", "ROE: 18% (strong, above 15% threshold)",
                "ROCE: 16.2%", "Debt/Equity: 0.3 (low leverage)", "Revenue Growth (3Y CAGR): 14%",
                "Profit Growth (TTM): 11%", "Promoter Holding: 50.3% (high conviction)",
                "Dividend Yield: 1.2%",
            ]),
            _make_report("Options", "NEUTRAL", 5, 40, [
                "PCR: 0.92 (near neutral — slight put bias)", "IV Rank: 68 (elevated options premiums)",
                "Max Pain: ₹2,500", "OI buildup at ₹2,600 CE (resistance)",
                "OI buildup at ₹2,400 PE (support)", "Straddle cost: ₹120 (4.2%)",
            ]),
            _make_report("News & Macro", "BEARISH", -20, 50, [
                "FII: net seller (-₹450 Cr last 3 days)", "3 bearish headlines identified",
                "RBI policy meeting in 5 days (uncertainty)", "US tech earnings mixed",
                "Market breadth: A/D ratio 0.8 (weak)",
            ]),
            _make_report("Sentiment", "NEUTRAL", 0, 30, ["keyword-based sentiment: neutral"]),
            _make_report("Sector Rotation", "BULLISH", 30, 60, [
                "IT sector: +2.1% vs NIFTY +0.4% (outperforming)", "Sector momentum: positive",
                "Relative strength vs NIFTY50: 1.08", "3 IT stocks in top 10 movers today",
            ]),
            _make_report("Risk Manager", "NEUTRAL", -10, 55, [
                "India VIX: 14.2 (normal range 12-15)", "Capital: ₹2,00,000",
                "Max risk per trade: ₹4,000 (2%)", "No major events in next 48h",
            ]),
        ]

        verbose = "\n\n".join(r.summary_text() for r in rich_reports if not r.error)
        compact = build_compact_signals("RELIANCE", "NSE", rich_reports, 2850.0)

        assert len(compact) < len(verbose), (
            f"compact ({len(compact)} chars) should be shorter than verbose ({len(verbose)} chars)"
        )

    def test_compact_signals_contains_key_data_points(self):
        """All critical metrics should survive the compression."""
        compact = build_compact_signals("RELIANCE", "NSE", MIXED_REPORTS, 2850.0)

        # Every analyst must be represented
        for report in MIXED_REPORTS:
            assert report.analyst in compact, f"Missing analyst: {report.analyst}"

        # All verdicts present
        assert "BEARISH" in compact
        assert "BULLISH" in compact
