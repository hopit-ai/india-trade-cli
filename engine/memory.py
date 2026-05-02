"""
engine/memory.py
────────────────
Trade Memory — stores every analysis and recommendation as situation-outcome
pairs for future recall.

When the multi-agent pipeline analyzes a stock, the context and recommendation
are stored. Later, analysts can query: "What happened last time VIX was this
high?" or "How did our RELIANCE calls perform?"

Persistence: ~/.trading_platform/trade_memory.json

Usage:
    from engine.memory import trade_memory

    # Store an analysis
    trade_memory.store(
        symbol="RELIANCE",
        verdict="BUY",
        confidence=75,
        context={...},       # market snapshot at time of analysis
        recommendation={...}, # entry, SL, target
    )

    # Query past analyses
    results = trade_memory.query(symbol="RELIANCE")
    results = trade_memory.query(verdict="BUY", min_confidence=70)
    results = trade_memory.query(conditions={"vix_above": 20})

    # Record outcome (when trade is closed)
    trade_memory.record_outcome(trade_id, actual_pnl=1250.0, notes="Hit target")

    # Get performance stats
    stats = trade_memory.get_stats()
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.schema_parser import parse_synthesis_output as _parse_synthesis_output

console = Console()

MEMORY_FILE = Path.home() / ".trading_platform" / "trade_memory.json"
MAX_MEMORIES = 500  # cap to prevent unbounded growth


# ── Data Model ───────────────────────────────────────────────


@dataclass
class TradeRecord:
    """A single analysis + recommendation, with optional outcome."""

    id: str  # unique ID
    timestamp: str  # ISO format
    symbol: str
    exchange: str

    # Analysis context (market state at time of analysis)
    verdict: str  # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
    confidence: int  # 0-100
    analyst_scores: dict = field(default_factory=dict)  # {"Technical": 45, "Fundamental": 72, ...}

    # Market context snapshot
    vix: Optional[float] = None
    nifty_level: Optional[float] = None
    nifty_change: Optional[float] = None  # % change on analysis day
    fii_net: Optional[float] = None  # FII net buy/sell in Cr
    sector: Optional[str] = None

    # Recommendation
    strategy: str = ""  # e.g. "Bull Call Spread", "Delivery Buy"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward: Optional[str] = None

    # Debate summary
    debate_winner: str = ""  # "BULL" or "BEAR"
    bull_summary: str = ""  # 1-2 sentence summary
    bear_summary: str = ""

    # Outcome (filled later when trade is closed)
    outcome: Optional[str] = None  # "WIN" / "LOSS" / "BREAKEVEN" / "EXPIRED"
    actual_pnl: Optional[float] = None  # realized P&L
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    hold_days: Optional[int] = None
    outcome_notes: str = ""

    # Analysis snapshot (#122)
    price_at_analysis: Optional[float] = None  # LTP at time of analysis
    synthesis_text: str = ""  # full raw LLM synthesis output
    analysis_snapshot: dict = field(default_factory=dict)  # key metrics at analysis time

    # Reflection (#92) — LLM-extracted lesson from outcome
    lesson: str = ""

    # Tags for filtering
    tags: list[str] = field(default_factory=list)


# ── Trade Memory Manager ─────────────────────────────────────


class TradeMemory:
    """Persistent store for trade analyses and their outcomes."""

    def __init__(self) -> None:
        self._records: list[TradeRecord] = []
        self._load()

    # ── Store ────────────────────────────────────────────────

    def store(
        self,
        symbol: str,
        exchange: str = "NSE",
        verdict: str = "",
        confidence: int = 0,
        analyst_scores: Optional[dict] = None,
        vix: Optional[float] = None,
        nifty_level: Optional[float] = None,
        nifty_change: Optional[float] = None,
        fii_net: Optional[float] = None,
        strategy: str = "",
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
        risk_reward: Optional[str] = None,
        debate_winner: str = "",
        bull_summary: str = "",
        bear_summary: str = "",
        tags: Optional[list[str]] = None,
        raw_synthesis: str = "",
        price_at_analysis: Optional[float] = None,
        synthesis_text: str = "",
        analysis_snapshot: Optional[dict] = None,
    ) -> TradeRecord:
        """Store a new analysis/recommendation."""
        record = TradeRecord(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(timespec="seconds"),
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            verdict=verdict,
            confidence=confidence,
            analyst_scores=analyst_scores or {},
            vix=vix,
            nifty_level=nifty_level,
            nifty_change=nifty_change,
            fii_net=fii_net,
            strategy=strategy,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            risk_reward=risk_reward,
            debate_winner=debate_winner,
            bull_summary=bull_summary,
            bear_summary=bear_summary,
            tags=tags or [],
            price_at_analysis=price_at_analysis,
            synthesis_text=synthesis_text or raw_synthesis,
            analysis_snapshot=analysis_snapshot or {},
        )

        self._records.append(record)

        # Cap the list
        if len(self._records) > MAX_MEMORIES:
            self._records = self._records[-MAX_MEMORIES:]

        self._save()
        return record

    def store_from_analysis(
        self,
        symbol: str,
        exchange: str,
        analyst_reports: list,  # list of AnalystReport
        debate: Any,  # DebateResult
        synthesis: str,  # raw LLM output
        price: Optional[float] = None,  # spot price at time of analysis (#122)
    ) -> TradeRecord:
        """
        Store a record directly from multi-agent pipeline output.
        Extracts structured data from analyst reports and synthesis text.
        """
        # Extract analyst scores
        scores = {}
        vix = None
        fii_net = None

        for report in analyst_reports:
            if hasattr(report, "analyst") and hasattr(report, "score"):
                scores[report.analyst] = report.score

                # Extract market context from Risk Manager
                if report.analyst == "Risk Manager" and hasattr(report, "data"):
                    vix = report.data.get("vix")

                # Extract FII data from News & Macro
                if report.analyst == "News & Macro" and hasattr(report, "data"):
                    fii_dii = report.data.get("fii_dii", [])
                    if fii_dii and isinstance(fii_dii, list) and fii_dii:
                        latest = fii_dii[0] if isinstance(fii_dii[0], dict) else {}
                        fii_net = latest.get("fii_net")

        # Parse verdict and confidence from synthesis text
        verdict, confidence, strategy = _parse_synthesis_output(synthesis)

        # Debate info
        debate_winner = ""
        bull_summary = ""
        bear_summary = ""
        if debate:
            if hasattr(debate, "bull_argument"):
                bull_summary = _truncate(debate.bull_argument, 200)
            if hasattr(debate, "bear_argument"):
                bear_summary = _truncate(debate.bear_argument, 200)
            if hasattr(debate, "winner"):
                debate_winner = debate.winner

        # Build analysis snapshot — compact dict of key metrics (#122)
        snapshot: dict = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "verdict": verdict,
            "confidence": confidence,
        }
        if price is not None:
            snapshot["price"] = price
        if vix is not None:
            snapshot["vix"] = vix
        if fii_net is not None:
            snapshot["fii_net"] = fii_net
        if scores:
            snapshot["analyst_scores"] = scores

        return self.store(
            symbol=symbol,
            exchange=exchange,
            verdict=verdict,
            confidence=confidence,
            analyst_scores=scores,
            vix=vix,
            fii_net=fii_net,
            strategy=strategy,
            debate_winner=debate_winner,
            bull_summary=bull_summary,
            bear_summary=bear_summary,
            synthesis_text=synthesis,
            price_at_analysis=price,
            analysis_snapshot=snapshot,
        )

    # ── Record Outcome ───────────────────────────────────────

    def record_outcome(
        self,
        trade_id: str,
        outcome: str = "",  # WIN / LOSS / BREAKEVEN
        actual_pnl: Optional[float] = None,
        exit_price: Optional[float] = None,
        notes: str = "",
    ) -> bool:
        """Update a trade record with the actual outcome."""
        record = self.get_by_id(trade_id)
        if not record:
            return False

        record.outcome = outcome.upper()
        record.actual_pnl = actual_pnl
        record.exit_price = exit_price
        record.exit_date = datetime.now().isoformat(timespec="seconds")
        record.outcome_notes = notes

        if record.timestamp and record.exit_date:
            try:
                start = datetime.fromisoformat(record.timestamp)
                end = datetime.fromisoformat(record.exit_date)
                record.hold_days = (end - start).days
            except Exception:
                pass

        self._save()
        return True

    def reflect_and_remember(self, trade_id: str, llm_provider=None) -> str:
        """
        Run reflection on a closed trade and store a lesson (#92).

        Uses LLM if provided; falls back to rule-based lesson extraction.
        Returns the lesson string (or "" if trade not found).
        """
        record = self.get_by_id(trade_id)
        if not record:
            return ""

        # Try LLM first
        if llm_provider:
            try:
                lesson = self._llm_reflect(record, llm_provider)
                if lesson:
                    record.lesson = lesson
                    self._save()
                    return lesson
            except Exception:
                pass  # fall through to rule-based

        # Rule-based fallback
        lesson = self._rule_reflect(record)
        record.lesson = lesson
        self._save()
        return lesson

    def _llm_reflect(self, record: "TradeRecord", llm_provider) -> str:
        """Use LLM to extract a lesson from the trade record."""
        prompt = (
            f"A trade on {record.symbol} ({record.exchange}) was analysed on {record.timestamp[:10]}.\n"
            f"Verdict: {record.verdict} (confidence: {record.confidence}%)\n"
            f"Strategy: {record.strategy or 'unspecified'}\n"
        )
        if record.entry_price:
            prompt += f"Entry: {record.entry_price}, SL: {record.stop_loss}, Target: {record.target_price}\n"
        if record.vix is not None:
            prompt += f"VIX at analysis: {record.vix:.1f}\n"
        if record.synthesis_text:
            prompt += f"\nBull thesis: {record.bull_summary}\nBear thesis: {record.bear_summary}\n"
        prompt += (
            f"\nOutcome: {record.outcome or 'unknown'}, P&L: {record.actual_pnl:+,.0f}\n"
            if record.actual_pnl is not None
            else "\nOutcome: unknown\n"
        )
        prompt += (
            "\nIn 1-3 sentences, what is the most important trading lesson from this trade? "
            "Be specific: mention the signal, market conditions, and what worked or failed."
        )
        return llm_provider.chat(
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )

    @staticmethod
    def _rule_reflect(record: "TradeRecord") -> str:
        """Rule-based lesson extraction when no LLM is available."""
        outcome = (record.outcome or "").upper()
        pnl_str = (
            f" (+{record.actual_pnl:,.0f})"
            if record.actual_pnl and record.actual_pnl > 0
            else (f" ({record.actual_pnl:,.0f})" if record.actual_pnl else "")
        )
        if outcome == "WIN":
            return (
                f"The {record.verdict} signal on {record.symbol} was correct{pnl_str}. "
                f"Similar setups may work in the future."
            )
        elif outcome == "LOSS":
            return (
                f"The {record.verdict} signal on {record.symbol} was incorrect{pnl_str}. "
                f"Review the thesis and consider tightening the stop-loss."
            )
        elif outcome in ("BREAKEVEN", "EXPIRED"):
            return (
                f"The {record.symbol} trade was a wash — "
                f"market conditions may have changed after the {record.verdict} signal."
            )
        return (
            f"Trade on {record.symbol} ({record.verdict}) — outcome not yet recorded. "
            f"Update with result to generate a lesson."
        )

    # ── Query ────────────────────────────────────────────────

    def query(
        self,
        symbol: Optional[str] = None,
        verdict: Optional[str] = None,
        min_confidence: int = 0,
        outcome: Optional[str] = None,
        limit: int = 20,
        days_back: Optional[int] = None,
        vix_above: Optional[float] = None,
        vix_below: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> list[TradeRecord]:
        """Query trade memory with filters."""
        results = list(self._records)

        if symbol:
            results = [r for r in results if r.symbol == symbol.upper()]

        if verdict:
            results = [r for r in results if r.verdict == verdict.upper()]

        if min_confidence > 0:
            results = [r for r in results if r.confidence >= min_confidence]

        if outcome:
            results = [r for r in results if r.outcome == outcome.upper()]

        if days_back:
            cutoff = datetime.now().isoformat(timespec="seconds")
            try:
                from datetime import timedelta

                cutoff_dt = datetime.now() - timedelta(days=days_back)
                cutoff = cutoff_dt.isoformat(timespec="seconds")
                results = [r for r in results if r.timestamp >= cutoff]
            except Exception:
                pass

        if vix_above is not None:
            results = [r for r in results if r.vix is not None and r.vix >= vix_above]

        if vix_below is not None:
            results = [r for r in results if r.vix is not None and r.vix <= vix_below]

        if tag:
            results = [r for r in results if tag in r.tags]

        # Most recent first
        results.reverse()
        return results[:limit]

    def get_by_id(self, trade_id: str) -> Optional[TradeRecord]:
        """Get a specific trade record by ID."""
        for r in self._records:
            if r.id == trade_id:
                return r
        return None

    def get_symbol_history(self, symbol: str, limit: int = 10) -> list[TradeRecord]:
        """Get all past analyses for a specific symbol."""
        return self.query(symbol=symbol, limit=limit)

    def get_similar_conditions(
        self,
        vix: Optional[float] = None,
        fii_net: Optional[float] = None,
        tolerance: float = 0.2,
    ) -> list[TradeRecord]:
        """
        Find past trades made under similar market conditions.
        Useful for: "Last time VIX was ~18 and FII were selling, what did we do?"
        """
        results = []
        for r in self._records:
            match = True

            if vix is not None and r.vix is not None:
                if abs(r.vix - vix) / max(vix, 1) > tolerance:
                    match = False

            if fii_net is not None and r.fii_net is not None:
                # Same direction (both buying or both selling)
                if (fii_net > 0) != (r.fii_net > 0):
                    match = False

            if match:
                results.append(r)

        results.reverse()
        return results[:10]

    # ── Stats ────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get overall performance statistics."""
        total = len(self._records)
        with_outcome = [r for r in self._records if r.outcome]
        wins = [r for r in with_outcome if r.outcome == "WIN"]
        losses = [r for r in with_outcome if r.outcome == "LOSS"]

        total_pnl = sum(r.actual_pnl for r in with_outcome if r.actual_pnl is not None)
        avg_pnl = total_pnl / len(with_outcome) if with_outcome else 0

        # Verdict distribution
        verdicts = {}
        for r in self._records:
            verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1

        # Most analyzed symbols
        symbols = {}
        for r in self._records:
            symbols[r.symbol] = symbols.get(r.symbol, 0) + 1
        top_symbols = sorted(symbols.items(), key=lambda x: -x[1])[:5]

        # Average confidence
        avg_confidence = sum(r.confidence for r in self._records) / total if total else 0

        # Win rate: only meaningful with ≥5 outcomes (#123)
        _min_outcomes_for_rate = 5
        _tracked = len(with_outcome)
        if _tracked >= _min_outcomes_for_rate:
            win_rate: Optional[float] = round(len(wins) / _tracked * 100, 1)
            win_rate_label = f"{len(wins)}/{_tracked} tracked ({win_rate:.0f}%)"
        elif _tracked > 0:
            win_rate = None
            win_rate_label = f"{len(wins)}/{_tracked} tracked (insufficient data)"
        else:
            win_rate = None
            win_rate_label = "No outcomes recorded"

        return {
            "total_analyses": total,
            "with_outcome": _tracked,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "win_rate_label": win_rate_label,
            "win_rate_insufficient": _tracked < _min_outcomes_for_rate,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "avg_confidence": round(avg_confidence, 1),
            "verdict_distribution": verdicts,
            "top_symbols": top_symbols,
        }

    def count(self) -> int:
        return len(self._records)

    # ── Display ──────────────────────────────────────────────

    def print_recent(self, n: int = 10) -> None:
        """Display recent analyses as a Rich table."""
        recent = list(reversed(self._records[-n:]))
        if not recent:
            console.print("[dim]No trade memories stored yet.[/dim]")
            return

        table = Table(title=f"Recent Analyses ({len(self._records)} total)", show_lines=False)
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Date", style="dim", width=12)
        table.add_column("Symbol", style="bold", width=12)
        table.add_column("Verdict", width=12)
        table.add_column("Conf", justify="right", width=6)
        table.add_column("Strategy", width=20)
        table.add_column("Outcome", width=10)
        table.add_column("P&L", justify="right", width=12)

        for r in recent:
            verdict_style = {
                "STRONG_BUY": "bold green",
                "BUY": "green",
                "HOLD": "yellow",
                "SELL": "red",
                "STRONG_SELL": "bold red",
            }.get(r.verdict, "white")

            outcome_str = ""
            if r.outcome:
                o_style = (
                    "green" if r.outcome == "WIN" else "red" if r.outcome == "LOSS" else "yellow"
                )
                outcome_str = f"[{o_style}]{r.outcome}[/{o_style}]"

            pnl_str = ""
            if r.actual_pnl is not None:
                p_style = "green" if r.actual_pnl >= 0 else "red"
                pnl_str = f"[{p_style}]{r.actual_pnl:+,.0f}[/{p_style}]"

            date_str = r.timestamp[:10] if r.timestamp else ""

            table.add_row(
                r.id,
                date_str,
                r.symbol,
                f"[{verdict_style}]{r.verdict}[/{verdict_style}]",
                f"{r.confidence}%",
                r.strategy[:20] if r.strategy else "-",
                outcome_str or "-",
                pnl_str or "-",
            )

        console.print(table)

    def print_stats(self) -> None:
        """Display performance statistics."""
        stats = self.get_stats()

        lines = []
        lines.append(f"  Total Analyses : {stats['total_analyses']}")
        lines.append(f"  With Outcomes  : {stats['with_outcome']}")
        if stats["with_outcome"]:
            lines.append(f"  Win Rate       : {stats['win_rate']}%")
            lines.append(f"  Total P&L      : {stats['total_pnl']:+,.0f}")
            lines.append(f"  Avg P&L/Trade  : {stats['avg_pnl']:+,.0f}")
        lines.append(f"  Avg Confidence : {stats['avg_confidence']}%")

        if stats["top_symbols"]:
            syms = ", ".join(f"{s}({c})" for s, c in stats["top_symbols"])
            lines.append(f"  Top Symbols    : {syms}")

        if stats["verdict_distribution"]:
            vd = ", ".join(f"{k}:{v}" for k, v in stats["verdict_distribution"].items())
            lines.append(f"  Verdicts       : {vd}")

        console.print(
            Panel(
                "\n".join(lines),
                title="[bold cyan]Trade Memory Stats[/bold cyan]",
                border_style="cyan",
            )
        )

    # ── Context for LLM ──────────────────────────────────────

    def get_context_for_symbol(self, symbol: str) -> str:
        """
        Generate a text summary of past analyses for a symbol,
        suitable for injecting into LLM prompts.
        """
        history = self.get_symbol_history(symbol, limit=5)
        if not history:
            return f"No previous analyses found for {symbol}."

        parts = [f"Past analyses for {symbol} ({len(history)} most recent):"]
        for r in history:
            line = f"  [{r.timestamp[:10]}] {r.verdict} (conf: {r.confidence}%)"
            if r.strategy:
                line += f" — {r.strategy}"
            if r.outcome:
                line += f" → {r.outcome}"
                if r.actual_pnl is not None:
                    line += f" (P&L: {r.actual_pnl:+,.0f})"
            if r.vix is not None:
                line += f" | VIX={r.vix:.1f}"
            if getattr(r, "price_at_analysis", None) is not None:
                line += f" | ₹{r.price_at_analysis:.0f}"
            parts.append(line)
            # Include snapshot summary if available
            snap = getattr(r, "analysis_snapshot", {})
            if snap and snap.get("analyst_scores"):
                scores_str = ", ".join(
                    f"{k}:{v}" for k, v in snap["analyst_scores"].items()
                )
                parts.append(f"    Scores: {scores_str}")
            if getattr(r, "lesson", ""):
                parts.append(f"    Lesson: {r.lesson}")

        return "\n".join(parts)

    def get_context_for_conditions(
        self, vix: Optional[float] = None, fii_net: Optional[float] = None
    ) -> str:
        """
        Generate text summary of past trades under similar conditions,
        for injecting into LLM prompts.
        """
        similar = self.get_similar_conditions(vix=vix, fii_net=fii_net)
        if not similar:
            return "No past trades found under similar market conditions."

        parts = [f"Past trades under similar conditions ({len(similar)} found):"]
        for r in similar:
            line = f"  [{r.timestamp[:10]}] {r.symbol}: {r.verdict}"
            if r.outcome:
                line += f" → {r.outcome}"
                if r.actual_pnl is not None:
                    line += f" ({r.actual_pnl:+,.0f})"
            if r.vix is not None:
                line += f" | VIX={r.vix:.1f}"
            parts.append(line)

        return "\n".join(parts)

    # ── Persistence ──────────────────────────────────────────

    def _save(self) -> None:
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(r) for r in self._records]
            MEMORY_FILE.write_text(json.dumps(data, indent=2, default=str))
        except Exception:
            pass

    def _load(self) -> None:
        try:
            if MEMORY_FILE.exists():
                data = json.loads(MEMORY_FILE.read_text())
                # Backward compat: strip unknown keys, fill missing with defaults
                valid_fields = set(TradeRecord.__dataclass_fields__.keys())
                records = []
                for d in data:
                    filtered = {k: v for k, v in d.items() if k in valid_fields}
                    try:
                        records.append(TradeRecord(**filtered))
                    except Exception:
                        pass  # skip corrupt records
                self._records = records
        except Exception:
            self._records = []


# ── Helpers ──────────────────────────────────────────────────


def _parse_synthesis(text: str) -> tuple[str, int, str]:
    """
    Extract verdict, confidence, and strategy from synthesis LLM output.

    Thin wrapper around agent.schema_parser.parse_synthesis_output for
    backward compatibility with code that imports _parse_synthesis directly.
    """
    return _parse_synthesis_output(text)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# ── Singleton ────────────────────────────────────────────────

trade_memory = TradeMemory()
