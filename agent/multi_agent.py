"""
agent/multi_agent.py
────────────────────
Multi-agent stock analysis system inspired by the TradingAgents framework
(Xiao et al., 2025 — https://arxiv.org/abs/2412.20138).

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Phase 1: ANALYST TEAM  (pure Python, no LLM, run in parallel) │
  │                                                                 │
  │   Technical   Fundamental   Options   News/Macro   Risk Mgr    │
  │       │            │           │          │           │          │
  │       └────────────┴───────────┴──────────┴───────────┘          │
  │                           │                                     │
  │                    AnalystReport[]                               │
  ├─────────────────────────────────────────────────────────────────┤
  │  Phase 2: RESEARCHER TEAM  (2 LLM calls — bull + bear debate)  │
  │                                                                 │
  │   Bullish Researcher  ←──debate──→  Bearish Researcher         │
  │                                                                 │
  ├─────────────────────────────────────────────────────────────────┤
  │  Phase 3: SYNTHESIS  (1 LLM call — final verdict + trade rec)  │
  │                                                                 │
  │   Fund Manager — weighs debate + risk profile → recommendation │
  └─────────────────────────────────────────────────────────────────┘

Total LLM calls: 3 (bull, bear, synthesis)
Analysts: pure Python — call tools directly via ToolRegistry, no LLM needed.

Key design choices:
  - Analysts return structured AnalystReport (dataclass), not free text
  - Personality/bias only enters at the debate stage (LLM)
  - Default: sequential LLM calls (works with any subscription)
  - Option: parallel analyst execution via ThreadPoolExecutor
  - Verbose output by default — shows full debate process
  - Graceful fallback: if all analysts fail, falls back to single-agent
"""

from __future__ import annotations

import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agent.tools import ToolRegistry, build_registry

console = Console()


# ── Data Models ──────────────────────────────────────────────

@dataclass
class AnalystReport:
    """Structured output from each analyst agent."""
    analyst:    str                       # e.g. "Technical", "Fundamental"
    verdict:    str                       # BULLISH / BEARISH / NEUTRAL
    confidence: int                       # 0-100
    score:      float                     # raw score from analysis
    key_points: list[str] = field(default_factory=list)
    data:       dict = field(default_factory=dict)   # raw data for LLM context
    error:      str = ""                  # non-empty if analyst failed

    def summary_text(self) -> str:
        """One-paragraph summary for feeding into LLM debate prompts."""
        if self.error:
            return f"[{self.analyst} Analyst] FAILED: {self.error}"
        points = "\n".join(f"  - {p}" for p in self.key_points)
        return (
            f"[{self.analyst} Analyst] Verdict: {self.verdict} "
            f"(confidence: {self.confidence}%, score: {self.score})\n"
            f"{points}"
        )


@dataclass
class DebateResult:
    """Output from the bull/bear debate phase."""
    bull_argument: str
    bear_argument: str
    winner:        str    # "BULL" or "BEAR" (determined by synthesis)


@dataclass
class TradeRecommendation:
    """Final output from the multi-agent pipeline."""
    symbol:           str
    exchange:         str
    overall_verdict:  str            # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
    confidence:       int            # 0-100
    strategy:         str            # e.g. "Buy on dip", "Bull call spread"
    entry:            str
    stop_loss:        str
    target:           str
    risk_reward:      str
    rationale:        list[str]
    risks:            list[str]
    analyst_reports:  list[AnalystReport]
    debate:           DebateResult
    raw_synthesis:    str            # full LLM output


# ── Analyst Agents (pure Python, no LLM) ─────────────────────

class BaseAnalyst:
    """Base class for all analyst agents. Each runs tool(s) and returns structured data."""

    name: str = "Base"

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        raise NotImplementedError


class TechnicalAnalyst(BaseAnalyst):
    """Runs technical analysis: RSI, MACD, EMAs, Bollinger, support/resistance."""

    name = "Technical"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            result = self.registry.execute("technical_analyse", {
                "symbol": symbol, "exchange": exchange
            })
            if isinstance(result, dict) and "error" in result:
                return AnalystReport(
                    analyst=self.name, verdict="UNKNOWN", confidence=0,
                    score=0, error=result["error"],
                )

            score = result.get("score", 0)
            verdict = result.get("verdict", "NEUTRAL")
            confidence = min(abs(score), 100)

            points = []
            if result.get("rsi") is not None:
                rsi = result["rsi"]
                points.append(f"RSI: {rsi:.1f} ({'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'})")
            if result.get("macd") is not None:
                macd_signal = "bullish" if result.get("macd_signal") == "BUY" else "bearish"
                points.append(f"MACD: {macd_signal} crossover")
            if result.get("ema20") and result.get("ema50"):
                trend = "above" if result["ema20"] > result["ema50"] else "below"
                points.append(f"EMA20 {trend} EMA50 (short-term trend {'up' if trend == 'above' else 'down'})")
            if result.get("support"):
                points.append(f"Support: {result['support']}")
            if result.get("resistance"):
                points.append(f"Resistance: {result['resistance']}")
            if result.get("volume_verdict"):
                points.append(f"Volume: {result['volume_verdict']}")
            if result.get("bollinger_position"):
                points.append(f"Bollinger: {result['bollinger_position']}")

            return AnalystReport(
                analyst=self.name, verdict=verdict, confidence=confidence,
                score=score, key_points=points, data=result,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name, verdict="UNKNOWN", confidence=0,
                score=0, error=str(e),
            )


class FundamentalAnalyst(BaseAnalyst):
    """Runs fundamental analysis: PE, PB, ROE, ROCE, growth, promoter holding."""

    name = "Fundamental"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            result = self.registry.execute("fundamental_analyse", {"symbol": symbol})
            if isinstance(result, dict) and "error" in result:
                return AnalystReport(
                    analyst=self.name, verdict="UNKNOWN", confidence=0,
                    score=0, error=result["error"],
                )

            score = result.get("score", 50)
            if score >= 70:
                verdict = "BULLISH"
            elif score <= 30:
                verdict = "BEARISH"
            else:
                verdict = "NEUTRAL"

            points = []
            if result.get("pe") is not None:
                points.append(f"PE: {result['pe']:.1f}")
            if result.get("roe") is not None:
                points.append(f"ROE: {result['roe']:.1f}%")
            if result.get("roce") is not None:
                points.append(f"ROCE: {result['roce']:.1f}%")
            if result.get("debt_to_equity") is not None:
                points.append(f"Debt/Equity: {result['debt_to_equity']:.2f}")
            if result.get("revenue_growth") is not None:
                points.append(f"Revenue Growth: {result['revenue_growth']:.1f}%")
            if result.get("profit_growth") is not None:
                points.append(f"Profit Growth: {result['profit_growth']:.1f}%")
            if result.get("promoter_holding") is not None:
                points.append(f"Promoter Holding: {result['promoter_holding']:.1f}%")
            if result.get("verdict"):
                points.append(f"Overall: {result['verdict']}")

            return AnalystReport(
                analyst=self.name, verdict=verdict, confidence=min(score, 100),
                score=score, key_points=points, data=result,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name, verdict="UNKNOWN", confidence=0,
                score=0, error=str(e),
            )


class OptionsAnalyst(BaseAnalyst):
    """Analyzes options data: PCR, max pain, IV rank, OI patterns."""

    name = "Options"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}

            # PCR
            pcr_result = self.registry.execute("get_pcr", {"underlying": symbol})
            if isinstance(pcr_result, dict) and "pcr" in pcr_result:
                pcr = pcr_result["pcr"]
                data["pcr"] = pcr
                if pcr is not None:
                    if pcr > 1.2:
                        points.append(f"PCR: {pcr:.2f} (bearish — heavy put writing)")
                    elif pcr < 0.8:
                        points.append(f"PCR: {pcr:.2f} (bullish — heavy call writing)")
                    else:
                        points.append(f"PCR: {pcr:.2f} (neutral)")

            # Max Pain
            mp_result = self.registry.execute("get_max_pain", {"underlying": symbol})
            if isinstance(mp_result, dict) and "max_pain" in mp_result:
                data["max_pain"] = mp_result["max_pain"]
                points.append(f"Max Pain: {mp_result['max_pain']}")

            # IV Rank
            iv_result = self.registry.execute("get_iv_rank", {"symbol": symbol})
            if isinstance(iv_result, dict) and "iv_rank" in iv_result:
                iv_rank = iv_result["iv_rank"]
                data["iv_rank"] = iv_rank
                if iv_rank is not None:
                    if iv_rank > 50:
                        points.append(f"IV Rank: {iv_rank} (elevated — good for selling premium)")
                    else:
                        points.append(f"IV Rank: {iv_rank} (low — good for buying options)")

            # Derive verdict from PCR
            pcr_val = data.get("pcr")
            if pcr_val is not None:
                if pcr_val > 1.2:
                    verdict, score = "BEARISH", -40
                elif pcr_val < 0.8:
                    verdict, score = "BULLISH", 40
                else:
                    verdict, score = "NEUTRAL", 0
            else:
                verdict, score = "NEUTRAL", 0

            return AnalystReport(
                analyst=self.name, verdict=verdict,
                confidence=min(abs(score) + 30, 100),
                score=score, key_points=points, data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name, verdict="UNKNOWN", confidence=0,
                score=0, error=str(e),
            )


class NewsMacroAnalyst(BaseAnalyst):
    """Gathers news, FII/DII flows, market breadth, upcoming events."""

    name = "News & Macro"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}

            # Stock-specific news
            news = self.registry.execute("get_stock_news", {"symbol": symbol, "n": 5})
            if isinstance(news, list) and news:
                data["news"] = news[:5]
                points.append(f"{len(news)} recent news articles found")
                # Summarize top headline
                if isinstance(news[0], dict) and "title" in news[0]:
                    points.append(f"Latest: {news[0]['title'][:80]}")

            # FII/DII flows
            fii = self.registry.execute("get_fii_dii_data", {"days": 3})
            if isinstance(fii, list) and fii:
                data["fii_dii"] = fii
                latest = fii[0] if fii else {}
                fii_net = latest.get("fii_net", 0)
                if fii_net:
                    direction = "buying" if fii_net > 0 else "selling"
                    points.append(f"FII: net {direction} {abs(fii_net):,.0f} Cr (latest)")

            # Market breadth
            breadth = self.registry.execute("get_market_breadth", {})
            if isinstance(breadth, dict):
                data["breadth"] = breadth
                ad_ratio = breadth.get("ad_ratio")
                if ad_ratio is not None:
                    if ad_ratio > 1.5:
                        points.append(f"Breadth: Strong ({ad_ratio:.1f} A/D ratio)")
                    elif ad_ratio < 0.7:
                        points.append(f"Breadth: Weak ({ad_ratio:.1f} A/D ratio)")
                    else:
                        points.append(f"Breadth: Neutral ({ad_ratio:.1f} A/D ratio)")

            # Upcoming events
            events = self.registry.execute("get_upcoming_events", {"days": 7})
            if isinstance(events, dict) or isinstance(events, list):
                data["events"] = events
                points.append("Checked upcoming events (expiry, earnings, RBI)")

            # Derive sentiment
            bullish_signals = sum(1 for p in points if any(w in p.lower() for w in ["buying", "strong"]))
            bearish_signals = sum(1 for p in points if any(w in p.lower() for w in ["selling", "weak"]))

            if bullish_signals > bearish_signals:
                verdict, score = "BULLISH", 30
            elif bearish_signals > bullish_signals:
                verdict, score = "BEARISH", -30
            else:
                verdict, score = "NEUTRAL", 0

            return AnalystReport(
                analyst=self.name, verdict=verdict,
                confidence=40, score=score,
                key_points=points, data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name, verdict="UNKNOWN", confidence=0,
                score=0, error=str(e),
            )


class RiskAnalyst(BaseAnalyst):
    """Evaluates risk: VIX, position sizing, portfolio exposure, upcoming events."""

    name = "Risk Manager"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            import os
            points = []
            data: dict[str, Any] = {}

            # VIX check
            vix_result = self.registry.execute("get_vix", {})
            vix = None
            if isinstance(vix_result, dict):
                vix = vix_result.get("vix")
                data["vix"] = vix
                if vix is not None:
                    if vix > 20:
                        points.append(f"VIX: {vix:.1f} — DANGER ZONE. Reduce position sizes by 50%")
                    elif vix > 15:
                        points.append(f"VIX: {vix:.1f} — Elevated. Use hedged strategies")
                    elif vix < 12:
                        points.append(f"VIX: {vix:.1f} — Low. Good for directional trades")
                    else:
                        points.append(f"VIX: {vix:.1f} — Normal range")

            # Current quote for the symbol
            quote = self.registry.execute("get_quote", {"instruments": [f"{exchange}:{symbol}"]})
            if isinstance(quote, list) and quote:
                ltp = quote[0].get("last_price") or quote[0].get("ltp")
                if ltp:
                    data["ltp"] = ltp
                    points.append(f"Current price: {ltp:,.2f}")

            # Portfolio exposure check
            try:
                holdings = self.registry.execute("get_holdings", {})
                if isinstance(holdings, list):
                    existing = [h for h in holdings
                                if isinstance(h, dict) and h.get("symbol", "").upper() == symbol.upper()]
                    if existing:
                        points.append(f"Already holding {symbol} — check concentration risk")
                    data["has_existing_position"] = bool(existing)
            except Exception:
                pass

            # Risk sizing
            capital = int(os.environ.get("TOTAL_CAPITAL", "200000"))
            risk_pct = int(os.environ.get("DEFAULT_RISK_PCT", "2"))
            max_risk = capital * risk_pct / 100
            data["max_risk_per_trade"] = max_risk
            data["capital"] = capital
            points.append(f"Max risk per trade: {risk_pct}% of {capital:,} = {max_risk:,.0f}")

            # Risk verdict based on VIX
            if vix and vix > 20:
                verdict, score = "BEARISH", -50
                points.append("RECOMMENDATION: Reduce exposure, hedge positions")
            elif vix and vix > 15:
                verdict, score = "NEUTRAL", -20
                points.append("RECOMMENDATION: Use defined-risk strategies only")
            else:
                verdict, score = "NEUTRAL", 0
                points.append("RECOMMENDATION: Normal position sizing OK")

            return AnalystReport(
                analyst=self.name, verdict=verdict,
                confidence=70, score=score,
                key_points=points, data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name, verdict="UNKNOWN", confidence=0,
                score=0, error=str(e),
            )


# ── Multi-Agent Orchestrator ─────────────────────────────────

class MultiAgentAnalyzer:
    """
    Orchestrates the full multi-agent analysis pipeline.

    Pipeline:
      1. Run 5 analyst agents (parallel or sequential)
      2. Feed analyst reports into bull/bear debate (2 LLM calls)
      3. Synthesize final verdict + trade recommendation (1 LLM call)

    Usage:
        from agent.multi_agent import MultiAgentAnalyzer
        from agent.tools import build_registry
        from agent.core import get_provider

        analyzer = MultiAgentAnalyzer(registry, provider)
        result = analyzer.analyze("RELIANCE")
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm_provider: Any,
        parallel: bool = True,
        verbose: bool = True,
    ) -> None:
        self.registry = registry
        self.llm = llm_provider
        self.parallel = parallel
        self.verbose = verbose

        self.analysts = [
            TechnicalAnalyst(registry),
            FundamentalAnalyst(registry),
            OptionsAnalyst(registry),
            NewsMacroAnalyst(registry),
            RiskAnalyst(registry),
        ]

    def analyze(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Run the full multi-agent pipeline and return the final response text.

        Returns the synthesis LLM output (already printed to terminal).
        """
        symbol = symbol.upper()
        exchange = exchange.upper()

        console.print()
        console.rule(
            f"[bold cyan]Multi-Agent Analysis: {exchange}:{symbol}[/bold cyan]",
            style="cyan",
        )

        # ── Phase 1: Analyst Team ────────────────────────────
        t0 = time.time()
        reports = self._run_analysts(symbol, exchange)
        analyst_time = time.time() - t0

        if self.verbose:
            self._print_analyst_summary(reports, analyst_time)

        # Check if we have enough data to debate
        valid_reports = [r for r in reports if not r.error]
        if not valid_reports:
            console.print("[yellow]All analysts failed. Falling back to single-agent.[/yellow]")
            return self._fallback_single_agent(symbol, exchange)

        # ── Phase 2: Bull/Bear Debate ────────────────────────
        if self.verbose:
            console.print()
            console.rule("[bold yellow]Researcher Team — Bull vs Bear Debate[/bold yellow]", style="yellow")

        t1 = time.time()
        debate = self._run_debate(symbol, exchange, reports)
        debate_time = time.time() - t1

        if self.verbose:
            self._print_debate(debate, debate_time)

        # ── Phase 3: Synthesis ───────────────────────────────
        if self.verbose:
            console.print()
            console.rule("[bold green]Fund Manager — Final Synthesis[/bold green]", style="green")

        t2 = time.time()
        synthesis = self._run_synthesis(symbol, exchange, reports, debate)
        synthesis_time = time.time() - t2

        # Print timing summary
        total = analyst_time + debate_time + synthesis_time
        console.print()
        console.print(
            f"[dim]Analysis complete in {total:.1f}s "
            f"(analysts: {analyst_time:.1f}s, debate: {debate_time:.1f}s, "
            f"synthesis: {synthesis_time:.1f}s)[/dim]"
        )
        console.rule(style="cyan")
        console.print()

        return synthesis

    # ── Phase 1: Analyst Team ────────────────────────────────

    def _run_analysts(self, symbol: str, exchange: str) -> list[AnalystReport]:
        """Run all analyst agents. Parallel by default."""
        import os
        os.environ["_CLI_BATCH_MODE"] = "1"

        if self.parallel:
            reports = self._run_analysts_parallel(symbol, exchange)
        else:
            reports = self._run_analysts_sequential(symbol, exchange)

        os.environ.pop("_CLI_BATCH_MODE", None)
        return reports

    def _run_analysts_parallel(self, symbol: str, exchange: str) -> list[AnalystReport]:
        """Run analysts concurrently via ThreadPoolExecutor."""
        reports: list[AnalystReport] = []

        if self.verbose:
            console.print()
            console.print("[bold]Analyst Team[/bold] — running 5 analysts in parallel...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(a.analyze, symbol, exchange): a
                for a in self.analysts
            }
            for future in as_completed(futures):
                analyst = futures[future]
                try:
                    report = future.result(timeout=30)
                    reports.append(report)
                    if self.verbose:
                        status = "[green]OK[/green]" if not report.error else f"[red]FAIL: {report.error[:50]}[/red]"
                        console.print(f"  [dim]{analyst.name:<15}[/dim] {status}")
                except Exception as e:
                    reports.append(AnalystReport(
                        analyst=analyst.name, verdict="UNKNOWN",
                        confidence=0, score=0, error=str(e),
                    ))
                    if self.verbose:
                        console.print(f"  [dim]{analyst.name:<15}[/dim] [red]FAIL: {e}[/red]")

        return reports

    def _run_analysts_sequential(self, symbol: str, exchange: str) -> list[AnalystReport]:
        """Run analysts one by one (for debugging or rate-limited envs)."""
        reports: list[AnalystReport] = []

        if self.verbose:
            console.print()
            console.print("[bold]Analyst Team[/bold] — running 5 analysts sequentially...")

        for analyst in self.analysts:
            try:
                report = analyst.analyze(symbol, exchange)
                reports.append(report)
                if self.verbose:
                    status = "[green]OK[/green]" if not report.error else f"[red]FAIL: {report.error[:50]}[/red]"
                    console.print(f"  [dim]{analyst.name:<15}[/dim] {status}")
            except Exception as e:
                reports.append(AnalystReport(
                    analyst=analyst.name, verdict="UNKNOWN",
                    confidence=0, score=0, error=str(e),
                ))

        return reports

    def _print_analyst_summary(self, reports: list[AnalystReport], elapsed: float) -> None:
        """Display analyst results as a Rich table."""
        console.print()
        table = Table(
            title=f"Analyst Reports ({elapsed:.1f}s)",
            show_header=True,
            header_style="bold cyan",
            show_lines=True,
        )
        table.add_column("Analyst", style="bold", width=16)
        table.add_column("Verdict", width=10)
        table.add_column("Confidence", justify="right", width=12)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Key Points", ratio=1)

        for r in reports:
            if r.error:
                table.add_row(
                    r.analyst, "[red]ERROR[/red]", "-", "-",
                    f"[red]{r.error[:60]}[/red]",
                )
            else:
                verdict_style = {
                    "BULLISH": "green", "BEARISH": "red", "NEUTRAL": "yellow",
                }.get(r.verdict, "white")
                points_text = "\n".join(r.key_points[:4]) if r.key_points else "-"
                table.add_row(
                    r.analyst,
                    f"[{verdict_style}]{r.verdict}[/{verdict_style}]",
                    f"{r.confidence}%",
                    f"{r.score:+.0f}",
                    points_text,
                )

        console.print(table)

    # ── Phase 2: Bull/Bear Debate ────────────────────────────

    def _run_debate(
        self, symbol: str, exchange: str, reports: list[AnalystReport]
    ) -> DebateResult:
        """
        Run bull and bear researchers via LLM calls.
        Each gets the same analyst data but argues from their assigned perspective.
        """
        analyst_context = "\n\n".join(r.summary_text() for r in reports if not r.error)

        # Bull researcher
        bull_prompt = BULL_RESEARCHER_PROMPT.format(
            symbol=symbol, exchange=exchange, analyst_data=analyst_context,
        )
        if self.verbose:
            console.print("\n[green]Bull Researcher[/green] building investment case...")

        bull_argument = self.llm.chat(
            messages=[{"role": "user", "content": bull_prompt}],
            stream=self.verbose,
        )

        # Bear researcher
        bear_prompt = BEAR_RESEARCHER_PROMPT.format(
            symbol=symbol, exchange=exchange, analyst_data=analyst_context,
            bull_case=bull_argument,
        )
        if self.verbose:
            console.print("\n[red]Bear Researcher[/red] building counter-argument...")

        bear_argument = self.llm.chat(
            messages=[{"role": "user", "content": bear_prompt}],
            stream=self.verbose,
        )

        return DebateResult(
            bull_argument=bull_argument,
            bear_argument=bear_argument,
            winner="",  # determined by synthesis
        )

    def _print_debate(self, debate: DebateResult, elapsed: float) -> None:
        """Display the bull/bear debate results."""
        console.print(f"\n[dim]Debate completed in {elapsed:.1f}s[/dim]")

    # ── Phase 3: Synthesis ───────────────────────────────────

    def _run_synthesis(
        self,
        symbol: str,
        exchange: str,
        reports: list[AnalystReport],
        debate: DebateResult,
    ) -> str:
        """
        Final synthesis: weigh all analyst reports + debate arguments,
        produce a trade recommendation.
        """
        analyst_context = "\n\n".join(r.summary_text() for r in reports if not r.error)

        # Include risk data
        risk_report = next((r for r in reports if r.analyst == "Risk Manager"), None)
        risk_context = ""
        if risk_report and not risk_report.error:
            risk_context = (
                f"\nRisk Parameters:\n"
                f"  Capital: {risk_report.data.get('capital', 'N/A')}\n"
                f"  Max Risk/Trade: {risk_report.data.get('max_risk_per_trade', 'N/A')}\n"
                f"  VIX: {risk_report.data.get('vix', 'N/A')}\n"
            )

        synthesis_prompt = SYNTHESIS_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            analyst_data=analyst_context,
            bull_case=debate.bull_argument,
            bear_case=debate.bear_argument,
            risk_context=risk_context,
        )

        if self.verbose:
            console.print("\nSynthesizing final verdict...")

        synthesis = self.llm.chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            stream=self.verbose,
        )

        return synthesis

    # ── Fallback ─────────────────────────────────────────────

    def _fallback_single_agent(self, symbol: str, exchange: str) -> str:
        """If multi-agent fails, fall back to simple single-agent analysis."""
        from agent.prompts import ANALYZE_STOCK_PROMPT

        prompt = ANALYZE_STOCK_PROMPT.format(symbol=symbol)
        return self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )


# ── Debate & Synthesis Prompt Templates ──────────────────────

BULL_RESEARCHER_PROMPT = """You are a BULLISH stock researcher at an Indian trading firm.
Your job: build the strongest possible investment case for {symbol} ({exchange}).

You have received the following analyst reports from your team:

{analyst_data}

Based on this data, construct a compelling BULL CASE for investing in {symbol}:

1. Highlight every positive signal from the analyst reports
2. Identify growth catalysts and upside potential
3. Explain why any negative signals are temporary or manageable
4. Suggest optimal entry timing based on technical levels
5. Propose a specific strategy (delivery, options, etc.)

Keep it concise (200-300 words). Cite specific numbers from the data.
This is for an Indian market context (NSE/BSE). Use INR for all prices."""

BEAR_RESEARCHER_PROMPT = """You are a BEARISH stock researcher at an Indian trading firm.
Your job: identify all risks and build a counter-argument against investing in {symbol} ({exchange}).

You have received the following analyst reports from your team:

{analyst_data}

The BULL researcher has made this case:
{bull_case}

Build a compelling BEAR CASE against {symbol}:

1. Challenge every bullish claim with counter-evidence from the data
2. Highlight all risk factors: valuation, technical weakness, macro headwinds
3. Identify what could go wrong in the short and medium term
4. Point out any red flags in fundamentals or options data
5. If the trade idea has merit, argue for a more conservative approach

Keep it concise (200-300 words). Cite specific numbers from the data.
Be skeptical but fair — this is about protecting capital, not being contrarian for its own sake."""

SYNTHESIS_PROMPT = """You are the FUND MANAGER at an Indian trading firm.
You must make the final call on {symbol} ({exchange}) after reviewing all evidence.

## Analyst Reports
{analyst_data}

## Bull Case
{bull_case}

## Bear Case
{bear_case}

## Risk Parameters
{risk_context}

## Your Task
Weigh the bull and bear arguments against the analyst data. Consider:
- Which side has stronger evidence?
- What does the risk profile suggest?
- Is the timing right (technicals, events, VIX)?

Provide your FINAL VERDICT in this exact format:

VERDICT: [STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL]
CONFIDENCE: [0-100]%
WINNER: [BULL / BEAR] — which researcher had the stronger argument

TRADE RECOMMENDATION:
Strategy  : [specific strategy name]
Entry     : [price or "at market"]
Stop-Loss : [price] ([% from entry]%)
Target    : [price] ([% from entry]%)
R:R Ratio : [reward:risk]
Position  : [lots/shares and sizing rationale]

RATIONALE (3 bullets):
- [why this trade]
- [key supporting evidence]
- [timing justification]

RISKS (2-3 bullets):
- [primary risk]
- [secondary risk]

Keep the output concise and terminal-friendly. Use bullets. All prices in INR."""
