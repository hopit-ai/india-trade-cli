"""
agent/persona_agent.py
──────────────────────
Run a named investor persona analysis on a stock symbol.

Flow (with LLM):
  1. Fetch pre-computed data: technicals + fundamentals + macro snapshot
  2. Build a compact data brief
  3. Call LLM with persona's system_prompt + data brief
  4. Parse response → PersonaSignal
  5. Return PersonaSignal

Flow (no LLM — deterministic fallback):
  Same data fetch, then score each dimension using simple rules,
  apply persona weights, map to verdict.

Public API:
  run_persona_analysis(persona_id, symbol, exchange, registry, llm_provider) -> PersonaSignal
  run_debate(symbol, exchange, registry, llm_provider) -> list[PersonaSignal]
  parse_persona_response(text, persona_id) -> PersonaSignal
"""

from __future__ import annotations

import re
from typing import Any

from agent.personas import get_persona, list_personas
from agent.schemas import PersonaSignal


# ── Response parser ───────────────────────────────────────────


def parse_persona_response(text: str, persona_id: str) -> PersonaSignal:
    """
    Parse an LLM response into a PersonaSignal.

    Handles:
      - Full structured responses
      - Partial responses (missing some fields)
      - Empty or error responses (returns HOLD with 30% confidence)

    Expected loose format in the response:
        VERDICT: BUY
        CONFIDENCE: 72
        RATIONALE:
        - Strong moat in telecom
        - ROE below threshold
        KEY_METRICS:
        ROE: 8% (need >15%)
        D/E: 0.4
    """
    if not text or not text.strip():
        return PersonaSignal(
            persona=persona_id,
            verdict="HOLD",
            confidence=30,
            rationale=["Insufficient data for analysis"],
            key_metrics={},
        )

    verdict = "HOLD"
    confidence = 50
    rationale: list[str] = []
    key_metrics: dict[str, str] = {}

    # ── Verdict ──────────────────────────────────────────────
    verdict_match = re.search(
        r"VERDICT\s*[:=]\s*(STRONG_BUY|STRONG_SELL|BUY|SELL|HOLD)",
        text,
        re.IGNORECASE,
    )
    if verdict_match:
        verdict_raw = verdict_match.group(1).upper().replace(" ", "_")
        # Normalise: "STRONG BUY" → "STRONG_BUY"
        valid = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}
        if verdict_raw in valid:
            verdict = verdict_raw

    # ── Confidence ────────────────────────────────────────────
    conf_match = re.search(r"CONFIDENCE\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if conf_match:
        try:
            confidence = max(0, min(100, int(conf_match.group(1))))
        except ValueError:
            pass

    # ── Rationale (bullet points) ─────────────────────────────
    rationale_section = re.search(
        r"RATIONALE\s*[:=]?\s*\n(.*?)(?=KEY_METRICS|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if rationale_section:
        lines = rationale_section.group(1).strip().splitlines()
        for line in lines:
            line = line.strip().lstrip("-•*").strip()
            if line:
                rationale.append(line)

    # Fall back: find any bullet points in the text
    if not rationale:
        bullets = re.findall(r"^[\s]*[-•*]\s+(.+)$", text, re.MULTILINE)
        rationale = [b.strip() for b in bullets if b.strip()][:6]

    # Guarantee at least one rationale item
    if not rationale:
        rationale = ["Analysis based on available data"]

    # ── Key metrics ───────────────────────────────────────────
    metrics_section = re.search(
        r"KEY_METRICS\s*[:=]?\s*\n(.*?)$",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if metrics_section:
        lines = metrics_section.group(1).strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # "ROE: 8%" or "ROE = 8%"
            kv = re.match(r"^([^:=]+?)\s*[:=]\s*(.+)$", line)
            if kv:
                key_metrics[kv.group(1).strip()] = kv.group(2).strip()

    return PersonaSignal(
        persona=persona_id,
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
        key_metrics=key_metrics,
    )


# ── Data fetcher ──────────────────────────────────────────────


def _fetch_data_brief(
    symbol: str,
    exchange: str,
    registry: Any,
) -> dict[str, Any]:
    """
    Fetch technical, fundamental, and macro data for the symbol.

    Returns a dict with all available data. Empty / default values used
    when registry is None or a tool raises an exception.
    """
    brief: dict[str, Any] = {
        "symbol": symbol,
        "exchange": exchange,
        "technicals": {},
        "fundamentals": {},
        "macro": {},
        "news": [],
        "fii_dii": {},
    }

    if registry is None:
        return brief

    def _safe_call(tool_name: str, **kwargs) -> Any:
        try:
            fn = registry.get_fn(tool_name)
            if fn is None:
                return None
            return fn(**kwargs)
        except Exception:
            return None

    # Technical snapshot
    tech = _safe_call("technical_analyse", symbol=symbol, exchange=exchange)
    if tech:
        brief["technicals"] = tech if isinstance(tech, dict) else vars(tech)

    # Fundamental snapshot
    fund = _safe_call("fundamental_analyse", symbol=symbol)
    if fund:
        brief["fundamentals"] = fund if isinstance(fund, dict) else vars(fund)

    # FII/DII data
    fii = _safe_call("get_fii_dii_data")
    if fii:
        brief["fii_dii"] = fii if isinstance(fii, dict) else vars(fii)

    # Market snapshot
    macro = _safe_call("get_market_snapshot")
    if macro:
        brief["macro"] = macro if isinstance(macro, dict) else vars(macro)

    # News
    news = _safe_call("get_stock_news", symbol=symbol)
    if news and isinstance(news, list):
        brief["news"] = news[:5]  # limit to 5 headlines

    return brief


def _build_prompt(symbol: str, exchange: str, brief: dict[str, Any]) -> str:
    """Build a compact data brief string for the LLM prompt."""
    lines = [
        "=== Stock Analysis Request ===",
        f"Symbol: {symbol} | Exchange: {exchange}",
        "",
    ]

    tech = brief.get("technicals", {})
    if tech:
        lines.append("--- Technical Data ---")
        for k, v in list(tech.items())[:10]:
            lines.append(f"  {k}: {v}")
        lines.append("")

    fund = brief.get("fundamentals", {})
    if fund:
        lines.append("--- Fundamentals ---")
        for k, v in list(fund.items())[:15]:
            lines.append(f"  {k}: {v}")
        lines.append("")

    macro = brief.get("macro", {})
    if macro:
        lines.append("--- Macro Data ---")
        for k, v in list(macro.items())[:8]:
            lines.append(f"  {k}: {v}")
        lines.append("")

    fii = brief.get("fii_dii", {})
    if fii:
        lines.append("--- FII/DII Flows ---")
        for k, v in list(fii.items())[:5]:
            lines.append(f"  {k}: {v}")
        lines.append("")

    news = brief.get("news", [])
    if news:
        lines.append("--- Recent News ---")
        for headline in news[:3]:
            lines.append(f"  • {headline}")
        lines.append("")

    lines += [
        "=== Required Output Format ===",
        "VERDICT: <STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL>",
        "CONFIDENCE: <0-100>",
        "RATIONALE:",
        "- <checklist item 1>",
        "- <checklist item 2>",
        "- <checklist item 3>",
        "KEY_METRICS:",
        "<metric name>: <value and context>",
        "",
        "Then provide 2-3 sentences of reasoning in your authentic voice.",
    ]

    return "\n".join(lines)


# ── Rule-based fallback scorer ────────────────────────────────


def _score_dimension(dimension: str, brief: dict[str, Any]) -> float:
    """
    Score a single dimension 0–100 using simple heuristics on available data.

    Returns 50 (neutral) when data is unavailable.
    """
    tech = brief.get("technicals", {})
    fund = brief.get("fundamentals", {})
    macro = brief.get("macro", {})
    fii = brief.get("fii_dii", {})

    if dimension == "fundamentals":
        score = 50.0
        roe = fund.get("roe") or fund.get("ROE")
        if roe is not None:
            try:
                roe = float(roe)
                score += 15 if roe > 15 else (-10 if roe < 8 else 5)
            except (TypeError, ValueError):
                pass

        de = fund.get("debt_equity") or fund.get("de") or fund.get("D/E")
        if de is not None:
            try:
                de = float(de)
                score += 10 if de < 0.5 else (-10 if de > 1.5 else 0)
            except (TypeError, ValueError):
                pass

        pe = fund.get("pe") or fund.get("PE")
        if pe is not None:
            try:
                pe = float(pe)
                score += 10 if pe < 15 else (-10 if pe > 40 else 0)
            except (TypeError, ValueError):
                pass

        fcf_yield = fund.get("fcf_yield") or fund.get("FCF_yield")
        if fcf_yield is not None:
            try:
                fcf_yield = float(fcf_yield)
                score += 10 if fcf_yield > 5 else (-5 if fcf_yield < 2 else 0)
            except (TypeError, ValueError):
                pass

        return max(0.0, min(100.0, score))

    elif dimension == "technicals":
        score = 50.0
        rsi = tech.get("rsi") or tech.get("RSI")
        if rsi is not None:
            try:
                rsi = float(rsi)
                if rsi < 30:
                    score += 20  # oversold → buy signal
                elif rsi > 70:
                    score -= 15  # overbought → cautious
                elif 40 <= rsi <= 60:
                    score += 5  # neutral zone
            except (TypeError, ValueError):
                pass

        trend = tech.get("trend") or tech.get("price_trend")
        if trend:
            trend_str = str(trend).upper()
            if "BULL" in trend_str or "UP" in trend_str:
                score += 10
            elif "BEAR" in trend_str or "DOWN" in trend_str:
                score -= 10

        return max(0.0, min(100.0, score))

    elif dimension == "macro":
        score = 50.0
        # FII flows
        fii_net = fii.get("net") or fii.get("fii_net") or fii.get("FII_net")
        if fii_net is not None:
            try:
                fii_net = float(fii_net)
                score += 15 if fii_net > 0 else (-10 if fii_net < 0 else 0)
            except (TypeError, ValueError):
                pass

        # Market regime
        vix = macro.get("india_vix") or macro.get("VIX") or macro.get("vix")
        if vix is not None:
            try:
                vix = float(vix)
                score += 10 if vix < 15 else (-15 if vix > 25 else 0)
            except (TypeError, ValueError):
                pass

        return max(0.0, min(100.0, score))

    elif dimension == "sentiment":
        score = 50.0
        # Use news count or FII direction as a proxy for sentiment
        news = brief.get("news", [])
        if news:
            # Simple: more news = more attention, slightly positive
            score += min(5, len(news))
        return max(0.0, min(100.0, score))

    elif dimension == "options":
        score = 50.0
        pcr = tech.get("pcr") or tech.get("put_call_ratio")
        if pcr is not None:
            try:
                pcr = float(pcr)
                # PCR > 1.5 → bullish contrarian signal; PCR < 0.5 → bearish contrarian
                if pcr > 1.5:
                    score += 15
                elif pcr < 0.5:
                    score -= 10
            except (TypeError, ValueError):
                pass
        return max(0.0, min(100.0, score))

    return 50.0


def _rule_based_signal(
    persona_id: str,
    brief: dict[str, Any],
) -> PersonaSignal:
    """
    Deterministic rule-based signal using persona weights × dimension scores.

    No LLM required.
    """
    from agent.personas import get_persona

    persona = get_persona(persona_id)

    weighted_sum = 0.0
    checklist_results: list[str] = []
    key_metrics: dict[str, str] = {}

    for dimension, weight in persona.weights.items():
        dim_score = _score_dimension(dimension, brief)
        weighted_sum += dim_score * weight

        # Produce a checklist entry for each dimension
        level = "strong" if dim_score >= 65 else ("weak" if dim_score <= 40 else "neutral")
        symbol_map = {"strong": "✓", "neutral": "~", "weak": "✗"}
        checklist_results.append(
            f"{symbol_map[level]} {dimension.title()} score: {dim_score:.0f}/100 ({level})"
        )
        key_metrics[dimension.title()] = f"{dim_score:.0f}/100"

    # Add persona-specific checklist items
    for item in persona.checklist[:3]:
        checklist_results.append(f"~ {item} (data insufficient for precise check)")

    # Map score to verdict
    score = weighted_sum
    if score >= 80:
        verdict = "STRONG_BUY"
    elif score >= 65:
        verdict = "BUY"
    elif score >= 40:
        verdict = "HOLD"
    elif score >= 25:
        verdict = "SELL"
    else:
        verdict = "STRONG_SELL"

    confidence = max(30, min(90, int(score)))

    return PersonaSignal(
        persona=persona_id,
        verdict=verdict,
        confidence=confidence,
        rationale=checklist_results[:6],
        key_metrics=key_metrics,
    )


# ── LLM caller ────────────────────────────────────────────────


def _call_llm(
    system_prompt: str,
    user_message: str,
    llm_provider: Any,
) -> str:
    """Call the LLM provider with system + user message. Returns response text."""
    try:
        # Try the standard call interface used by the platform
        if hasattr(llm_provider, "call"):
            return llm_provider.call(
                system=system_prompt,
                message=user_message,
            )
        # Fallback: direct chat method
        if hasattr(llm_provider, "chat"):
            return llm_provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
        # Generic: try __call__
        if callable(llm_provider):
            return str(llm_provider(system_prompt, user_message))
    except Exception as exc:
        # Any LLM failure → return empty (caller will use rule-based fallback)
        return f"LLM call failed: {exc}"
    return ""


# ── Public API ────────────────────────────────────────────────


def run_persona_analysis(
    persona_id: str,
    symbol: str,
    exchange: str = "NSE",
    registry: Any = None,
    llm_provider: Any = None,
) -> PersonaSignal:
    """
    Run a single persona analysis on a symbol.

    Parameters
    ----------
    persona_id:    One of 'buffett', 'jhunjhunwala', 'lynch', 'soros', 'munger'
    symbol:        Stock ticker, e.g. 'RELIANCE'
    exchange:      'NSE' or 'BSE'
    registry:      ToolRegistry for live data; if None, analysis uses empty data
    llm_provider:  LLM provider instance; if None, uses deterministic fallback

    Returns
    -------
    PersonaSignal
    """
    # Validate persona (raises ValueError for unknown ids)
    persona = get_persona(persona_id)

    # 1. Fetch data
    brief = _fetch_data_brief(symbol, exchange, registry)

    # 2. LLM path
    if llm_provider is not None:
        prompt = _build_prompt(symbol, exchange, brief)
        response_text = _call_llm(
            system_prompt=persona.system_prompt,
            user_message=prompt,
            llm_provider=llm_provider,
        )
        if response_text and "LLM call failed" not in response_text:
            return parse_persona_response(response_text, persona_id)
        # Fall through to rule-based if LLM failed

    # 3. Rule-based fallback
    return _rule_based_signal(persona_id, brief)


def run_debate(
    symbol: str,
    exchange: str = "NSE",
    registry: Any = None,
    llm_provider: Any = None,
) -> list[PersonaSignal]:
    """
    Run all 5 personas and return their signals.

    Parameters
    ----------
    symbol:       Stock ticker
    exchange:     'NSE' or 'BSE'
    registry:     ToolRegistry for live data
    llm_provider: LLM provider; if None uses deterministic fallback for all

    Returns
    -------
    list[PersonaSignal] — one per persona, in stable order
    """
    personas = list_personas()
    signals: list[PersonaSignal] = []

    for persona in personas:
        signal = run_persona_analysis(
            persona_id=persona.id,
            symbol=symbol,
            exchange=exchange,
            registry=registry,
            llm_provider=llm_provider,
        )
        signals.append(signal)

    return signals
