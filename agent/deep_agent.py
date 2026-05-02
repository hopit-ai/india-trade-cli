"""
agent/deep_agent.py
───────────────────
Full LLM multi-agent mode ("--deep") — every agent is LLM-powered.

Every agent is LLM-powered (vs default mode where analysts are pure Python).
11+ LLM calls per analysis — expensive but much deeper reasoning.

Architecture:
  Phase 1: 5 LLM Analyst calls (each reads raw data + reasons about it)
  Phase 2: 2-round debate (5 LLM calls: bull, bear, bull rebuttal, bear rebuttal, facilitator)
  Phase 3: 1 LLM synthesis call
  Total: 11 LLM calls minimum

Requires API key (not subscription) due to high call volume.

Usage:
    from agent.deep_agent import DeepAnalyzer

    analyzer = DeepAnalyzer(registry, llm_provider)
    result = analyzer.analyze("RELIANCE")

    # Or via REPL:
    deep-analyze RELIANCE
"""

from __future__ import annotations

import json
import time
from typing import Any

from rich.table import Table

from agent.tools import ToolRegistry
from agent.multi_agent import (
    AnalystReport,
    MultiAgentAnalyzer,
    compute_scorecard,
    console,
)


# ── LLM Analyst Prompts ──────────────────────────────────────

DEEP_TECHNICAL_PROMPT = """You are a TECHNICAL ANALYST at an Indian trading firm.
Analyze {symbol} ({exchange}) using the following raw market data.

{tool_data}

Provide a thorough technical analysis covering:
1. Trend analysis: EMA20 vs EMA50 vs SMA200, trend direction and strength
2. Momentum: RSI level and divergences, MACD crossover state
3. Volatility: Bollinger Band position, ATR relative to price
4. Volume: is volume confirming the trend or diverging?
5. Support/Resistance: key levels from pivot points
6. Pattern recognition: any chart patterns forming?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]"""

DEEP_FUNDAMENTAL_PROMPT = """You are a FUNDAMENTAL ANALYST at an Indian trading firm.
Evaluate {symbol} ({exchange}) business quality using this data.

{tool_data}

Analyze:
1. Valuation: PE relative to sector, PB vs historical, is it cheap or expensive?
2. Quality: ROE, ROCE trends — is the business generating adequate returns?
3. Growth: Revenue and profit CAGR — accelerating or decelerating?
4. Balance sheet: Debt/equity, interest coverage — any stress?
5. Promoter: Holding %, pledge % — are insiders confident?
6. Red flags: any concerning patterns in the numbers?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]"""

DEEP_OPTIONS_PROMPT = """You are an OPTIONS ANALYST at an Indian trading firm.
Analyze {symbol} ({exchange}) options market for sentiment signals.

{tool_data}

Analyze:
1. PCR interpretation: what does the put-call ratio tell us about sentiment?
2. Max pain: where is the gravitational pull for expiry?
3. IV rank: is implied volatility elevated or cheap? What does this mean for strategy?
4. OI patterns: any unusual buildup at specific strikes?
5. Strategy suggestion: based on IV and direction, what's the optimal options play?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]"""

DEEP_SENTIMENT_PROMPT = """You are a SENTIMENT & NEWS ANALYST at an Indian trading firm.
Assess the sentiment landscape for {symbol} ({exchange}).

{tool_data}

Analyze:
1. News sentiment: are recent headlines positive, negative, or mixed?
2. FII/DII positioning: what are institutions doing? Any divergence signals?
3. Market breadth: is the broader market supporting or diverging?
4. Sector rotation: is money flowing into or out of this stock's sector?
5. Event risk: any upcoming events that could change the picture?
6. Social sentiment: any unusual retail interest or buzz?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]"""

DEEP_RISK_PROMPT = """You are a RISK MANAGER at an Indian trading firm.
Assess the risk profile for a potential trade in {symbol} ({exchange}).

{tool_data}

Analyze:
1. VIX regime: what does current VIX say about market risk appetite?
2. Position sizing: given the capital and risk tolerance, what's appropriate?
3. Concentration: is this trade adding to existing sector concentration?
4. Upcoming events: any events that could cause sharp adverse moves?
5. Liquidity: is this stock liquid enough for the intended position size?
6. Correlation: does this trade correlate with existing positions?
7. Macro risks: any currency, commodity, or rate risks?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]  (from a risk perspective — BULLISH = low risk)
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
RISK_LEVEL: [LOW / MEDIUM / HIGH / DANGER]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]"""

DEEP_DCF_PROMPT = """You are a VALUATION ANALYST at an Indian trading firm.
Compute a DCF (Discounted Cash Flow) valuation for {symbol} ({exchange}).

{tool_data}

The data above includes:
- **Base DCF** with auto-detected growth rate
- **Reverse DCF**: what growth the market implies at the current price
- **FCF quality**: whether free cash flow is sustainable
- **Bull/Base/Bear scenarios** with different growth assumptions
- **If this is a bank**: a P/BV model instead of (or alongside) DCF

Your job as a valuation analyst:

1. **PICK YOUR OWN GROWTH RATE** with reasoning:
   - Look at: revenue growth, analyst consensus, sector trends, competitive position
   - State: "I'm using X% because..." (don't just accept the auto-detected rate)
   - If you disagree with the auto rate, explain why

2. **Interpret the reverse DCF**:
   - "Market implies X% growth. This is [realistic/aggressive/conservative] because..."
   - This is the most important insight — tells you what the market is pricing in

3. **Assess FCF quality**:
   - Is FCF sustainable? Any red flags (capex cuts, working capital swings)?
   - If quality is LOW, discount the DCF result

4. **Pick the most realistic scenario**:
   - Bull/Base/Bear — which one matches your view?
   - What would need to happen for bull case? For bear case?

5. **For banks**: Use the P/BV model primarily. DCF doesn't work well for banks.
   - Justified P/BV = ROE / Cost of Equity
   - Is the stock trading above or below justified book?

Respond with:
VERDICT: [BULLISH / BEARISH / NEUTRAL]
CONFIDENCE: [0-100]%
SCORE: [-100 to +100]
KEY_POINTS:
- [point 1 — must include your chosen growth rate and intrinsic value]
- [point 2 — must reference reverse DCF / market-implied growth]
- [point 3 — risk or quality concern]"""


# ── Deep Analyzer ────────────────────────────────────────────


class DeepAnalyzer:
    """
    Full LLM multi-agent analysis — every analyst is LLM-powered.

    11+ LLM calls per analysis:
      5 analyst calls + 5 debate calls + 1 synthesis = 11

    Uses the same debate and synthesis from MultiAgentAnalyzer
    but replaces pure-Python analysts with LLM analysts.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        llm_provider: Any,
        verbose: bool = True,
        risk_debate: bool = False,
        context: str | None = None,
    ) -> None:
        self.registry = registry
        self.llm = llm_provider
        self.verbose = verbose
        self.risk_debate = risk_debate
        self.context = context  # inline synthesis hint — no mid-run prompting

    def analyze(self, symbol: str, exchange: str = "NSE") -> str:
        """Run full LLM deep analysis."""
        symbol = symbol.upper()
        exchange = exchange.upper()

        console.print()
        console.rule(
            f"[bold magenta]Deep Analysis (Full LLM): {exchange}:{symbol}[/bold magenta]",
            style="magenta",
        )
        console.print("[dim]  11+ LLM calls — this will take a few minutes...[/dim]")

        # ── Phase 1: LLM Analyst Team ────────────────────────
        t0 = time.time()
        reports = self._run_llm_analysts(symbol, exchange)
        analyst_time = time.time() - t0

        if self.verbose:
            self._print_reports(reports, analyst_time)

        valid = [r for r in reports if not r.error]
        if not valid:
            console.print("[yellow]All LLM analysts failed.[/yellow]")
            return ""

        # Scorecard
        scorecard = compute_scorecard(reports)
        if self.verbose:
            console.print(f"\n[dim]{scorecard.summary()}[/dim]")

        # ── Phase 2: Debate (reuse MultiAgentAnalyzer's debate) ──
        if self.verbose:
            console.print()
            console.rule("[bold yellow]Deep Debate (2 rounds)[/bold yellow]", style="yellow")

        t1 = time.time()
        # Create a temporary MultiAgentAnalyzer just for debate + synthesis
        multi = MultiAgentAnalyzer(
            self.registry, self.llm, verbose=self.verbose, risk_debate=self.risk_debate
        )
        # Inject inline context hint without blocking for input
        if self.context:
            multi.user_hints.put(self.context)

        # Build compact Stage 1 signals for token-efficient debate prompts
        from analysis.pipeline import build_compact_signals

        ltp = 0.0
        for r in reports:
            if r.analyst == "Technical" and not r.error:
                ltp = r.data.get("ltp", 0.0) or 0.0
                break
        _compact = build_compact_signals(symbol, exchange, reports, ltp)

        debate = multi._run_debate(symbol, exchange, reports, compact_signals=_compact)
        debate_time = time.time() - t1

        # ── Phase 2.5: Risk Debate ───────────────────────────
        risk_debate_result = None
        risk_debate_time = 0.0
        if self.risk_debate and scorecard.verdict != "HOLD":
            if self.verbose:
                console.print()
                console.rule(
                    "[bold magenta]Risk Team — Aggressive / Conservative / Neutral[/bold magenta]",
                    style="magenta",
                )
            t_risk = time.time()
            risk_debate_result = multi._run_risk_debate(
                symbol, exchange, scorecard, debate, reports
            )
            risk_debate_time = time.time() - t_risk
            if self.verbose:
                console.print(f"[dim]Risk debate completed in {risk_debate_time:.1f}s[/dim]")

        # ── Phase 3: Synthesis ───────────────────────────────
        if self.verbose:
            console.print()
            console.rule("[bold green]Deep Synthesis[/bold green]", style="green")

        t2 = time.time()
        synthesis = multi._run_synthesis(
            symbol,
            exchange,
            reports,
            debate,
            risk_debate_result,
            compact_signals=_compact,
        )
        synthesis_time = time.time() - t2

        # ── Trade plans ──────────────────────────────────────
        try:
            from engine.trader import TraderAgent

            trader = TraderAgent()
            all_plans = trader.generate_all_plans(
                symbol=symbol,
                exchange=exchange,
                reports=reports,
                synthesis=synthesis,
            )
            if any(p for p in all_plans.values()):
                TraderAgent.print_all_plans(all_plans)
        except Exception:
            pass

        # ── Memory ───────────────────────────────────────────
        try:
            from engine.memory import trade_memory

            record = trade_memory.store_from_analysis(
                symbol=symbol,
                exchange=exchange,
                analyst_reports=reports,
                debate=debate,
                synthesis=synthesis,
            )
            if self.verbose:
                console.print(f"[dim]  Stored to memory (ID: {record.id})[/dim]")
        except Exception:
            pass

        total = analyst_time + debate_time + risk_debate_time + synthesis_time
        llm_calls = 11 + (3 if risk_debate_time > 0 else 0)
        risk_str = f", risk: {risk_debate_time:.1f}s" if risk_debate_time > 0 else ""
        console.print(
            f"\n[dim]Deep analysis complete in {total:.1f}s "
            f"(analysts: {analyst_time:.1f}s, debate: {debate_time:.1f}s"
            f"{risk_str}, synthesis: {synthesis_time:.1f}s) — "
            f"{llm_calls} LLM calls[/dim]"
        )
        console.rule(style="magenta")

        # Build full report for PDF/export
        full_parts = [
            f"DEEP ANALYSIS (FULL LLM): {exchange}:{symbol}",
            f"Date: {time.strftime('%d %b %Y, %I:%M %p')}",
            f"Mode: 11 LLM calls | {total:.0f}s total",
            "",
            "=" * 60,
            "LLM ANALYST REPORTS",
            "=" * 60,
        ]
        for r in reports:
            if not r.error:
                full_parts.append(r.summary_text())
                full_parts.append("")

        full_parts.append(f"\nSCORECARD: {scorecard.summary()}\n")

        full_parts.extend(
            [
                "=" * 60,
                "BULL/BEAR DEBATE",
                "=" * 60,
                "",
                "--- BULL CASE (Round 1) ---",
                debate.bull_argument,
                "",
                "--- BEAR CASE (Round 1) ---",
                debate.bear_argument,
                "",
            ]
        )
        if debate.bull_rebuttal:
            full_parts.extend(["--- BULL REBUTTAL (Round 2) ---", debate.bull_rebuttal, ""])
        if debate.bear_rebuttal:
            full_parts.extend(["--- BEAR REBUTTAL (Round 2) ---", debate.bear_rebuttal, ""])
        if debate.facilitator:
            full_parts.extend(
                [
                    "--- FACILITATOR SUMMARY ---",
                    debate.facilitator,
                    f"Debate Winner: {debate.winner}",
                    "",
                ]
            )

        full_parts.extend(
            [
                "=" * 60,
                "FUND MANAGER SYNTHESIS",
                "=" * 60,
                "",
                synthesis,
            ]
        )

        self.last_full_report = "\n".join(full_parts)
        return self.last_full_report

    def _run_llm_analysts(self, symbol: str, exchange: str) -> list[AnalystReport]:
        """Run all analysts as LLM calls in parallel (ThreadPoolExecutor).

        Each analyst is independent — they gather their own tool data then
        make one LLM call. Running them concurrently cuts Phase 1 time from
        N×latency down to ~1×latency (the slowest analyst).
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os

        os.environ["_CLI_BATCH_MODE"] = "1"

        analysts = [
            ("Technical", DEEP_TECHNICAL_PROMPT, ["technical_analyse", "get_quote"]),
            ("Fundamental", DEEP_FUNDAMENTAL_PROMPT, ["fundamental_analyse"]),
            ("DCF Valuation", DEEP_DCF_PROMPT, ["compute_dcf"]),
            ("Options", DEEP_OPTIONS_PROMPT, ["get_pcr", "get_max_pain", "get_iv_rank"]),
            (
                "Sentiment",
                DEEP_SENTIMENT_PROMPT,
                ["get_stock_news", "get_fii_dii_data", "get_market_breadth"],
            ),
            ("Risk", DEEP_RISK_PROMPT, ["get_vix", "get_quote", "get_upcoming_events"]),
        ]

        if self.verbose:
            console.print(f"  [dim]Running {len(analysts)} analysts in parallel...[/dim]")

        def _run_one(analyst_spec) -> AnalystReport:
            name, prompt_template, tools = analyst_spec
            try:
                # Phase A: gather raw tool data
                tool_data_parts = []
                for tool_name in tools:
                    args = {}
                    if "symbol" in str(
                        self.registry._tools.get(tool_name, {}).get("parameters", {})
                    ):
                        args["symbol"] = symbol
                    elif "underlying" in str(
                        self.registry._tools.get(tool_name, {}).get("parameters", {})
                    ):
                        args["underlying"] = symbol
                    elif "instruments" in str(
                        self.registry._tools.get(tool_name, {}).get("parameters", {})
                    ):
                        args["instruments"] = [f"{exchange}:{symbol}"]

                    result = self.registry.execute(tool_name, args)
                    tool_data_parts.append(
                        f"[{tool_name}]\n{json.dumps(result, indent=2, default=str)}"
                    )

                tool_data = "\n\n".join(tool_data_parts)

                # Phase B: LLM reasoning
                prompt = prompt_template.format(
                    symbol=symbol,
                    exchange=exchange,
                    tool_data=tool_data,
                )
                response = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )
                return self._parse_llm_report(name, response)

            except Exception as e:
                return AnalystReport(
                    analyst=name,
                    verdict="UNKNOWN",
                    confidence=0,
                    score=0,
                    error=str(e),
                )

        # Submit all analysts concurrently; collect in original order
        name_to_report: dict[str, AnalystReport] = {}
        with ThreadPoolExecutor(max_workers=len(analysts)) as pool:
            future_to_name = {pool.submit(_run_one, spec): spec[0] for spec in analysts}
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                report = future.result()
                name_to_report[name] = report
                if self.verbose:
                    if report.error:
                        console.print(f"  [dim]{name:15s}[/dim] [red]FAIL[/red]")
                    else:
                        console.print(f"  [dim]{name:15s}[/dim] [green]{report.verdict}[/green]")

        os.environ.pop("_CLI_BATCH_MODE", None)

        # Return in original analyst order
        return [name_to_report[spec[0]] for spec in analysts if spec[0] in name_to_report]

    def _parse_llm_report(self, analyst: str, response: str) -> AnalystReport:
        """Parse an LLM analyst response into AnalystReport.

        Handles various LLM output formats:
          VERDICT: BEARISH
          ### VERDICT: **BEARISH** (with notes)
          VERDICT    : NEUTRAL (leaning BULLISH)
          **VERDICT:** BEARISH
        """
        import re

        verdict = "NEUTRAL"
        confidence = 50
        score = 0.0
        points = []

        # Strip markdown formatting for cleaner parsing
        clean = response.replace("**", "").replace("###", "").replace("##", "").replace("#", "")

        for line in clean.splitlines():
            stripped = line.strip()
            upper = stripped.upper()

            # Match VERDICT with flexible formatting:
            # "VERDICT: BEARISH", "VERDICT : NEUTRAL (leaning bullish)", etc.
            verdict_match = re.match(r"VERDICT\s*:\s*(.+)", upper)
            if verdict_match:
                val = verdict_match.group(1)
                for v in ("BULLISH", "BEARISH", "NEUTRAL"):
                    if v in val:
                        verdict = v
                        break

            # Match CONFIDENCE with flexible formatting:
            # "CONFIDENCE: 62%", "CONFIDENCE : 55%", "CONFIDENCE: 62"
            conf_match = re.match(r"CONFIDENCE\s*:\s*(\d+)", upper)
            if conf_match:
                try:
                    confidence = int(conf_match.group(1))
                except (ValueError, IndexError):
                    pass

            # Match SCORE with flexible formatting:
            # "SCORE: -23", "SCORE : +30", "SCORE: -15"
            score_match = re.match(r"SCORE\s*:\s*([+\-]?\d+(?:\.\d+)?)", upper)
            if score_match:
                try:
                    score = float(score_match.group(1))
                except (ValueError, IndexError):
                    pass

            # Collect key points
            if stripped.startswith("- ") or stripped.startswith("* "):
                point = stripped.lstrip("-* ").strip()
                if point and len(point) > 10:  # skip tiny fragments
                    points.append(point)

        # Fallback: scan the entire response for verdict keywords if still NEUTRAL/50/0
        if verdict == "NEUTRAL" and confidence == 50 and score == 0.0:
            resp_upper = clean.upper()
            # Look for verdict in the last 30 lines (summary section)
            last_lines = "\n".join(clean.splitlines()[-30:]).upper()
            if "BEARISH" in last_lines and "BULLISH" not in last_lines:
                verdict = "BEARISH"
            elif "BULLISH" in last_lines and "BEARISH" not in last_lines:
                verdict = "BULLISH"

            # Try to find confidence/score anywhere in response
            all_conf = re.findall(r"CONFIDENCE\s*:?\s*(\d+)\s*%?", resp_upper)
            if all_conf:
                confidence = int(all_conf[-1])  # take last occurrence

            all_scores = re.findall(r"SCORE\s*:?\s*([+\-]?\d+(?:\.\d+)?)", resp_upper)
            if all_scores:
                score = float(all_scores[-1])

        return AnalystReport(
            analyst=analyst,
            verdict=verdict,
            confidence=confidence,
            score=score,
            key_points=points[:5],
        )

    def _print_reports(self, reports: list[AnalystReport], elapsed: float) -> None:
        """Display LLM analyst results."""
        table = Table(
            title=f"Deep LLM Analyst Reports ({elapsed:.1f}s)",
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
        )
        table.add_column("Analyst", style="bold", width=14)
        table.add_column("Verdict", width=10)
        table.add_column("Conf", justify="right", width=8)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Key Points", ratio=1)

        for r in reports:
            if r.error:
                table.add_row(r.analyst, "[red]ERROR[/red]", "-", "-", f"[red]{r.error[:50]}[/red]")
            else:
                v_style = {"BULLISH": "green", "BEARISH": "red"}.get(r.verdict, "yellow")
                table.add_row(
                    r.analyst,
                    f"[{v_style}]{r.verdict}[/{v_style}]",
                    f"{r.confidence}%",
                    f"{r.score:+.0f}",
                    "\n".join(r.key_points[:3]) if r.key_points else "-",
                )

        console.print(table)
