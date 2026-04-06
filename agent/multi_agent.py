"""
agent/multi_agent.py
────────────────────
Multi-agent stock analysis system for Indian markets.

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

Total LLM calls: 8 (news sentiment, bull, bear, bull rebuttal, bear rebuttal,
                     facilitator, synthesis — plus trader agent is pure Python)
Analysts: pure Python — call tools directly via ToolRegistry.
Exception: NewsMacroAnalyst uses 1 LLM call for real news sentiment analysis.
Debate: 2 rounds with facilitator summary (5 LLM calls).
Risk Management: 3 trade plans (aggressive/neutral/conservative) generated locally.

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Optional

from rich.console import Console
from rich.table import Table

from agent.tools import ToolRegistry

console = Console()


# ── Data Models ──────────────────────────────────────────────


@dataclass
class AnalystReport:
    """Structured output from each analyst agent."""

    analyst: str  # e.g. "Technical", "Fundamental"
    verdict: str  # BULLISH / BEARISH / NEUTRAL
    confidence: int  # 0-100
    score: float  # raw score from analysis
    key_points: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)  # raw data for LLM context
    error: str = ""  # non-empty if analyst failed

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
class AnalystScorecard:
    """Weighted composite score from all analysts."""

    scores: dict[str, float]  # analyst_name → raw score
    weights: dict[str, float]  # analyst_name → weight (0-1)
    weighted_total: float  # sum(score * weight)
    verdict: str  # derived from total
    agreement: float  # 0-100, how much analysts agree
    conflicts: list[str] = field(
        default_factory=list
    )  # e.g. "Technical BULLISH vs Fundamental BEARISH"

    def summary(self) -> str:
        parts = [
            f"Scorecard: {self.verdict} (total: {self.weighted_total:+.1f}, agreement: {self.agreement:.0f}%)"
        ]
        for name, score in self.scores.items():
            w = self.weights.get(name, 0)
            parts.append(f"  {name:20s}: {score:+6.1f} (weight: {w:.0%})")
        if self.conflicts:
            parts.append(f"  Conflicts: {', '.join(self.conflicts)}")
        return "\n".join(parts)


# Default weights for the scorecard (customizable)
DEFAULT_ANALYST_WEIGHTS = {
    "Technical": 0.25,
    "Fundamental": 0.20,
    "Options": 0.15,
    "News & Macro": 0.10,
    "Sentiment": 0.10,
    "Sector Rotation": 0.05,
    "Risk Manager": 0.15,
}


def compute_scorecard(reports: list[AnalystReport]) -> AnalystScorecard:
    """Compute a weighted scorecard from analyst reports."""
    # Exclude analysts with no real data (error or UNAVAILABLE)
    _EXCLUDED_VERDICTS = {"UNKNOWN", "UNAVAILABLE"}

    scores = {}
    for r in reports:
        if not r.error and r.verdict not in _EXCLUDED_VERDICTS:
            scores[r.analyst] = r.score

    weights = {}
    for name in scores:
        weights[name] = DEFAULT_ANALYST_WEIGHTS.get(name, 0.1)

    # Normalize weights to sum to 1 (only across analysts with real data)
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}

    # Weighted total
    weighted_total = sum(scores.get(k, 0) * weights.get(k, 0) for k in scores)

    # Verdict from total
    if weighted_total > 30:
        verdict = "STRONG_BUY"
    elif weighted_total > 10:
        verdict = "BUY"
    elif weighted_total < -30:
        verdict = "STRONG_SELL"
    elif weighted_total < -10:
        verdict = "SELL"
    else:
        verdict = "HOLD"

    # Agreement: how many analysts agree on direction? (exclude unavailable)
    verdicts = [r.verdict for r in reports if not r.error and r.verdict not in _EXCLUDED_VERDICTS]
    if verdicts:
        from collections import Counter

        most_common = Counter(verdicts).most_common(1)[0]
        agreement = most_common[1] / len(verdicts) * 100
    else:
        agreement = 0

    # Detect conflicts
    conflicts = []
    bulls = [r.analyst for r in reports if not r.error and r.verdict == "BULLISH"]
    bears = [r.analyst for r in reports if not r.error and r.verdict == "BEARISH"]
    if bulls and bears:
        conflicts.append(f"{', '.join(bulls)} BULLISH vs {', '.join(bears)} BEARISH")

    return AnalystScorecard(
        scores=scores,
        weights=weights,
        weighted_total=round(weighted_total, 1),
        verdict=verdict,
        agreement=round(agreement, 1),
        conflicts=conflicts,
    )


@dataclass
class DebateResult:
    """Output from the multi-round bull/bear debate phase."""

    bull_argument: str  # Round 1: bull case
    bear_argument: str  # Round 1: bear counter
    bull_rebuttal: str = ""  # Round 2: bull responds to bear
    bear_rebuttal: str = ""  # Round 2: bear responds to bull rebuttal
    facilitator: str = ""  # Facilitator summary: key agreements/disagreements
    winner: str = ""  # "BULL" or "BEAR" (determined by facilitator)
    rounds: int = 1  # how many rounds were run


@dataclass
class RiskDebateResult:
    """Output from the three-way risk debate (aggressive / conservative / neutral)."""

    aggressive_view: str  # argues for larger size, tighter stop, no hedge
    conservative_view: str  # argues for smaller size, wider stop, protective hedge
    neutral_view: str  # synthesises a calibrated middle path
    consensus: str = ""  # brief consensus on sizing from the three views


@dataclass
class TradeRecommendation:
    """Final output from the multi-agent pipeline."""

    symbol: str
    exchange: str
    overall_verdict: str  # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
    confidence: int  # 0-100
    strategy: str  # e.g. "Buy on dip", "Bull call spread"
    entry: str
    stop_loss: str
    target: str
    risk_reward: str
    rationale: list[str]
    risks: list[str]
    analyst_reports: list[AnalystReport]
    debate: DebateResult
    risk_debate: Optional[RiskDebateResult] = None  # None when verdict is HOLD
    raw_synthesis: str = ""  # full LLM output


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
            result = self.registry.execute(
                "technical_analyse", {"symbol": symbol, "exchange": exchange}
            )
            if isinstance(result, dict) and "error" in result:
                return AnalystReport(
                    analyst=self.name,
                    verdict="UNKNOWN",
                    confidence=0,
                    score=0,
                    error=result["error"],
                )

            score = result.get("score", 0)
            verdict = result.get("verdict", "NEUTRAL")
            confidence = min(abs(score), 100)

            points = []
            if result.get("rsi") is not None:
                rsi = result["rsi"]
                points.append(
                    f"RSI: {rsi:.1f} ({'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'})"
                )
            if result.get("macd") is not None:
                macd_signal = "bullish" if result.get("macd_signal") == "BUY" else "bearish"
                points.append(f"MACD: {macd_signal} crossover")
            if result.get("ema20") and result.get("ema50"):
                trend = "above" if result["ema20"] > result["ema50"] else "below"
                points.append(
                    f"EMA20 {trend} EMA50 (short-term trend {'up' if trend == 'above' else 'down'})"
                )
            if result.get("support"):
                points.append(f"Support: {result['support']}")
            if result.get("resistance"):
                points.append(f"Resistance: {result['resistance']}")
            if result.get("volume_verdict"):
                points.append(f"Volume: {result['volume_verdict']}")
            if result.get("bollinger_position"):
                points.append(f"Bollinger: {result['bollinger_position']}")

            return AnalystReport(
                analyst=self.name,
                verdict=verdict,
                confidence=confidence,
                score=score,
                key_points=points,
                data=result,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )


class FundamentalAnalyst(BaseAnalyst):
    """Runs fundamental analysis: PE, PB, ROE, ROCE, growth, promoter holding."""

    name = "Fundamental"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            result = self.registry.execute("fundamental_analyse", {"symbol": symbol})
            if isinstance(result, dict) and "error" in result:
                return AnalystReport(
                    analyst=self.name,
                    verdict="UNKNOWN",
                    confidence=0,
                    score=0,
                    error=result["error"],
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
                analyst=self.name,
                verdict=verdict,
                confidence=min(score, 100),
                score=score,
                key_points=points,
                data=result,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )


class OptionsAnalyst(BaseAnalyst):
    """Analyzes options data: PCR, max pain, IV rank, OI patterns."""

    name = "Options"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}
            has_data = False  # track if we got any real options data

            # PCR
            pcr_result = self.registry.execute("get_pcr", {"underlying": symbol})
            if isinstance(pcr_result, dict) and "error" not in pcr_result and "pcr" in pcr_result:
                pcr = pcr_result["pcr"]
                data["pcr"] = pcr
                has_data = True
                if pcr is not None:
                    if pcr > 1.2:
                        points.append(f"PCR: {pcr:.2f} (bearish — heavy put writing)")
                    elif pcr < 0.8:
                        points.append(f"PCR: {pcr:.2f} (bullish — heavy call writing)")
                    else:
                        points.append(f"PCR: {pcr:.2f} (neutral)")

            # Max Pain
            mp_result = self.registry.execute("get_max_pain", {"underlying": symbol})
            if isinstance(mp_result, dict) and "error" not in mp_result and "max_pain" in mp_result:
                data["max_pain"] = mp_result["max_pain"]
                has_data = True
                points.append(f"Max Pain: {mp_result['max_pain']}")

            # IV Rank (note: mock_iv_rank is synthetic — don't count as real data)
            iv_result = self.registry.execute("get_iv_rank", {"symbol": symbol})
            if isinstance(iv_result, dict) and "error" not in iv_result and "iv_rank" in iv_result:
                iv_rank = iv_result["iv_rank"]
                data["iv_rank"] = iv_rank
                # Don't set has_data — IV rank is always mock, not from real options market
                if iv_rank is not None:
                    if iv_rank > 50:
                        points.append(f"IV Rank: {iv_rank} (elevated — good for selling premium)")
                    else:
                        points.append(f"IV Rank: {iv_rank} (low — good for buying options)")

            # If no options data was available, report clearly
            if not has_data:
                return AnalystReport(
                    analyst=self.name,
                    verdict="UNAVAILABLE",
                    confidence=0,
                    score=0,
                    key_points=[
                        "Options data unavailable for this symbol (no broker or no F&O segment)"
                    ],
                    data={"options_available": False},
                )

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
                analyst=self.name,
                verdict=verdict,
                confidence=min(abs(score) + 30, 100),
                score=score,
                key_points=points,
                data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )


class NewsMacroAnalyst(BaseAnalyst):
    """
    Gathers news, FII/DII flows, market breadth, upcoming events.

    Two modes:
      - Without LLM: counts bullish/bearish keywords in headlines (fast, free)
      - With LLM: sends headlines + macro data to LLM for real sentiment
        analysis — understands context, sarcasm, implications (1 extra LLM call)

    Set llm_provider via set_llm() before calling analyze() to enable LLM mode.
    """

    name = "News & Macro"

    def __init__(self, registry: ToolRegistry) -> None:
        super().__init__(registry)
        self._llm: Any = None

    def set_llm(self, llm_provider: Any) -> None:
        """Enable LLM-powered sentiment analysis."""
        self._llm = llm_provider

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}

            # ── Gather raw data (pure Python, no LLM) ───────────

            # Stock-specific news
            news = self.registry.execute("get_stock_news", {"symbol": symbol, "n": 8})
            if isinstance(news, list) and news:
                data["news"] = news[:8]
                points.append(f"{len(news)} recent news articles found")

            # Market-wide news
            market_news = self.registry.execute("get_market_news", {"n": 5})
            if isinstance(market_news, list) and market_news:
                data["market_news"] = market_news[:5]

            # FII/DII flows
            fii = self.registry.execute("get_fii_dii_data", {"days": 3})
            if isinstance(fii, list) and fii:
                data["fii_dii"] = fii
                latest = fii[0] if fii else {}
                fii_net = latest.get("fii_net", 0)
                if fii_net:
                    direction = "buying" if fii_net > 0 else "selling"
                    points.append(f"FII: net {direction} {abs(fii_net):,.0f} Cr (latest)")

            # Bulk/block deals (institutional activity)
            try:
                deals = self.registry.execute("get_bulk_block_deals", {"symbol": symbol})
                if isinstance(deals, dict):
                    bulk_deals = deals.get("bulk", [])
                    block_deals = deals.get("block", [])
                    all_deals = bulk_deals + block_deals
                    if all_deals:
                        data["bulk_block_deals"] = all_deals
                        buys = [d for d in all_deals if d.get("deal_type") == "BUY"]
                        sells = [d for d in all_deals if d.get("deal_type") == "SELL"]
                        fii_deals = [d for d in all_deals if d.get("entity_type") == "FII"]
                        mf_deals = [d for d in all_deals if d.get("entity_type") == "MF"]
                        summary = f"Bulk/block deals: {len(buys)} buys, {len(sells)} sells"
                        if fii_deals:
                            summary += f" ({len(fii_deals)} FII)"
                        if mf_deals:
                            summary += f" ({len(mf_deals)} MF)"
                        points.append(summary)
            except Exception:
                pass  # non-critical — don't fail analysis if deals unavailable

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

            # ── Sentiment analysis ───────────────────────────────

            if self._llm and (data.get("news") or data.get("market_news")):
                # LLM mode: real sentiment analysis
                verdict, score, confidence, llm_points = self._llm_sentiment(symbol, exchange, data)
                points.extend(llm_points)
                data["sentiment_mode"] = "llm"
            else:
                # Fallback: keyword-based sentiment
                verdict, score, confidence = self._keyword_sentiment(points)
                data["sentiment_mode"] = "keyword"

            return AnalystReport(
                analyst=self.name,
                verdict=verdict,
                confidence=confidence,
                score=score,
                key_points=points,
                data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )

    def _llm_sentiment(
        self,
        symbol: str,
        exchange: str,
        data: dict,
    ) -> tuple[str, float, int, list[str]]:
        """
        Use the LLM to analyze news sentiment. Returns (verdict, score, confidence, points).

        The LLM reads actual headlines and macro data, understands context
        (e.g. "RBI holds rates" is neutral, not negative), and produces a
        structured sentiment assessment.
        """
        # Build headlines text
        headlines = []
        for article in data.get("news", []):
            if isinstance(article, dict):
                title = article.get("title", "")
                source = article.get("source", "")
                if title:
                    headlines.append(f"- {title}" + (f" ({source})" if source else ""))

        for article in data.get("market_news", []):
            if isinstance(article, dict):
                title = article.get("title", "")
                if title:
                    headlines.append(f"- [Market] {title}")

        if not headlines:
            return self._keyword_sentiment([]) + ([],)

        headlines_text = "\n".join(headlines[:12])

        # Build macro context
        macro_parts = []
        fii_dii = data.get("fii_dii", [])
        if fii_dii and isinstance(fii_dii, list):
            macro_parts.append(f"FII/DII data (last 3 days): {json.dumps(fii_dii[:3])}")
        breadth = data.get("breadth", {})
        if breadth:
            macro_parts.append(f"Market breadth: {json.dumps(breadth)}")
        deals = data.get("bulk_block_deals", [])
        if deals:
            deal_lines = []
            for d in deals[:10]:
                dl = f"{d.get('date', '')} {d.get('symbol', '')} {d.get('client', '')[:30]} {d.get('deal_type', '')} {d.get('quantity', 0):,} @ ₹{d.get('price', 0):,.1f} [{d.get('entity_type', '')}]"
                deal_lines.append(dl)
            macro_parts.append("Bulk/block deals:\n" + "\n".join(deal_lines))
        events = data.get("events")
        if events:
            events_str = json.dumps(events) if isinstance(events, (dict, list)) else str(events)
            if len(events_str) > 500:
                events_str = events_str[:500] + "..."
            macro_parts.append(f"Upcoming events: {events_str}")

        macro_text = "\n".join(macro_parts) if macro_parts else "No macro data available."

        prompt = NEWS_SENTIMENT_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            headlines=headlines_text,
            macro_data=macro_text,
        )

        try:
            if self._llm:
                console.print(
                    f"  [dim cyan]Analyzing news sentiment for {symbol} via LLM...[/dim cyan]"
                )
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            return self._parse_sentiment_response(response)
        except Exception as e:
            # LLM failed — fall back to keyword sentiment
            console.print(
                f"  [dim yellow]LLM sentiment failed: {e} — using keyword fallback[/dim yellow]"
            )
            return self._keyword_sentiment([]) + ([f"LLM sentiment unavailable: {e}"],)

    def _parse_sentiment_response(self, response: str) -> tuple[str, float, int, list[str]]:
        """Parse the structured LLM sentiment response."""
        verdict = "NEUTRAL"
        score = 0.0
        confidence = 50
        points: list[str] = []

        for line in response.splitlines():
            line = line.strip()
            upper = line.upper()

            if upper.startswith("SENTIMENT:"):
                val = line.split(":", 1)[1].strip().upper()
                if "BULLISH" in val:
                    verdict = "BULLISH"
                elif "BEARISH" in val:
                    verdict = "BEARISH"
                else:
                    verdict = "NEUTRAL"

            elif upper.startswith("SCORE:"):
                try:
                    score = float(line.split(":", 1)[1].strip().rstrip("%"))
                except (ValueError, IndexError):
                    pass

            elif upper.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.split(":", 1)[1].strip().rstrip("%"))
                except (ValueError, IndexError):
                    pass

            elif line.startswith("- ") or line.startswith("* "):
                points.append(line.lstrip("-* ").strip())

        # If no points parsed, use the whole response as a single point
        if not points and response.strip():
            # Take first 2 sentences
            sentences = response.strip().split(". ")
            points = [s.strip() + "." for s in sentences[:2] if s.strip()]

        return verdict, score, confidence, points

    @staticmethod
    def _keyword_sentiment(points: list[str]) -> tuple[str, float, int]:
        """Fallback: count bullish/bearish keywords in existing points."""
        bullish_signals = sum(
            1 for p in points if any(w in p.lower() for w in ["buying", "strong", "rally", "surge"])
        )
        bearish_signals = sum(
            1
            for p in points
            if any(w in p.lower() for w in ["selling", "weak", "decline", "crash", "fall"])
        )

        if bullish_signals > bearish_signals:
            return "BULLISH", 30, 40
        elif bearish_signals > bullish_signals:
            return "BEARISH", -30, 40
        return "NEUTRAL", 0, 30


class SentimentAnalyst(BaseAnalyst):
    """
    Dedicated sentiment analyst — separated from News/Macro.
    Focuses purely on market sentiment signals: FII/DII flows,
    market breadth, VIX positioning, and options sentiment (PCR).
    """

    name = "Sentiment"

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}
            score = 0.0

            # FII/DII flows
            try:
                from market.flow_intel import get_flow_analysis

                flow = get_flow_analysis()
                data["flow_signal"] = flow.signal
                data["fii_5d"] = flow.fii_5d_net
                data["dii_5d"] = flow.dii_5d_net
                data["divergence"] = flow.divergence
                points.append(f"Flow signal: {flow.signal} (conf: {flow.confidence}%)")
                if flow.divergence:
                    points.append(f"FII-DII divergence: {flow.divergence_type}")
                if flow.signal in ("BULLISH", "NEUTRAL_TO_BULLISH"):
                    score += 25
                elif flow.signal in ("BEARISH", "NEUTRAL_TO_BEARISH"):
                    score -= 25
            except Exception:
                pass

            # Market breadth
            try:
                breadth = self.registry.execute("get_market_breadth", {})
                if isinstance(breadth, dict):
                    ad = breadth.get("ad_ratio")
                    data["ad_ratio"] = ad
                    if ad and ad > 1.5:
                        points.append(f"Breadth: Strong ({ad:.1f} A/D)")
                        score += 15
                    elif ad and ad < 0.7:
                        points.append(f"Breadth: Weak ({ad:.1f} A/D)")
                        score -= 15
                    else:
                        points.append(f"Breadth: Neutral ({ad:.1f} A/D)" if ad else "Breadth: N/A")
            except Exception:
                pass

            # PCR for the symbol (options sentiment)
            try:
                pcr_result = self.registry.execute("get_pcr", {"underlying": symbol})
                if isinstance(pcr_result, dict):
                    pcr = pcr_result.get("pcr")
                    data["pcr"] = pcr
                    if pcr and pcr > 1.3:
                        points.append(f"PCR: {pcr:.2f} (bearish sentiment)")
                        score -= 15
                    elif pcr and pcr < 0.7:
                        points.append(f"PCR: {pcr:.2f} (bullish sentiment)")
                        score += 15
            except Exception:
                pass

            verdict = "BULLISH" if score > 15 else "BEARISH" if score < -15 else "NEUTRAL"
            confidence = min(abs(int(score)) + 30, 100)

            return AnalystReport(
                analyst=self.name,
                verdict=verdict,
                confidence=confidence,
                score=score,
                key_points=points,
                data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )


class SectorRotationAnalyst(BaseAnalyst):
    """
    Tracks sector performance and rotation patterns.
    Compares the stock's sector vs broader market to identify
    tailwinds/headwinds from sector rotation.
    """

    name = "Sector Rotation"

    # Map stocks to their primary sector index
    _SECTOR_MAP = {
        "INFY": "IT",
        "TCS": "IT",
        "WIPRO": "IT",
        "HCLTECH": "IT",
        "TECHM": "IT",
        "HDFCBANK": "BANK",
        "ICICIBANK": "BANK",
        "SBIN": "BANK",
        "KOTAKBANK": "BANK",
        "AXISBANK": "BANK",
        "INDUSINDBK": "BANK",
        "BANDHANBNK": "BANK",
        "SUNPHARMA": "PHARMA",
        "DRREDDY": "PHARMA",
        "CIPLA": "PHARMA",
        "DIVISLAB": "PHARMA",
        "MARUTI": "AUTO",
        "TATAMOTORS": "AUTO",
        "M&M": "AUTO",
        "BAJAJ-AUTO": "AUTO",
        "ITC": "FMCG",
        "HINDUNILVR": "FMCG",
        "NESTLEIND": "FMCG",
        "BRITANNIA": "FMCG",
        "RELIANCE": "ENERGY",
        "ONGC": "ENERGY",
        "NTPC": "ENERGY",
        "POWERGRID": "ENERGY",
        "TATASTEEL": "METAL",
        "JSWSTEEL": "METAL",
        "HINDALCO": "METAL",
        "DLF": "REALTY",
        "GODREJPROP": "REALTY",
        "BAJFINANCE": "FINANCE",
        "BAJFINSV": "FINANCE",
        "HDFCLIFE": "FINANCE",
    }

    def analyze(self, symbol: str, exchange: str = "NSE") -> AnalystReport:
        try:
            points = []
            data: dict[str, Any] = {}
            score = 0.0

            # Get sector snapshot
            try:
                sectors = self.registry.execute("get_sector_snapshot", {})
                if isinstance(sectors, list):
                    data["sectors"] = sectors
                    # Sort by performance
                    sorted_sectors = sorted(
                        [s for s in sectors if isinstance(s, dict)],
                        key=lambda s: s.get("change_pct", 0),
                        reverse=True,
                    )
                    if sorted_sectors:
                        top = sorted_sectors[0]
                        bottom = sorted_sectors[-1]
                        points.append(
                            f"Strongest sector: {top.get('name', '?')} ({top.get('change_pct', 0):+.1f}%)"
                        )
                        points.append(
                            f"Weakest sector: {bottom.get('name', '?')} ({bottom.get('change_pct', 0):+.1f}%)"
                        )
            except Exception:
                pass

            # Check if this stock's sector is in favor
            sector = self._SECTOR_MAP.get(symbol.upper(), "")
            if sector and data.get("sectors"):
                for s in data["sectors"]:
                    s_name = s.get("name", "") if isinstance(s, dict) else ""
                    if sector.upper() in s_name.upper():
                        chg = s.get("change_pct", 0) if isinstance(s, dict) else 0
                        data["stock_sector"] = sector
                        data["sector_change"] = chg
                        if chg > 0.5:
                            points.append(
                                f"{symbol}'s sector ({sector}) is outperforming: {chg:+.1f}%"
                            )
                            score += 20
                        elif chg < -0.5:
                            points.append(
                                f"{symbol}'s sector ({sector}) is underperforming: {chg:+.1f}%"
                            )
                            score -= 20
                        else:
                            points.append(f"{symbol}'s sector ({sector}) is flat: {chg:+.1f}%")
                        break

            if not sector:
                points.append(f"Sector mapping not available for {symbol}")

            verdict = "BULLISH" if score > 10 else "BEARISH" if score < -10 else "NEUTRAL"
            confidence = min(abs(int(score)) + 30, 80)

            return AnalystReport(
                analyst=self.name,
                verdict=verdict,
                confidence=confidence,
                score=score,
                key_points=points,
                data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
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
                    existing = [
                        h
                        for h in holdings
                        if isinstance(h, dict) and h.get("symbol", "").upper() == symbol.upper()
                    ]
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
                analyst=self.name,
                verdict=verdict,
                confidence=70,
                score=score,
                key_points=points,
                data=data,
            )
        except Exception as e:
            return AnalystReport(
                analyst=self.name,
                verdict="UNKNOWN",
                confidence=0,
                score=0,
                error=str(e),
            )


# ── Multi-Agent Orchestrator ─────────────────────────────────


class MultiAgentAnalyzer:
    """
    Orchestrates the full multi-agent analysis pipeline.

    Pipeline:
      1. Run analyst agents (parallel or sequential)
      2. Feed analyst reports into bull/bear debate (5 LLM calls)
      2.5. Three-way risk debate: aggressive / conservative / neutral (3 LLM calls)
           Skipped when scorecard verdict is HOLD — no point sizing a no-trade.
      3. Synthesize final verdict + trade recommendation (1 LLM call)

    Total: ~9 LLM calls per analysis (6 for debate stages, 1 synthesis, 1 news, 1 sentiment).

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
        risk_debate: bool = False,
        progress_callback=None,
    ) -> None:
        self.registry = registry
        self.llm = llm_provider
        self.parallel = parallel
        self.verbose = verbose
        self.risk_debate = risk_debate  # enable 3-way risk debate (aggressive/conservative/neutral)
        self.progress_callback = progress_callback

        news_analyst = NewsMacroAnalyst(registry)
        news_analyst.set_llm(llm_provider)

        self.analysts = [
            TechnicalAnalyst(registry),
            FundamentalAnalyst(registry),
            OptionsAnalyst(registry),
            news_analyst,
            SentimentAnalyst(registry),
            SectorRotationAnalyst(registry),
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

        # Compute scorecard
        scorecard = compute_scorecard(reports)
        if self.verbose:
            console.print(f"\n[dim]{scorecard.summary()}[/dim]")

        # ── Phase 2: Bull/Bear Debate ────────────────────────
        if self.progress_callback:
            self.progress_callback({"type": "phase", "phase": "debate"})
        if self.verbose:
            console.print()
            console.rule(
                "[bold yellow]Researcher Team — Bull vs Bear Debate[/bold yellow]", style="yellow"
            )

        t1 = time.time()
        debate = self._run_debate(symbol, exchange, reports)
        debate_time = time.time() - t1

        if self.verbose:
            self._print_debate(debate, debate_time)

        # ── Phase 2.5: Risk Debate ───────────────────────────
        risk_debate: Optional[RiskDebateResult] = None
        risk_debate_time = 0.0
        if self.risk_debate and scorecard.verdict != "HOLD":
            if self.verbose:
                console.print()
                console.rule(
                    "[bold magenta]Risk Team — Aggressive / Conservative / Neutral[/bold magenta]",
                    style="magenta",
                )
            t_risk = time.time()
            risk_debate = self._run_risk_debate(symbol, exchange, scorecard, debate, reports)
            risk_debate_time = time.time() - t_risk
            if self.verbose:
                console.print(f"[dim]Risk debate completed in {risk_debate_time:.1f}s[/dim]")

        # ── Phase 3: Synthesis ───────────────────────────────
        if self.progress_callback:
            self.progress_callback({"type": "phase", "phase": "synthesis"})
        if self.verbose:
            console.print()
            console.rule("[bold green]Fund Manager — Final Synthesis[/bold green]", style="green")

        t2 = time.time()
        synthesis = self._run_synthesis(symbol, exchange, reports, debate, risk_debate)
        synthesis_time = time.time() - t2

        # ── Phase 4: Store to Memory ─────────────────────────
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
                console.print(f"[dim]  Stored to trade memory (ID: {record.id})[/dim]")
        except Exception:
            pass  # memory storage is non-critical

        # ── Phase 5: Risk Management Team — 3 Perspectives ────
        self.last_trade_plans = {}
        try:
            from engine.trader import TraderAgent

            trader = TraderAgent()
            all_plans = trader.generate_all_plans(
                symbol=symbol,
                exchange=exchange,
                reports=reports,
                synthesis=synthesis,
            )
            self.last_trade_plans = all_plans
            if any(p for p in all_plans.values()):
                TraderAgent.print_all_plans(all_plans)
        except Exception:
            pass  # trade plan generation is non-critical

        # Print timing summary
        total = analyst_time + debate_time + risk_debate_time + synthesis_time
        risk_str = f", risk: {risk_debate_time:.1f}s" if risk_debate_time > 0 else ""
        console.print()
        console.print(
            f"[dim]Analysis complete in {total:.1f}s "
            f"(analysts: {analyst_time:.1f}s, debate: {debate_time:.1f}s"
            f"{risk_str}, synthesis: {synthesis_time:.1f}s)[/dim]"
        )
        console.rule(style="cyan")
        console.print()

        # Build full report for PDF/export (includes everything)
        full_report_parts = [
            f"MULTI-AGENT ANALYSIS: {exchange}:{symbol}",
            f"Date: {time.strftime('%d %b %Y, %I:%M %p')}",
            "",
            "=" * 60,
            "ANALYST REPORTS",
            "=" * 60,
        ]
        for r in reports:
            if not r.error:
                full_report_parts.append(r.summary_text())
                full_report_parts.append("")

        full_report_parts.append(f"\nSCORECARD: {scorecard.summary()}\n")

        full_report_parts.extend(
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
            full_report_parts.extend(
                [
                    "--- BULL REBUTTAL (Round 2) ---",
                    debate.bull_rebuttal,
                    "",
                ]
            )
        if debate.bear_rebuttal:
            full_report_parts.extend(
                [
                    "--- BEAR REBUTTAL (Round 2) ---",
                    debate.bear_rebuttal,
                    "",
                ]
            )
        if debate.facilitator:
            full_report_parts.extend(
                [
                    "--- FACILITATOR SUMMARY ---",
                    debate.facilitator,
                    f"Debate Winner: {debate.winner}",
                    "",
                ]
            )

        full_report_parts.extend(
            [
                "=" * 60,
                "FUND MANAGER SYNTHESIS",
                "=" * 60,
                "",
                synthesis,
            ]
        )

        self.last_full_report = "\n".join(full_report_parts)
        return self.last_full_report

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
            futures = {executor.submit(a.analyze, symbol, exchange): a for a in self.analysts}
            for future in as_completed(futures):
                analyst = futures[future]
                try:
                    report = future.result(timeout=30)
                    reports.append(report)
                    if self.verbose:
                        status = (
                            "[green]OK[/green]"
                            if not report.error
                            else f"[red]FAIL: {report.error[:50]}[/red]"
                        )
                        console.print(f"  [dim]{analyst.name:<15}[/dim] {status}")
                    if self.progress_callback:
                        self.progress_callback({
                            "type": "analyst",
                            "name": analyst.name,
                            "verdict": report.verdict,
                            "confidence": report.confidence,
                            "score": getattr(report, "score", 0),
                            "error": report.error,
                        })
                except Exception as e:
                    reports.append(
                        AnalystReport(
                            analyst=analyst.name,
                            verdict="UNKNOWN",
                            confidence=0,
                            score=0,
                            error=str(e),
                        )
                    )
                    if self.verbose:
                        console.print(f"  [dim]{analyst.name:<15}[/dim] [red]FAIL: {e}[/red]")
                    if self.progress_callback:
                        self.progress_callback({
                            "type": "analyst",
                            "name": analyst.name,
                            "verdict": "UNKNOWN",
                            "confidence": 0,
                            "score": 0,
                            "error": str(e),
                        })

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
                    status = (
                        "[green]OK[/green]"
                        if not report.error
                        else f"[red]FAIL: {report.error[:50]}[/red]"
                    )
                    console.print(f"  [dim]{analyst.name:<15}[/dim] {status}")
            except Exception as e:
                reports.append(
                    AnalystReport(
                        analyst=analyst.name,
                        verdict="UNKNOWN",
                        confidence=0,
                        score=0,
                        error=str(e),
                    )
                )

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
                    r.analyst,
                    "[red]ERROR[/red]",
                    "-",
                    "-",
                    f"[red]{r.error[:60]}[/red]",
                )
            else:
                verdict_style = {
                    "BULLISH": "green",
                    "BEARISH": "red",
                    "NEUTRAL": "yellow",
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

    def _run_debate(self, symbol: str, exchange: str, reports: list[AnalystReport]) -> DebateResult:
        """
        Run multi-round bull/bear debate with facilitator.

        Round 1: Bull builds case → Bear counters
        Round 2: Bull rebuts bear's points → Bear rebuts bull's rebuttal
        Facilitator: Summarizes key agreements, disagreements, and picks a winner.

        Total: 5 LLM calls for debate (bull, bear, bull rebuttal, bear rebuttal, facilitator)
        """
        analyst_context = "\n\n".join(r.summary_text() for r in reports if not r.error)

        # ── Round 1: Opening arguments ───────────────────────
        if self.verbose:
            console.print("\n[bold]Round 1[/bold]")

        # Bull opening
        bull_prompt = BULL_RESEARCHER_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            analyst_data=analyst_context,
        )
        if self.verbose:
            console.print("[green]Bull Researcher[/green] building investment case...")

        bull_argument = self.llm.chat(
            messages=[{"role": "user", "content": bull_prompt}],
            stream=self.verbose,
        )

        # Bear counter
        bear_prompt = BEAR_RESEARCHER_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            analyst_data=analyst_context,
            bull_case=bull_argument,
        )
        if self.verbose:
            console.print("\n[red]Bear Researcher[/red] building counter-argument...")

        bear_argument = self.llm.chat(
            messages=[{"role": "user", "content": bear_prompt}],
            stream=self.verbose,
        )

        # ── Round 2: Rebuttals ───────────────────────────────
        if self.verbose:
            console.print("\n[bold]Round 2[/bold]")

        # Bull rebuttal
        bull_rebuttal_prompt = BULL_REBUTTAL_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            bull_case=bull_argument,
            bear_case=bear_argument,
        )
        if self.verbose:
            console.print("[green]Bull Researcher[/green] responding to bear's points...")

        bull_rebuttal = self.llm.chat(
            messages=[{"role": "user", "content": bull_rebuttal_prompt}],
            stream=self.verbose,
        )

        # Bear rebuttal
        bear_rebuttal_prompt = BEAR_REBUTTAL_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            bear_case=bear_argument,
            bull_rebuttal=bull_rebuttal,
        )
        if self.verbose:
            console.print("\n[red]Bear Researcher[/red] final counter...")

        bear_rebuttal = self.llm.chat(
            messages=[{"role": "user", "content": bear_rebuttal_prompt}],
            stream=self.verbose,
        )

        # ── Facilitator: Summarize & pick winner ─────────────
        facilitator_prompt = FACILITATOR_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            bull_r1=bull_argument,
            bear_r1=bear_argument,
            bull_r2=bull_rebuttal,
            bear_r2=bear_rebuttal,
        )
        if self.verbose:
            console.print("\n[cyan]Facilitator[/cyan] summarizing debate...")

        facilitator_summary = self.llm.chat(
            messages=[{"role": "user", "content": facilitator_prompt}],
            stream=self.verbose,
        )

        # Extract winner from facilitator
        winner = ""
        for line in facilitator_summary.splitlines():
            if "WINNER:" in line.upper():
                if "BULL" in line.upper():
                    winner = "BULL"
                elif "BEAR" in line.upper():
                    winner = "BEAR"
                break

        return DebateResult(
            bull_argument=bull_argument,
            bear_argument=bear_argument,
            bull_rebuttal=bull_rebuttal,
            bear_rebuttal=bear_rebuttal,
            facilitator=facilitator_summary,
            winner=winner,
            rounds=2,
        )

    def _print_debate(self, debate: DebateResult, elapsed: float) -> None:
        """Display the bull/bear debate results."""
        console.print(f"\n[dim]Debate completed in {elapsed:.1f}s[/dim]")

    # ── Phase 2.5: Risk Debate ───────────────────────────────

    def _run_risk_debate(
        self,
        symbol: str,
        exchange: str,
        scorecard: AnalystScorecard,
        debate: DebateResult,
        reports: list[AnalystReport],
    ) -> RiskDebateResult:
        """
        Three-way risk debate: Aggressive / Conservative / Neutral.

        Each debater receives the scorecard + investment debate and argues
        for a different position-sizing and risk-management approach.
        A consensus note is derived from all three views.

        Total: 3 LLM calls (one per debater).
        Only called when scorecard.verdict != HOLD.
        """
        # Build shared context for all three debaters
        risk_report = next((r for r in reports if r.analyst == "Risk Manager"), None)
        risk_params = ""
        if risk_report and not risk_report.error:
            risk_params = (
                f"Capital: {risk_report.data.get('capital', 'N/A')} | "
                f"Max risk/trade: {risk_report.data.get('max_risk_per_trade', 'N/A')} | "
                f"VIX: {risk_report.data.get('vix', 'N/A')}"
            )

        debate_summary = (
            f"Investment debate winner: {debate.winner}\nFacilitator summary: {debate.facilitator}"
        )
        scorecard_summary = scorecard.summary()

        shared_context = dict(
            symbol=symbol,
            exchange=exchange,
            scorecard=scorecard_summary,
            debate_summary=debate_summary,
            risk_params=risk_params,
        )

        # Aggressive debater
        if self.verbose:
            console.print("[bold red]Aggressive[/bold red] debater — maximum upside, tight risk...")
        aggressive_view = self.llm.chat(
            messages=[
                {"role": "user", "content": AGGRESSIVE_DEBATER_PROMPT.format(**shared_context)}
            ],
            stream=self.verbose,
        )

        # Conservative debater
        if self.verbose:
            console.print(
                "\n[bold blue]Conservative[/bold blue] debater — capital preservation first..."
            )
        conservative_view = self.llm.chat(
            messages=[
                {"role": "user", "content": CONSERVATIVE_DEBATER_PROMPT.format(**shared_context)}
            ],
            stream=self.verbose,
        )

        # Neutral debater
        if self.verbose:
            console.print("\n[bold cyan]Neutral[/bold cyan] debater — calibrated middle path...")
        neutral_view = self.llm.chat(
            messages=[
                {
                    "role": "user",
                    "content": NEUTRAL_DEBATER_PROMPT.format(
                        **shared_context,
                        aggressive_view=aggressive_view,
                        conservative_view=conservative_view,
                    ),
                }
            ],
            stream=self.verbose,
        )

        # Extract consensus sizing from neutral view (first line with % or ₹)
        consensus = neutral_view.splitlines()[0] if neutral_view else ""

        return RiskDebateResult(
            aggressive_view=aggressive_view,
            conservative_view=conservative_view,
            neutral_view=neutral_view,
            consensus=consensus,
        )

    # ── Phase 3: Synthesis ───────────────────────────────────

    def _run_synthesis(
        self,
        symbol: str,
        exchange: str,
        reports: list[AnalystReport],
        debate: DebateResult,
        risk_debate: Optional[RiskDebateResult] = None,
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

        # Memory: past analyses for this symbol
        memory_context = ""
        try:
            from engine.memory import trade_memory

            memory_context = trade_memory.get_context_for_symbol(symbol)
        except Exception:
            pass

        # Patterns: active India-specific patterns
        pattern_context = ""
        try:
            from engine.patterns import get_pattern_context

            pattern_context = get_pattern_context()
        except Exception:
            pass

        # Build debate section with full multi-round context
        debate_text = (
            f"## Bull Case (Round 1)\n{debate.bull_argument}\n\n"
            f"## Bear Case (Round 1)\n{debate.bear_argument}\n\n"
        )
        if debate.bull_rebuttal:
            debate_text += f"## Bull Rebuttal (Round 2)\n{debate.bull_rebuttal}\n\n"
        if debate.bear_rebuttal:
            debate_text += f"## Bear Rebuttal (Round 2)\n{debate.bear_rebuttal}\n\n"
        if debate.facilitator:
            debate_text += f"## Facilitator Summary\n{debate.facilitator}\n\n"
            debate_text += f"Debate Winner: {debate.winner}\n"

        # Build risk debate section
        risk_debate_text = ""
        if risk_debate:
            risk_debate_text = (
                f"## Aggressive View\n{risk_debate.aggressive_view}\n\n"
                f"## Conservative View\n{risk_debate.conservative_view}\n\n"
                f"## Neutral Synthesis\n{risk_debate.neutral_view}"
            )

        synthesis_prompt = SYNTHESIS_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            analyst_data=analyst_context,
            debate_text=debate_text,
            risk_debate_text=risk_debate_text,
            risk_context=risk_context,
            memory_context=memory_context,
            pattern_context=pattern_context,
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

BULL_REBUTTAL_PROMPT = """You are the BULLISH researcher. The BEAR researcher has countered your case for {symbol} ({exchange}).

Your original bull case:
{bull_case}

Bear's counter-argument:
{bear_case}

Respond to the bear's strongest points. For each bear argument:
1. Acknowledge valid concerns (don't dismiss legitimate risks)
2. Provide counter-evidence or explain why the risk is overstated
3. Reinforce the strongest parts of your bull case that weren't adequately challenged
4. Address the timing question: even if bear is right long-term, is the short-term setup favorable?

Keep it concise (150-200 words). This is Round 2 — be surgical, not repetitive."""

BEAR_REBUTTAL_PROMPT = """You are the BEARISH researcher. The BULL researcher has responded to your counter-argument for {symbol} ({exchange}).

Your original bear case:
{bear_case}

Bull's rebuttal:
{bull_rebuttal}

Final counter-argument:
1. Which of your original concerns did the bull fail to address?
2. Point out any circular reasoning or wishful thinking in the rebuttal
3. If the bull made valid points, concede them honestly
4. State your final position: should this trade be taken, and if so, with what modifications?

Keep it concise (150-200 words). This is your final word — make it count."""

FACILITATOR_PROMPT = """You are the DEBATE FACILITATOR reviewing the {symbol} ({exchange}) investment debate.

## Round 1 — Opening Arguments
Bull: {bull_r1}
Bear: {bear_r1}

## Round 2 — Rebuttals
Bull Rebuttal: {bull_r2}
Bear Rebuttal: {bear_r2}

Summarize the debate outcome. Provide:

AGREEMENTS:
- [points both sides agree on]

DISAGREEMENTS:
- [unresolved points of contention]

KEY INSIGHT: [the single most important takeaway from this debate]

WINNER: [BULL / BEAR] — which researcher presented the stronger, more evidence-backed case?

VERDICT MODIFIER: [Should the fund manager lean more bullish or bearish based on debate quality? Any conditions?]

Keep it to 100-150 words. Be objective."""

SYNTHESIS_PROMPT = """You are the FUND MANAGER at an Indian trading firm.
You must make the final call on {symbol} ({exchange}) after reviewing all evidence.

## Analyst Reports
{analyst_data}

## Research Debate (2 Rounds)
{debate_text}

## Risk Team Debate (Aggressive / Conservative / Neutral)
{risk_debate_text}

## Risk Parameters
{risk_context}

## Trade Memory (Past Analyses)
{memory_context}

## Active Market Patterns (India-Specific)
{pattern_context}

## Your Task
Weigh the bull and bear arguments against the analyst data. Consider:
- Which side has stronger evidence?
- What does the risk profile suggest?
- Is the timing right (technicals, events, VIX)?
- Where do the three risk views (aggressive/conservative/neutral) converge on sizing?

**Decisiveness rule**: Do NOT default to HOLD simply because both sides raised valid points.
Every debate has a stronger side — identify it and commit to that stance.
HOLD is only correct when the evidence is genuinely split AND the risk/reward is unfavourable.

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

AGGRESSIVE_DEBATER_PROMPT = """You are the AGGRESSIVE RISK MANAGER at an Indian trading firm.
The investment team has decided to trade {symbol} ({exchange}).

## Scorecard
{scorecard}

## Investment Debate Outcome
{debate_summary}

## Risk Parameters
{risk_params}

Your role: argue for the most aggressive but still rational position sizing.

Make the case for:
1. **Position size**: Why should we deploy maximum permitted capital (up to 20% of portfolio)?
2. **Stop-loss**: Argue for a tighter stop — we have conviction, don't give back too much if wrong
3. **Strategy**: Prefer higher-leverage instruments (options, futures) over delivery if the setup warrants it
4. **Hedging**: Minimal or no hedge — hedges cost premium and dilute returns when we're right

Be specific: suggest a concrete position size (% of capital or lot count), stop level, and strategy.
Cite the strongest signals from the scorecard and debate to justify maximum aggression.
Keep it to 150-200 words. All prices in INR."""

CONSERVATIVE_DEBATER_PROMPT = """You are the CONSERVATIVE RISK MANAGER at an Indian trading firm.
The investment team has decided to trade {symbol} ({exchange}).

## Scorecard
{scorecard}

## Investment Debate Outcome
{debate_summary}

## Risk Parameters
{risk_params}

Your role: argue for a cautious, capital-preserving approach to this trade.

Make the case for:
1. **Position size**: Why should we start small (3-5% of capital) and add only on confirmation?
2. **Stop-loss**: Argue for a wider stop — avoid being shaken out by normal volatility
3. **Strategy**: Prefer defined-risk structures (spreads, delivery) over naked options or futures
4. **Hedging**: Recommend a protective hedge — the cost is worth the downside protection given market conditions

Be specific: suggest a concrete position size, stop level, hedge instrument, and entry approach (phased or single).
Cite the weakest signals or biggest risks from the scorecard and debate to justify caution.
Keep it to 150-200 words. All prices in INR."""

NEUTRAL_DEBATER_PROMPT = """You are the NEUTRAL RISK ARBITRATOR at an Indian trading firm.
You have heard two positions on how to size the {symbol} ({exchange}) trade.

## Scorecard
{scorecard}

## Investment Debate Outcome
{debate_summary}

## Risk Parameters
{risk_params}

## Aggressive View
{aggressive_view}

## Conservative View
{conservative_view}

Your role: synthesise a calibrated, evidence-based position between the two extremes.

Provide:
1. **Recommended position size**: A specific % of capital or lot count — not a range, a number
2. **Stop-loss level**: One specific price or % from entry
3. **Strategy**: The single best instrument/structure for this setup
4. **Hedge (if any)**: Only if VIX is elevated or conviction is below 65%
5. **Entry approach**: All-in at market, or phased entry with levels

Acknowledge the strongest point from each side, then commit to one calibrated recommendation.
Keep it to 150-200 words. All prices in INR."""


NEWS_SENTIMENT_PROMPT = """You are a NEWS & SENTIMENT ANALYST at an Indian trading firm.
Analyze the following news headlines and macro data for {symbol} ({exchange}).

## Recent Headlines
{headlines}

## Macro Context
{macro_data}

Provide a structured sentiment assessment. Consider:
- Is the news flow positive, negative, or mixed for this stock?
- Are there sector-wide or macro tailwinds/headwinds?
- Any upcoming catalysts or risks (earnings, policy, expiry)?
- How might FII/DII flows impact sentiment?
- Distinguish between noise and signal — not every headline matters.

Respond in EXACTLY this format (no extra text before or after):

SENTIMENT: [BULLISH / BEARISH / NEUTRAL]
SCORE: [number from -100 to +100]
CONFIDENCE: [0-100]%
- [key insight 1 — most important finding]
- [key insight 2 — second finding]
- [key insight 3 — third finding, if relevant]"""
