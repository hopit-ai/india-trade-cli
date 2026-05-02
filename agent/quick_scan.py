"""
agent/quick_scan.py
────────────────────
Quick scan mode — single-agent fast analysis in 3–5 seconds (#153).

Gathers technical + fundamental data (pure Python, no LLM), then makes
a single LLM call asking for a structured verdict.

Compare:
  quick analyze → 1 LLM call, 3-5s, signal-level
  analyze        → 8 LLM calls, 30-90s, full debate
  deep-analyze   → 11 LLM calls, 3-8min, institutional

Usage:
    from agent.quick_scan import QuickScanner

    scanner = QuickScanner(provider=my_provider)
    result = scanner.scan("INFY")
    print(result.verdict, result.confidence, result.reasons)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuickScanResult:
    """Result of a quick single-agent scan."""

    symbol: str
    verdict: str  # BUY / SELL / HOLD
    confidence: int  # 0-100
    reasons: list[str]  # 3-5 bullet points
    entry: Optional[float]
    sl: Optional[float]
    target: Optional[float]
    ltp: float  # live price at scan time
    elapsed_ms: int
    error: Optional[str] = None


# ── Response parser ───────────────────────────────────────────


def _parse_quick_response(text: str) -> dict:
    """
    Parse structured LLM response into components.

    Expected format (flexible — handles markdown, extra text):
        VERDICT: BUY
        CONFIDENCE: 72
        REASON:
        - RSI 54 neutral
        - PE 18x below sector avg
        ENTRY: 1410
        SL: 1370
        TARGET: 1480
    """
    result = {
        "verdict": "HOLD",
        "confidence": 50,
        "reasons": [],
        "entry": None,
        "sl": None,
        "target": None,
    }

    # Verdict
    m = re.search(
        r"verdict\s*[:\s]\s*\*{0,2}(STRONG_BUY|STRONG_SELL|BUY|SELL|HOLD)\*{0,2}",
        text,
        re.IGNORECASE,
    )
    if m:
        result["verdict"] = m.group(1).upper()

    # Confidence
    m = re.search(r"confidence\s*[:\s]\s*\*{0,2}(\d+)\s*%?\*{0,2}", text, re.IGNORECASE)
    if m:
        try:
            result["confidence"] = int(m.group(1))
        except ValueError:
            pass

    # Reasons — lines starting with dash/bullet after REASON:
    reason_section = re.search(
        r"reason[s]?\s*[:\s](.*?)(?:entry|sl|stop|target|$)", text, re.IGNORECASE | re.DOTALL
    )
    if reason_section:
        raw = reason_section.group(1)
        bullets = re.findall(r"[-•*]\s*(.+?)(?:\n|$)", raw)
        if bullets:
            result["reasons"] = [b.strip() for b in bullets if b.strip()][:5]
        else:
            # Fallback: split by newlines
            lines = [
                l.strip() for l in raw.splitlines() if l.strip() and not l.strip().startswith("#")
            ]
            result["reasons"] = lines[:5]

    # Entry, SL, Target — parse price values
    for key, pattern in [
        ("entry", r"entry\s*[:\s]\s*₹?\s*([0-9,.]+)"),
        ("sl", r"(?:sl|stop[-\s]?loss)\s*[:\s]\s*₹?\s*([0-9,.]+)"),
        ("target", r"target\s*[:\s]\s*₹?\s*([0-9,.]+)"),
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                result[key] = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    return result


# ── Prompt builder ────────────────────────────────────────────


_QUICK_PROMPT = """You are a senior equity analyst giving a rapid directional view on a stock.

Symbol: {symbol} (₹{ltp:.2f})

Technical signals:
{technical}

Fundamental signals:
{fundamental}

Give a concise trading view. Respond EXACTLY in this format (no extra text):

VERDICT: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASON:
- [reason 1]
- [reason 2]
- [reason 3]
ENTRY: [price or MARKET]
SL: [stop-loss price]
TARGET: [target price]

Be specific with prices based on the data provided. If data is insufficient, use HOLD."""


# ── Quick Scanner ─────────────────────────────────────────────


class QuickScanner:
    """
    Single-agent fast analysis.

    1. Gather technical + fundamental data (pure Python, ~0.5s)
    2. One LLM call with concise prompt (~2-4s)
    3. Parse response into structured QuickScanResult
    """

    def __init__(self, provider=None, registry=None) -> None:
        self._provider = provider
        self._registry = registry

    def _get_provider(self):
        if self._provider:
            return self._provider
        try:
            from agent.core import build_provider_from_env
            from agent.harness import ToolRegistry

            registry = self._registry or ToolRegistry()
            return build_provider_from_env(
                registry, system_prompt="You are a concise trading analyst."
            )
        except Exception as e:
            raise RuntimeError(f"No LLM provider available: {e}")

    def _get_registry(self):
        if self._registry:
            return self._registry
        try:
            from agent.harness import ToolRegistry

            return ToolRegistry()
        except Exception:
            return None

    def _gather_technical(self, symbol: str, exchange: str) -> dict:
        """Gather technical signals — pure Python, no LLM."""
        try:
            registry = self._get_registry()
            if registry:
                return (
                    registry.execute("technical_analyse", {"symbol": symbol, "exchange": exchange})
                    or {}
                )
        except Exception:
            pass
        return {}

    def _gather_fundamental(self, symbol: str) -> dict:
        """Gather fundamental signals — pure Python, no LLM."""
        try:
            registry = self._get_registry()
            if registry:
                return registry.execute("fundamental_data", {"symbol": symbol}) or {}
        except Exception:
            pass
        return {}

    def _format_technical(self, data: dict) -> str:
        """Format technical data as concise text for the prompt."""
        lines = []
        if data.get("rsi") is not None:
            rsi = data["rsi"]
            label = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
            lines.append(f"RSI: {rsi:.1f} ({label})")
        if data.get("macd_signal"):
            lines.append(f"MACD: {data['macd_signal'].lower()} signal")
        if data.get("ema20") and data.get("ema50"):
            trend = "above" if data["ema20"] > data["ema50"] else "below"
            lines.append(f"EMA: 20 {trend} 50 (short-term {'up' if trend == 'above' else 'down'})")
        if data.get("support"):
            lines.append(f"Support: ₹{data['support']:,.2f}")
        if data.get("resistance"):
            lines.append(f"Resistance: ₹{data['resistance']:,.2f}")
        if data.get("verdict"):
            lines.append(f"Technical verdict: {data['verdict']}")
        if data.get("score") is not None:
            lines.append(f"Score: {data['score']}/100")
        return "\n".join(lines) if lines else "No technical data available"

    def _format_fundamental(self, data: dict) -> str:
        """Format fundamental data as concise text for the prompt."""
        lines = []
        if data.get("pe_ratio") is not None:
            lines.append(f"PE: {data['pe_ratio']:.1f}x")
        if data.get("pb_ratio") is not None:
            lines.append(f"P/B: {data['pb_ratio']:.1f}x")
        if data.get("roe") is not None:
            lines.append(f"ROE: {data['roe']:.1f}%")
        if data.get("market_cap"):
            lines.append(f"Market cap: ₹{data['market_cap'] / 1e7:.0f} Cr")
        if data.get("sector"):
            lines.append(f"Sector: {data['sector']}")
        return "\n".join(lines) if lines else "No fundamental data available"

    def scan(self, symbol: str, exchange: str = "NSE", ltp: float = 0.0) -> QuickScanResult:
        """
        Run a quick single-agent scan.

        Args:
            symbol:   Stock symbol
            exchange: NSE (default) or BSE
            ltp:      Current price (fetched if 0.0)

        Returns:
            QuickScanResult with verdict, confidence, reasons, prices
        """
        t0 = time.time()
        sym = symbol.upper()

        # Fetch LTP if not provided
        if ltp <= 0:
            try:
                from market.quotes import get_ltp

                ltp = get_ltp(f"{exchange}:{sym}")
            except Exception:
                ltp = 0.0

        # Gather data (pure Python)
        tech_data = self._gather_technical(sym, exchange)
        fund_data = self._gather_fundamental(sym)

        tech_text = self._format_technical(tech_data)
        fund_text = self._format_fundamental(fund_data)

        prompt = _QUICK_PROMPT.format(
            symbol=sym,
            ltp=ltp,
            technical=tech_text,
            fundamental=fund_text,
        )

        # Single LLM call
        try:
            provider = self._get_provider()
            response = provider.chat(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            return QuickScanResult(
                symbol=sym,
                verdict="HOLD",
                confidence=0,
                reasons=[],
                entry=None,
                sl=None,
                target=None,
                ltp=ltp,
                elapsed_ms=elapsed,
                error=str(e),
            )

        # Parse response
        parsed = _parse_quick_response(response)
        elapsed = int((time.time() - t0) * 1000)

        return QuickScanResult(
            symbol=sym,
            verdict=parsed["verdict"],
            confidence=parsed["confidence"],
            reasons=parsed["reasons"],
            entry=parsed["entry"],
            sl=parsed["sl"],
            target=parsed["target"],
            ltp=ltp,
            elapsed_ms=elapsed,
        )
