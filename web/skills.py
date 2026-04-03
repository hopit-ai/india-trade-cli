"""
web/skills.py
─────────────
OpenClaw skill endpoints for india-trade-cli.

Each POST endpoint is a "skill" that any OpenClaw agent can call via HTTP.
Returns structured JSON from the existing market/analysis/engine modules.

Run the server (from repo root):
    uvicorn web.api:app --host 0.0.0.0 --port 8765

Skill endpoints:
    POST /skills/quote          → Live price, OHLCV, change%
    POST /skills/options_chain  → Full options chain
    POST /skills/flows          → FII/DII institutional flow data + signals
    POST /skills/earnings       → Earnings calendar
    POST /skills/macro          → Macro snapshot (USD/INR, crude, gold)
    POST /skills/deals          → Bulk/block deals
    POST /skills/backtest       → Backtest a trading strategy
    POST /skills/pairs          → Pair trading analysis
    POST /skills/analyze        → 7-analyst multi-agent analysis + debate + trade plans
    POST /skills/deep_analyze   → 11-LLM deep analysis
    POST /skills/morning_brief  → Daily market brief (structured JSON, no AI narrative)
    POST /skills/chat           → Multi-turn AI chat with trading agent (session-aware)
    POST /skills/chat/reset     → Clear chat history for a session
    POST /skills/alerts/add     → Create a price, technical, or conditional alert
    POST /skills/alerts/list    → List all active (untriggered) alerts
    POST /skills/alerts/remove  → Remove an alert by ID
    POST /skills/alerts/check   → Check alerts now and return any that just triggered

Manifest:
    GET  /.well-known/openclaw.json → OpenClaw skill discovery manifest
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.tools import _serialise

router = APIRouter(prefix="/skills", tags=["OpenClaw Skills"])

# ── Chat session store ────────────────────────────────────────
# Keyed by session_id → TradingAgent instance.
# In-memory only; sessions are lost on server restart.
_chat_sessions: dict[str, object] = {}


# ── Request models ────────────────────────────────────────────


class SymbolRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "rsi"
    period: str = "1y"
    exchange: str = "NSE"


class PairsRequest(BaseModel):
    stock_a: str
    stock_b: str


class EarningsRequest(BaseModel):
    symbols: Optional[list[str]] = None


class MacroRequest(BaseModel):
    symbol: Optional[str] = None


class DealsRequest(BaseModel):
    symbol: Optional[str] = None
    days: int = 5


class AnalyzeRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"  # use different IDs for separate conversations


class AlertAddRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    # Price alert fields
    condition: Optional[str] = None  # ABOVE | BELOW | CROSSES
    threshold: Optional[float] = None
    # Technical alert fields
    indicator: Optional[str] = None  # RSI | MACD | ADX | ATR | SCORE
    # Conditional alert: list of conditions joined by AND
    conditions: Optional[list[dict]] = None
    # Webhook: POST here when alert fires
    webhook_url: Optional[str] = None


class AlertRemoveRequest(BaseModel):
    alert_id: str


# ── Helper ────────────────────────────────────────────────────


def _ok(data) -> dict:
    return {"status": "ok", "data": _serialise(data)}


def _err(msg: str, code: int = 500) -> HTTPException:
    return HTTPException(status_code=code, detail={"status": "error", "message": msg})


# ── Skills ────────────────────────────────────────────────────


@router.post("/quote")
async def skill_quote(req: SymbolRequest):
    """Live price, OHLCV, and change% for a symbol."""
    try:
        from market.quotes import get_quote

        instrument = req.symbol if ":" in req.symbol else f"{req.exchange}:{req.symbol}"
        quotes = get_quote([instrument])
        if not quotes:
            raise _err(f"No quote found for {req.symbol}", 404)
        return _ok(list(quotes.values())[0])
    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


@router.post("/options_chain")
async def skill_options_chain(req: SymbolRequest):
    """Full options chain for a symbol (all strikes and expiries)."""
    try:
        from market.options import get_options_chain

        chain = get_options_chain(req.symbol.upper(), None)
        return _ok(chain)
    except Exception as e:
        raise _err(str(e))


@router.post("/flows")
async def skill_flows():
    """FII/DII institutional flow data with buy/sell signals."""
    try:
        from market.flow_intel import get_flow_analysis

        report = get_flow_analysis()
        return _ok(report)
    except Exception as e:
        raise _err(str(e))


@router.post("/earnings")
async def skill_earnings(req: EarningsRequest):
    """Upcoming earnings calendar, optionally filtered by symbol list."""
    try:
        from market.earnings import get_earnings_calendar

        events = get_earnings_calendar()
        if req.symbols:
            syms = {s.upper() for s in req.symbols}
            events = [e for e in events if any(s in str(e).upper() for s in syms)]
        return _ok(events)
    except Exception as e:
        raise _err(str(e))


@router.post("/macro")
async def skill_macro(req: MacroRequest):
    """Macro snapshot: USD/INR, crude oil, gold, US 10Y yield."""
    try:
        from market.macro import get_macro_snapshot

        snap = get_macro_snapshot()
        return _ok(snap)
    except Exception as e:
        raise _err(str(e))


@router.post("/deals")
async def skill_deals(req: DealsRequest):
    """Bulk and block deals from NSE, optionally filtered by symbol."""
    try:
        from market.bulk_deals import get_bulk_deals

        deals = get_bulk_deals(days=req.days, symbol=req.symbol)
        return _ok(deals)
    except Exception as e:
        raise _err(str(e))


@router.post("/backtest")
async def skill_backtest(req: BacktestRequest):
    """
    Backtest a trading strategy on historical data.
    Strategies: rsi, ma, ema, macd, bb (Bollinger Bands)
    """
    try:
        from engine.backtest import run_backtest

        result = run_backtest(req.symbol.upper(), req.strategy, period=req.period)
        return _ok(result)
    except Exception as e:
        raise _err(str(e))


@router.post("/pairs")
async def skill_pairs(req: PairsRequest):
    """Pair trading analysis: correlation, spread, mean reversion signals."""
    try:
        from engine.pairs import analyze_pair

        result = analyze_pair(req.stock_a.upper(), req.stock_b.upper())
        return _ok(result)
    except Exception as e:
        raise _err(str(e))


@router.post("/analyze")
async def skill_analyze(req: AnalyzeRequest):
    """
    7-analyst multi-agent analysis with bull/bear debate and 3 trade plans.

    Pipeline:
      Phase 1 — 7 analysts (Technical, Fundamental, Options, News/Macro,
                 Sentiment, Sector Rotation, Risk) run in parallel
      Phase 2 — Bull vs Bear researcher debate (2 rounds)
      Phase 3 — Fund Manager synthesizes final verdict + recommendation

    Returns the full text report plus structured trade plans.
    NOTE: Involves multiple LLM calls. Expect 30–90 seconds.
    """
    try:
        from agent.tools import build_registry
        from agent.core import get_provider
        from agent.multi_agent import MultiAgentAnalyzer

        registry = build_registry()
        provider = get_provider(registry=registry)
        analyzer = MultiAgentAnalyzer(registry, provider, verbose=False)
        report = analyzer.analyze(req.symbol.upper(), req.exchange.upper())

        return {
            "status": "ok",
            "data": {
                "symbol": req.symbol.upper(),
                "exchange": req.exchange.upper(),
                "report": report,
                "trade_plans": _serialise(getattr(analyzer, "last_trade_plans", {})),
            },
        }
    except Exception as e:
        raise _err(str(e))


@router.post("/deep_analyze")
async def skill_deep_analyze(req: AnalyzeRequest):
    """
    11-LLM deep analysis — every analyst uses AI (not just Python rules).
    More thorough than /analyze but takes several minutes.
    NOTE: 11+ LLM calls. Expect 3–8 minutes.
    """
    try:
        from agent.tools import build_registry
        from agent.core import get_provider
        from agent.deep_agent import DeepAnalyzer

        registry = build_registry()
        provider = get_provider(registry=registry)
        analyzer = DeepAnalyzer(registry, provider, verbose=False)
        report = analyzer.analyze(req.symbol.upper(), req.exchange.upper())

        return {
            "status": "ok",
            "data": {
                "symbol": req.symbol.upper(),
                "exchange": req.exchange.upper(),
                "report": report,
            },
        }
    except Exception as e:
        raise _err(str(e))


@router.post("/morning_brief")
async def skill_morning_brief():
    """
    Daily market brief: NIFTY snapshot, FII/DII flows, top news, breadth, events.
    Returns structured JSON — no AI narrative layer (fast, no LLM calls).
    """
    try:
        from market.indices import get_market_snapshot
        from market.flow_intel import get_flow_analysis
        from market.news import get_market_news
        from market.sentiment import get_market_breadth
        from market.events import get_upcoming_events

        snapshot = get_market_snapshot()
        flows = get_flow_analysis()
        news = get_market_news(n=5)
        breadth = get_market_breadth()
        events = get_upcoming_events(days=7)

        return {
            "status": "ok",
            "data": {
                "market_snapshot": _serialise(snapshot),
                "institutional_flows": _serialise(flows),
                "top_news": _serialise(news),
                "market_breadth": _serialise(breadth),
                "upcoming_events": _serialise(events),
            },
        }
    except Exception as e:
        raise _err(str(e))


@router.post("/chat")
async def skill_chat(req: ChatRequest):
    """
    Multi-turn AI chat with the trading agent.

    The agent has access to all market tools (quotes, technicals, fundamentals,
    options, flows, news, portfolio) and can call them during the conversation.

    Sessions are keyed by session_id — use the same ID across calls to keep
    conversation context. Use a new ID (or call /chat/reset) to start fresh.

    Example:
        {"message": "Analyse RELIANCE for me", "session_id": "user-123"}
        {"message": "What does the options chain say?", "session_id": "user-123"}
    """
    try:
        from agent.core import TradingAgent

        if req.session_id not in _chat_sessions:
            _chat_sessions[req.session_id] = TradingAgent(stream=False)

        agent = _chat_sessions[req.session_id]
        response = agent.chat(req.message)

        return {
            "status": "ok",
            "data": {
                "session_id": req.session_id,
                "response": response,
                "history_length": len(agent._history),
            },
        }
    except Exception as e:
        raise _err(str(e))


class ChatResetRequest(BaseModel):
    session_id: str = "default"


@router.post("/chat/reset")
async def skill_chat_reset(req: ChatResetRequest):
    """Clear conversation history for a session (start fresh)."""
    _chat_sessions.pop(req.session_id, None)
    return {"status": "ok", "data": {"session_id": req.session_id, "cleared": True}}


# ── Alert skills ──────────────────────────────────────────────


@router.post("/alerts/add")
async def skill_alerts_add(req: AlertAddRequest):
    """
    Create a price, technical, or conditional alert.

    Alert types (determined by which fields you provide):

    Price alert — fires when LTP crosses a price level:
        { "symbol": "RELIANCE", "condition": "ABOVE", "threshold": 2800 }

    Technical alert — fires when an indicator crosses a level:
        { "symbol": "INFY", "indicator": "RSI", "condition": "ABOVE", "threshold": 70 }
        Supported indicators: RSI, MACD, ADX, ATR, SCORE

    Conditional alert (AND logic) — fires when ALL conditions are met:
        { "symbol": "RELIANCE", "conditions": [
            {"condition_type": "PRICE",     "condition": "ABOVE", "threshold": 2800},
            {"condition_type": "TECHNICAL", "condition": "ABOVE", "threshold": 60, "indicator": "RSI"}
        ]}

    Webhook — optional callback when the alert triggers:
        Add "webhook_url": "https://your-agent/callback" to any alert type.
        When triggered, the server POSTs:
        { "event": "alert_triggered", "alert_id": "...", "symbol": "...",
          "description": "...", "triggered_at": "...", "ltp": ... }

    Alerts persist across server restarts (saved to ~/.trading_platform/alerts.json).
    """
    try:
        from engine.alerts import alert_manager

        sym = req.symbol.upper()
        exch = req.exchange.upper()

        # Conditional alert
        if req.conditions:
            alert = alert_manager.add_conditional_alert(
                symbol=sym,
                conditions=req.conditions,
                exchange=exch,
                webhook_url=req.webhook_url,
            )

        # Technical alert
        elif req.indicator:
            if req.condition is None or req.threshold is None:
                raise _err("Technical alerts require condition and threshold", 400)
            alert = alert_manager.add_technical_alert(
                symbol=sym,
                indicator=req.indicator,
                condition=req.condition,
                threshold=req.threshold,
                exchange=exch,
                webhook_url=req.webhook_url,
            )

        # Price alert
        elif req.condition and req.threshold is not None:
            alert = alert_manager.add_price_alert(
                symbol=sym,
                condition=req.condition,
                threshold=req.threshold,
                exchange=exch,
                webhook_url=req.webhook_url,
            )

        else:
            raise _err(
                "Provide condition+threshold (price), indicator+condition+threshold "
                "(technical), or conditions list (conditional).",
                400,
            )

        # Start polling if not already running
        alert_manager.start_polling(interval=60)

        return {"status": "ok", "data": _serialise(alert)}

    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


@router.post("/alerts/list")
async def skill_alerts_list():
    """List all active (not yet triggered) alerts."""
    try:
        from engine.alerts import alert_manager

        return {"status": "ok", "data": alert_manager.list_alerts()}
    except Exception as e:
        raise _err(str(e))


@router.post("/alerts/remove")
async def skill_alerts_remove(req: AlertRemoveRequest):
    """Remove an alert by its ID."""
    try:
        from engine.alerts import alert_manager

        removed = alert_manager.remove_alert(req.alert_id)
        if not removed:
            raise _err(f"Alert {req.alert_id} not found", 404)
        return {"status": "ok", "data": {"alert_id": req.alert_id, "removed": True}}
    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


@router.post("/alerts/check")
async def skill_alerts_check():
    """
    Manually evaluate all active alerts right now.
    Returns any alerts that just triggered during this check.
    Useful for polling-based agents that don't use webhooks.
    """
    try:
        from engine.alerts import alert_manager

        triggered = alert_manager.check_alerts()
        return {
            "status": "ok",
            "data": {
                "triggered": _serialise(triggered),
                "active_remaining": alert_manager.active_count(),
            },
        }
    except Exception as e:
        raise _err(str(e))
