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
    GET  /skills/profile        → Broker account profile (name, client_id, email)
    GET  /skills/funds          → Available cash, used margin, total balance
    GET  /skills/orders         → Today's orders list
    POST /skills/oi_profile     → OI profile by strike (PCR, max pain, support/resistance)
    POST /skills/patterns       → Active India-specific market patterns
    POST /skills/greeks         → Portfolio Greeks (delta, theta, vega, gamma)
    POST /skills/scan           → Options market scan (high IV, unusual OI, put writing)
    POST /skills/alerts/add     → Create a price, technical, or conditional alert
    POST /skills/alerts/list    → List all active (untriggered) alerts
    POST /skills/alerts/remove  → Remove an alert by ID
    POST /skills/alerts/check   → Check alerts now and return any that just triggered

Manifest:
    GET  /.well-known/openclaw.json → OpenClaw skill discovery manifest
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


@router.get("/analyze/ping")
async def skill_analyze_ping():
    """Quick SSE test — emits 3 events then closes."""

    async def _gen():
        for i in range(3):
            yield f"data: {json.dumps({'type': 'ping', 'i': i})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/analyze/stream")
async def skill_analyze_stream(symbol: str, exchange: str = "NSE"):
    """
    SSE stream of multi-agent analysis progress.

    Events (text/event-stream):
      {"type":"analyst","name":"...","verdict":"...","confidence":70,"score":0.6,"error":null}
      {"type":"phase","phase":"debate"}
      {"type":"phase","phase":"synthesis"}
      {"type":"done","symbol":"...","exchange":"...","report":"...","trade_plans":{...}}
      {"type":"error","message":"..."}
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _cb(event: dict):
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    def _run():
        """Runs entirely in a background thread — no event loop blocking."""
        try:
            import os as _os

            # Suppress interactive stdin prompts: if provider setup needs stdin, fail fast.
            _os.environ.setdefault("_CLI_BATCH_MODE", "1")

            from agent.tools import build_registry
            from agent.core import get_provider
            from agent.multi_agent import MultiAgentAnalyzer as _MAA

            registry = build_registry()
            provider = get_provider(registry=registry)
            analyzer = _MAA(registry, provider, verbose=False, progress_callback=_cb)
            report = analyzer.analyze(symbol.upper(), exchange.upper())
            _cb(
                {
                    "type": "done",
                    "symbol": symbol.upper(),
                    "exchange": exchange.upper(),
                    "report": report,
                    "trade_plans": _serialise(getattr(analyzer, "last_trade_plans", {})),
                }
            )
        except Exception as exc:
            _cb({"type": "error", "message": str(exc)})
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # sentinel

    async def _generator():
        # Immediately confirm the stream is open (before any LLM work begins)
        yield f"data: {json.dumps({'type': 'started', 'symbol': symbol.upper(), 'exchange': exchange.upper()})}\n\n"
        # Fire off analysis in a background thread — does NOT block the event loop
        asyncio.ensure_future(loop.run_in_executor(None, _run))
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


@router.post("/holdings")
async def skill_holdings():
    """Return current broker holdings as structured JSON."""
    try:
        from brokers.session import get_broker

        try:
            broker = get_broker()
        except RuntimeError:
            return {"status": "ok", "data": {"holdings": [], "demo": True}}
        holdings = broker.get_holdings()
        return {"status": "ok", "data": {"holdings": _serialise(holdings)}}
    except Exception as e:
        raise _err(str(e))


@router.post("/positions")
async def skill_positions():
    """Return current broker positions as structured JSON."""
    try:
        from brokers.session import get_broker

        try:
            broker = get_broker()
        except RuntimeError:
            return {"status": "ok", "data": {"holdings": [], "demo": True}}
        positions = broker.get_positions()
        return {"status": "ok", "data": {"holdings": _serialise(positions)}}
    except Exception as e:
        raise _err(str(e))


# ── Broker account skills ─────────────────────────────────────


_DEMO_PROFILE = {
    "name": "Demo User",
    "user_id": "DEMO",
    "email": "",
    "broker": "demo",
    "demo": True,
    "note": "No broker connected — connect one via the Broker panel.",
}
_DEMO_FUNDS = {
    "available_cash": 0.0,
    "used_margin": 0.0,
    "total_balance": 0.0,
    "demo": True,
    "note": "No broker connected.",
}


@router.post("/profile")
async def skill_profile():
    """Return the connected broker's user profile (name, client_id, email, broker)."""
    try:
        from brokers.session import get_broker

        try:
            broker = get_broker()
        except RuntimeError:
            return {"status": "ok", "data": _DEMO_PROFILE}
        return {"status": "ok", "data": _serialise(broker.get_profile())}
    except Exception as e:
        raise _err(str(e))


@router.post("/funds")
async def skill_funds():
    """Return available cash, used margin, and total balance from the connected broker."""
    try:
        from brokers.session import get_broker

        try:
            broker = get_broker()
        except RuntimeError:
            return {"status": "ok", "data": _DEMO_FUNDS}
        return {"status": "ok", "data": _serialise(broker.get_funds())}
    except Exception as e:
        raise _err(str(e))


@router.post("/orders")
async def skill_orders():
    """Return today's orders from the connected broker."""
    try:
        from brokers.session import get_broker

        try:
            broker = get_broker()
        except RuntimeError:
            return {
                "status": "ok",
                "data": {"orders": [], "demo": True, "note": "No broker connected."},
            }
        return {"status": "ok", "data": {"orders": _serialise(broker.get_orders())}}
    except Exception as e:
        raise _err(str(e))


# ── Market data skills ────────────────────────────────────────


class OIProfileRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


@router.post("/oi_profile")
async def skill_oi_profile(req: OIProfileRequest):
    """
    OI profile for an underlying: per-strike call/put OI, PCR, max pain,
    resistance (max call OI strike) and support (max put OI strike).
    """
    try:
        from market.oi_profile import get_oi_profile

        data = get_oi_profile(req.symbol.upper())
        if "error" in data:
            raise _err(data["error"], 502)
        return _ok(data)
    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


class PatternsRequest(BaseModel):
    symbol: Optional[str] = None  # reserved for future per-symbol filtering


@router.post("/patterns")
async def skill_patterns(req: PatternsRequest):
    """
    Active India-specific market patterns (seasonal, calendar, event-driven).
    Each pattern includes name, impact (BULLISH/BEARISH/VOLATILE/NEUTRAL),
    confidence %, description, and suggested action.
    """
    try:
        from engine.patterns import get_active_patterns

        patterns = get_active_patterns()
        return _ok([_serialise(p) for p in patterns])
    except Exception as e:
        raise _err(str(e))


class GreeksRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


@router.post("/greeks")
async def skill_greeks(req: GreeksRequest):
    """
    Portfolio Greeks aggregated from all open options positions
    (net delta, theta, vega, gamma) plus per-position breakdown.

    Note: Greeks are computed from the live positions of the connected broker.
    Returns demo zeros when no broker is connected.
    """
    try:
        from brokers.session import get_broker

        try:
            get_broker()  # just validate connection; greeks uses positions internally
        except RuntimeError:
            return {
                "status": "ok",
                "data": {
                    "net": {"delta": 0.0, "theta": 0.0, "vega": 0.0, "gamma": 0.0},
                    "positions": [],
                    "warnings": [],
                    "demo": True,
                },
            }
        from engine.portfolio import get_position_greeks
        from engine.greeks_manager import build_dashboard

        pg = get_position_greeks()
        dash = build_dashboard(pg.net_delta, pg.net_theta, pg.net_vega, pg.net_gamma)
        return {
            "status": "ok",
            "data": {
                "net_delta": pg.net_delta,
                "net_theta": pg.net_theta,
                "net_vega": pg.net_vega,
                "net_gamma": pg.net_gamma,
                "positions_with_greeks": _serialise(pg.positions_with_greeks),
                "by_underlying": _serialise(pg.by_underlying),
                "warnings": _serialise(dash.warnings),
            },
        }
    except Exception as e:
        raise _err(str(e))


class ScanRequest(BaseModel):
    scan_type: str = "options"  # "options" is currently the supported type
    filters: dict = {}  # reserved for future filter expressions


@router.post("/scan")
async def skill_scan(req: ScanRequest):
    """
    Options market scan across the F&O universe.

    Returns:
      high_iv      — stocks with IV rank > 60
      unusual_oi   — strikes with OI change > 100%
      high_put_writing — stocks with PCR > 1.0
      summary      — plain-text summary line

    Pass filters.symbols (list[str]) to narrow the scan to specific tickers.
    Pass filters.quick = true for a faster scan over a smaller universe.
    """
    try:
        from market.options_scanner import scan_options

        symbols = req.filters.get("symbols") or None
        if isinstance(symbols, list):
            symbols = [s.upper() for s in symbols]
        quick = bool(req.filters.get("quick", False))

        results = scan_options(symbols=symbols, quick=quick)
        return _ok(results)
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


# ── IV Smile ──────────────────────────────────────────────────


class IVSmileRequest(BaseModel):
    symbol: str
    expiry: Optional[str] = None


@router.post("/iv_smile")
async def skill_iv_smile(req: IVSmileRequest):
    """IV smile across strikes for a given expiry."""
    try:
        from analysis.volatility_surface import compute_iv_smile

        df = compute_iv_smile(req.symbol.upper(), req.expiry)
        if df is None:
            return {
                "status": "ok",
                "data": {"rows": [], "symbol": req.symbol, "error": "No data available"},
            }
        rows = df.to_dict(orient="records")
        return {
            "status": "ok",
            "data": {"rows": rows, "symbol": req.symbol.upper(), "expiry": req.expiry},
        }
    except Exception as e:
        raise _err(str(e))


# ── GEX ───────────────────────────────────────────────────────


class GEXRequest(BaseModel):
    symbol: str
    expiry: Optional[str] = None


@router.post("/gex")
async def skill_gex(req: GEXRequest):
    """Gamma Exposure analysis for an underlying."""
    try:
        from analysis.gex import get_gex_analysis

        result = get_gex_analysis(req.symbol.upper(), req.expiry)
        return {"status": "ok", "data": result}
    except Exception as e:
        raise _err(str(e))


# ── Delta Hedge ───────────────────────────────────────────────


@router.post("/delta_hedge")
async def skill_delta_hedge():
    """Delta hedging suggestions based on current portfolio."""
    try:
        from brokers.session import get_broker

        try:
            get_broker()
        except RuntimeError:
            return {
                "status": "ok",
                "data": {
                    "demo": True,
                    "message": "Connect a broker to compute delta hedge",
                    "current_delta": 0.0,
                    "target_delta": 0.0,
                    "gap": 0.0,
                    "suggestions": [],
                },
            }
        from engine.portfolio import get_position_greeks
        from engine.greeks_manager import compute_delta_hedge

        pg = get_position_greeks()
        hedge = compute_delta_hedge(
            net_delta=pg.net_delta,
            target_delta=0.0,
        )
        return {"status": "ok", "data": _serialise(hedge)}
    except Exception as e:
        raise _err(str(e))


# ── Risk Report ───────────────────────────────────────────────


@router.post("/risk_report")
async def skill_risk_report():
    """Portfolio VaR, volatility, and concentration risk metrics."""
    try:
        from brokers.session import get_broker

        try:
            get_broker()
        except RuntimeError:
            return {
                "status": "ok",
                "data": {"demo": True, "message": "Connect a broker to see risk metrics"},
            }
        from engine.risk_metrics import compute_portfolio_risk

        report = compute_portfolio_risk()
        return {"status": "ok", "data": _serialise(report)}
    except Exception as e:
        raise _err(str(e))


# ── Walk Forward ──────────────────────────────────────────────


class WalkForwardRequest(BaseModel):
    symbol: str
    strategy: str = "rsi"
    window_months: int = 6
    total_period: str = "3y"


@router.post("/walkforward")
async def skill_walkforward(req: WalkForwardRequest):
    """Walk-forward backtest across rolling windows to test strategy consistency."""
    try:
        from engine.backtest import walk_forward_test

        result = walk_forward_test(
            symbol=req.symbol.upper(),
            strategy_name=req.strategy,
            total_period=req.total_period,
            window_months=req.window_months,
        )
        return {"status": "ok", "data": _serialise(result)}
    except Exception as e:
        raise _err(str(e))


# ── What-If ───────────────────────────────────────────────────


class WhatIfRequest(BaseModel):
    scenario: str = "market"  # "market", "stock", or "custom"
    symbol: Optional[str] = None
    nifty_change: Optional[float] = None  # % change (e.g. -5.0)
    stock_change: Optional[float] = None  # % change for symbol
    custom_moves: Optional[dict] = None  # {SYMBOL: change_pct}


@router.post("/whatif")
async def skill_whatif(req: WhatIfRequest):
    """What-if scenario analysis on your portfolio."""
    try:
        from brokers.session import get_broker

        try:
            get_broker()
        except RuntimeError:
            return {
                "status": "ok",
                "data": {
                    "demo": True,
                    "message": "Connect a broker to run what-if scenarios",
                },
            }
        from engine.simulator import Simulator

        sim = Simulator()
        if req.scenario == "market" and req.nifty_change is not None:
            result = sim.scenario_market_move(req.nifty_change)
        elif req.scenario == "stock" and req.symbol and req.stock_change is not None:
            result = sim.scenario_stock_move(req.symbol.upper(), req.stock_change)
        elif req.scenario == "custom" and req.custom_moves:
            result = sim.scenario_custom(req.custom_moves)
        else:
            # Run three standard scenarios: -5%, flat, +5%
            results = [
                sim.scenario_market_move(-5.0),
                sim.scenario_market_move(0.0),
                sim.scenario_market_move(5.0),
            ]
            return {"status": "ok", "data": {"scenarios": _serialise(results), "multi": True}}
        return {"status": "ok", "data": _serialise(result)}
    except Exception as e:
        raise _err(str(e))


# ── Strategy ──────────────────────────────────────────────────


class StrategyRequest(BaseModel):
    symbol: str
    view: str  # BULLISH / BEARISH / NEUTRAL
    dte: int = 30
    capital: Optional[float] = None


@router.post("/strategy")
async def skill_strategy(req: StrategyRequest):
    """Recommend ranked options strategies for a symbol and market view."""
    try:
        from market.quotes import get_ltp
        from engine.strategy import recommend

        spot = get_ltp(f"NSE:{req.symbol.upper()}")
        if spot <= 0:
            raise _err(f"Could not get spot price for {req.symbol}")
        report = recommend(
            symbol=req.symbol.upper(),
            view=req.view.upper(),
            spot=spot,
            dte=req.dte,
            capital=req.capital,
        )
        return {"status": "ok", "data": _serialise(report)}
    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


# ── Drift ─────────────────────────────────────────────────────


@router.post("/drift")
async def skill_drift():
    """Detect model/analyst accuracy drift over time from trade memory."""
    try:
        from engine.drift import detect_drift

        report = detect_drift()
        return {"status": "ok", "data": _serialise(report)}
    except Exception as e:
        raise _err(str(e))


# ── Memory ────────────────────────────────────────────────────


class MemoryQueryRequest(BaseModel):
    symbol: Optional[str] = None
    verdict: Optional[str] = None
    limit: int = 20
    days_back: Optional[int] = None


@router.post("/memory")
async def skill_memory():
    """Trade memory stats and recent analyses."""
    try:
        from engine.memory import trade_memory

        stats = trade_memory.get_stats()
        records = trade_memory.query(limit=20)
        return {"status": "ok", "data": {"stats": stats, "records": _serialise(records)}}
    except Exception as e:
        raise _err(str(e))


@router.post("/memory/query")
async def skill_memory_query(req: MemoryQueryRequest):
    """Query trade memory with filters."""
    try:
        from engine.memory import trade_memory

        records = trade_memory.query(
            symbol=req.symbol.upper() if req.symbol else None,
            verdict=req.verdict,
            limit=req.limit,
            days_back=req.days_back,
        )
        return {"status": "ok", "data": {"records": _serialise(records)}}
    except Exception as e:
        raise _err(str(e))


# ── Audit ─────────────────────────────────────────────────────


class AuditRequest(BaseModel):
    trade_id: str


@router.post("/audit")
async def skill_audit(req: AuditRequest):
    """Post-mortem audit of a specific trade from memory."""
    try:
        from engine.audit import audit_trade

        report = audit_trade(req.trade_id)
        return {"status": "ok", "data": _serialise(report)}
    except Exception as e:
        raise _err(str(e))


# ── Telegram ──────────────────────────────────────────────────


@router.get("/telegram/status")
async def skill_telegram_status():
    """Get Telegram bot connection status."""
    try:
        import os

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        configured = bool(token)
        running = False
        try:
            from bot.telegram_bot import _bot_running

            running = _bot_running
        except Exception:
            pass
        return {
            "status": "ok",
            "data": {
                "configured": configured,
                "running": running,
                "token_hint": f"...{token[-6:]}" if token else None,
            },
        }
    except Exception as e:
        raise _err(str(e))


# ── Provider ──────────────────────────────────────────────────


@router.post("/provider")
async def skill_provider():
    """Get current AI provider information."""
    try:
        import os

        provider = os.environ.get("AI_PROVIDER", "anthropic")
        model = os.environ.get("AI_MODEL", "")
        available = []
        if os.environ.get("ANTHROPIC_API_KEY"):
            available.append("anthropic")
        if os.environ.get("OPENAI_API_KEY"):
            available.append("openai")
        if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
            available.append("gemini")
        available.append("ollama")  # always available if installed
        return {
            "status": "ok",
            "data": {"current": provider, "model": model, "available": available},
        }
    except Exception as e:
        raise _err(str(e))


class ProviderSwitchRequest(BaseModel):
    provider: str
    model: Optional[str] = None


@router.post("/provider/switch")
async def skill_provider_switch(req: ProviderSwitchRequest):
    """Switch the active AI provider (takes effect for next request)."""
    try:
        import os

        valid = {
            "anthropic",
            "openai",
            "gemini",
            "ollama",
            "claude_subscription",
            "openai_subscription",
        }
        if req.provider not in valid:
            raise _err(f"Unknown provider '{req.provider}'. Valid: {', '.join(sorted(valid))}", 400)
        os.environ["AI_PROVIDER"] = req.provider
        if req.model:
            os.environ["AI_MODEL"] = req.model
        return {
            "status": "ok",
            "data": {
                "current": req.provider,
                "model": req.model or os.environ.get("AI_MODEL", ""),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise _err(str(e))


# ── Post-analysis follow-up chat (#103) ───────────────────────


class AnalyzeFollowupRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    question: str
    session_id: str = "default"
    context: dict = {}  # analysts, synthesis_text, report from the completed analysis


@router.post("/analyze/followup")
async def analyze_followup(req: AnalyzeFollowupRequest):
    """
    Answer a follow-up question about a completed analysis.

    Primes a TradingAgent session with the analyst verdicts and synthesis,
    then asks the user's question. The same session_id maintains conversation
    history so follow-up turns stay in context.

    Send the full analysis context on the first question; for follow-ups in
    the same session you can omit it (the agent remembers).
    """
    try:
        from agent.core import get_provider

        # Unique session per symbol so the LLM remembers the analysis context
        session_key = f"followup_{req.symbol}_{req.exchange}_{req.session_id}"

        # If new analysis context is provided, always create a fresh session
        # so a second analyze of the same symbol gets fresh context (not stale)
        has_new_context = bool(
            req.context.get("analysts")
            or req.context.get("synthesis_text")
            or req.context.get("report")
        )
        if session_key not in _chat_sessions or has_new_context:
            # Build a system message from the primed context
            analysts = req.context.get("analysts", [])
            synthesis_text = req.context.get("synthesis_text") or ""
            report = req.context.get("report") or ""

            ctx_lines = [
                f"You are a trading analysis assistant in follow-up mode for {req.symbol} ({req.exchange}).",
                f"All follow-up questions are about {req.symbol} unless the user explicitly names another stock.",
                f"Interpret all industry terms, product names, and business concepts in the context of {req.symbol}'s business — "
                f"for example, 'AI deals' means {req.symbol}'s AI contracts and partnerships, not a stock ticker called AI.",
                f"Be concise, direct, and always ground your answer in {req.symbol}'s specific situation.",
            ]
            if analysts or synthesis_text or report:
                ctx_lines.append(
                    f"\nThe following multi-agent analysis was just completed for {req.symbol} ({req.exchange}):\n"
                )
                if analysts:
                    ctx_lines.append("Analyst verdicts:")
                    for a in analysts:
                        verdict = a.get("verdict", "")
                        conf = a.get("confidence", "")
                        name = a.get("name", "")
                        ctx_lines.append(f"  • {name}: {verdict} ({conf}%)")
                        for pt in a.get("key_points") or []:
                            ctx_lines.append(f"    – {pt}")
                if synthesis_text:
                    ctx_lines.append(f"\nFund Manager Synthesis:\n{synthesis_text}")
                if report:
                    ctx_lines.append(
                        f"\nFull Report:\n{report[:3000]}"
                    )  # cap to avoid token overflow
                ctx_lines.append("\nUse the analysis above as your primary source of truth.")

            system_msg = "\n".join(ctx_lines)
            # Store session as dict with system prompt and message history
            _chat_sessions[session_key] = {
                "system": system_msg,
                "history": [],
            }

        session = _chat_sessions[session_key]

        # Build messages: system + history + new question
        session["history"].append({"role": "user", "content": req.question})

        # Direct LLM call — empty registry so NO tools are available
        from agent.core import ToolRegistry
        provider = get_provider(registry=ToolRegistry())
        messages = [
            {"role": "system", "content": session["system"]},
        ] + session["history"]

        response = provider.chat(messages=messages, stream=False)

        session["history"].append({"role": "assistant", "content": response})

        return {
            "status": "ok",
            "data": {
                "response": response,
                "symbol": req.symbol,
                "session_id": session_key,
                "history_length": len(session["history"]),
            },
        }
    except Exception as e:
        raise _err(str(e))
