"""
agent/tools.py
──────────────
Tool definitions and executor for the trading agent.

Each tool maps a Claude/OpenAI function call → a Python function.
Two formats are generated:
  - anthropic_schema()  → list[dict]  (Anthropic tools format)
  - openai_schema()     → list[dict]  (OpenAI function calling format)

Tool executor dispatches the call and returns a JSON-serialisable result.
"""

from __future__ import annotations

import traceback
from typing import Any, Callable


# ── Tool registry ─────────────────────────────────────────────


class ToolRegistry:
    """Holds all tools with their schemas and Python implementations."""

    def __init__(self) -> None:
        self._tools: dict[str, dict] = {}  # name → {fn, description, params, flags}
        # Soft tool limiter — warns on excessive or looping tool calls (#177)
        from engine.tool_limiter import ToolLimiter

        self._limiter = ToolLimiter()

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,  # JSON Schema object for the params
        fn: Callable,
        *,
        is_read_only: bool = False,
        is_destructive: bool = False,
        is_concurrency_safe: bool = False,
        permission: str = "auto",  # "auto" | "ask" | "deny"
    ) -> None:
        """
        Register a tool with optional permission flags (inspired by Claude Code).

        Flags:
          is_read_only        — Tool only reads data, never modifies state.
                                Read-only tools are auto-approved in all modes.
          is_destructive      — Tool modifies real-world state (places orders, etc).
                                Destructive tools default to permission="ask".
          is_concurrency_safe — Tool can run in parallel with other tools safely.
                                Used for future parallel execution optimisation.
          permission          — "auto" (run freely) | "ask" (always confirm) |
                                "deny" (blocked; only overridable by env/config).
        """
        # Destructive tools are always "ask" unless explicitly overridden
        if is_destructive and permission == "auto":
            permission = "ask"

        self._tools[name] = {
            "fn": fn,
            "description": description,
            "parameters": parameters,
            "is_read_only": is_read_only,
            "is_destructive": is_destructive,
            "is_concurrency_safe": is_concurrency_safe,
            "permission": permission,
        }

    # ── Permission queries ────────────────────────────────────

    def is_read_only(self, name: str) -> bool:
        return self._tools.get(name, {}).get("is_read_only", False)

    def is_destructive(self, name: str) -> bool:
        return self._tools.get(name, {}).get("is_destructive", False)

    def is_concurrency_safe(self, name: str) -> bool:
        return self._tools.get(name, {}).get("is_concurrency_safe", False)

    def permission(self, name: str) -> str:
        return self._tools.get(name, {}).get("permission", "auto")

    def destructive_names(self) -> list[str]:
        """Return names of all destructive tools."""
        return [n for n, t in self._tools.items() if t.get("is_destructive")]

    def read_only_names(self) -> list[str]:
        """Return names of all read-only tools."""
        return [n for n, t in self._tools.items() if t.get("is_read_only")]

    # ── Schemas ───────────────────────────────────────────────

    def anthropic_schema(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for name, t in self._tools.items()
            if t.get("permission") != "deny"
        ]

    def openai_schema(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for name, t in self._tools.items()
            if t.get("permission") != "deny"
        ]

    def execute(self, name: str, arguments: dict) -> Any:
        """Run a tool by name with given arguments. Returns JSON-serialisable result."""
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        if self._tools[name].get("permission") == "deny":
            return {"error": f"Tool '{name}' is blocked by permission rules."}

        # Check and record for loop/limit detection (#177)
        warning = self._limiter.check_and_record(name)

        try:
            result = self._tools[name]["fn"](**arguments)
            serialised = _serialise(result)
            # Prepend warning to result if limit was hit
            if warning:
                if isinstance(serialised, dict):
                    serialised["_tool_warning"] = warning
                else:
                    serialised = {"result": serialised, "_tool_warning": warning}
            return serialised
        except Exception as exc:
            return {"error": str(exc), "trace": traceback.format_exc()[-500:]}

    def execute_parallel(self, tool_calls: list[dict]) -> list[dict]:
        """
        Execute a batch of tool calls, running concurrency-safe tools in parallel.

        Inspired by Claude Code's concurrent tool execution: tools marked
        is_concurrency_safe=True run via ThreadPoolExecutor; unsafe tools run
        sequentially after. Results are always returned in the original call order.

        Args:
            tool_calls: List of dicts with keys: id, name, input

        Returns:
            List of tool_result dicts (Anthropic format) in original call order.
        """
        import json
        from concurrent.futures import ThreadPoolExecutor, as_completed

        safe = [tc for tc in tool_calls if self.is_concurrency_safe(tc["name"])]
        unsafe = [tc for tc in tool_calls if not self.is_concurrency_safe(tc["name"])]

        results: dict[str, Any] = {}

        # Run safe tools in parallel
        if safe:
            with ThreadPoolExecutor(max_workers=len(safe)) as pool:
                futures = {
                    pool.submit(self.execute, tc["name"], tc["input"]): tc["id"] for tc in safe
                }
                for future in as_completed(futures):
                    tool_id = futures[future]
                    try:
                        results[tool_id] = future.result()
                    except Exception as exc:
                        results[tool_id] = {"error": str(exc)}

        # Run unsafe tools sequentially
        for tc in unsafe:
            results[tc["id"]] = self.execute(tc["name"], tc["input"])

        # Rebuild in original order
        return [
            {
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": json.dumps(results[tc["id"]]),
            }
            for tc in tool_calls
        ]

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())


# ── Serialiser ────────────────────────────────────────────────


def _serialise(obj: Any) -> Any:
    """Convert dataclasses, DataFrames, dates etc. to JSON-safe types."""
    import dataclasses
    import pandas as pd
    from datetime import date, datetime

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialise(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialise(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, pd.DataFrame):
        return obj.reset_index().to_dict(orient="records")
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


# ── Signal ensemble helper ────────────────────────────────────


def _run_signal_ensemble(symbol: str, days: int = 250) -> dict:
    """Fetch OHLCV and run the 5-strategy ensemble for the given symbol."""
    from market.history import get_ohlcv
    from engine.signal_ensemble import ensemble_signal

    df = get_ohlcv(symbol, days=days)
    sig = ensemble_signal(df)
    return {
        "symbol": symbol,
        "verdict": sig.verdict,
        "signal": sig.signal,
        "confidence": sig.confidence,
        "bull_score": sig.bull_score,
        "bear_score": sig.bear_score,
        "hurst": sig.hurst,
        "adx": sig.adx,
        "breakdown": {
            name: {"signal": v.signal, "label": v.label, "detail": v.detail}
            for name, v in sig.breakdown.items()
        },
    }


# ── Tool builder ──────────────────────────────────────────────


def build_registry() -> ToolRegistry:
    """Create and populate the tool registry with all platform functions."""
    reg = ToolRegistry()

    # ── Broker / Account ──────────────────────────────────────
    from brokers.session import get_broker

    reg.register(
        name="get_funds",
        description="Get the user's available cash, used margin, and total account balance.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_broker().get_funds(),
    )

    reg.register(
        name="get_holdings",
        description="Get all long-term delivery holdings with current price and P&L.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_broker().get_holdings(),
    )

    reg.register(
        name="get_positions",
        description="Get all open intraday and F&O positions with current P&L.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_broker().get_positions(),
    )

    reg.register(
        name="get_orders",
        description="Get all orders placed today with their status.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_broker().get_orders(),
    )

    # ── Market Data ───────────────────────────────────────────
    from market.quotes import get_quote
    from market.indices import get_market_snapshot, get_vix, get_sector_snapshot
    from market.options import get_options_chain, get_pcr, get_max_pain

    reg.register(
        name="get_quote",
        description=(
            "Get live market quote(s) for one or more instruments. "
            "Instrument format: 'EXCHANGE:SYMBOL' e.g. ['NSE:RELIANCE', 'NSE:NIFTY 50', 'NSE:INDIA VIX']."
        ),
        parameters={
            "type": "object",
            "properties": {
                "instruments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of instruments like ['NSE:RELIANCE', 'NSE:NIFTY 50']",
                }
            },
            "required": ["instruments"],
        },
        fn=lambda instruments: get_quote(instruments),
    )

    reg.register(
        name="get_market_snapshot",
        description=(
            "Get a full market snapshot: NIFTY 50, BANKNIFTY, India VIX, SENSEX levels, "
            "day change %, and an overall market posture (BULLISH/BEARISH/NEUTRAL/VOLATILE). "
            "Also includes GIFT NIFTY pre-market indicator when available."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_market_snapshot(),
    )

    from market.gift_nifty import get_gift_nifty

    reg.register(
        name="get_gift_nifty",
        description=(
            "Get GIFT NIFTY (NSE IFSC futures) price — the primary pre-market indicator for NSE. "
            "GIFT NIFTY trades when NSE is closed (evenings, early morning, weekends) and is the "
            "best predictor of gap-up / gap-down opens. Returns LTP, change, and implied gap % "
            "vs NIFTY spot when nifty_spot is provided."
        ),
        parameters={
            "type": "object",
            "properties": {
                "nifty_spot": {
                    "type": "number",
                    "description": "Current NIFTY 50 spot price to compute premium/discount. Optional.",
                },
            },
            "required": [],
        },
        fn=lambda nifty_spot=None: get_gift_nifty(nifty_spot),
    )

    reg.register(
        name="get_vix",
        description="Get current India VIX level. VIX > 20 = danger zone; < 12 = complacent.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: {"vix": get_vix()},
    )

    reg.register(
        name="get_sector_snapshot",
        description="Get performance of all major NSE sector indices (IT, Pharma, Auto, FMCG, etc.).",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_sector_snapshot(),
    )

    reg.register(
        name="get_options_chain",
        description=(
            "Get the full options chain for an underlying index or stock. "
            "Returns all strikes with CE/PE prices, OI, OI change, volume, and IV."
        ),
        parameters={
            "type": "object",
            "properties": {
                "underlying": {
                    "type": "string",
                    "description": "e.g. 'NIFTY', 'BANKNIFTY', 'RELIANCE'",
                },
                "expiry": {
                    "type": "string",
                    "description": "Optional. 'YYYY-MM-DD'. Defaults to nearest expiry.",
                },
            },
            "required": ["underlying"],
        },
        fn=lambda underlying, expiry=None: get_options_chain(underlying, expiry),
    )

    reg.register(
        name="get_pcr",
        description=(
            "Get the Put-Call Ratio (by OI) for an underlying. "
            "PCR > 1.2 = bearish sentiment; PCR < 0.8 = bullish."
        ),
        parameters={
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
                "expiry": {"type": "string", "description": "Optional expiry date YYYY-MM-DD"},
            },
            "required": ["underlying"],
        },
        fn=lambda underlying, expiry=None: {"pcr": get_pcr(underlying, expiry)},
    )

    reg.register(
        name="get_max_pain",
        description=(
            "Get the max pain strike for an underlying — the strike where option buyers lose the most. "
            "Markets often gravitate towards max pain near expiry."
        ),
        parameters={
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
                "expiry": {"type": "string"},
            },
            "required": ["underlying"],
        },
        fn=lambda underlying, expiry=None: {"max_pain": get_max_pain(underlying, expiry)},
    )

    # ── Analysis ──────────────────────────────────────────────
    from analysis.technical import analyse as tech_analyse
    from analysis.fundamental import analyse as fund_analyse, score_fundamentals
    from analysis.options import (
        compute_greeks,
        payoff as calc_payoff,
        PayoffLeg,
    )

    reg.register(
        name="technical_analyse",
        description=(
            "Full technical analysis for a stock or index: RSI, MACD, EMA20/50, SMA200, "
            "Bollinger Bands, ATR, volume, support/resistance, pivot points. "
            "Returns a verdict (BULLISH/BEARISH/NEUTRAL) and score -100 to +100."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'RELIANCE'"},
                "exchange": {"type": "string", "default": "NSE"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, exchange="NSE": tech_analyse(symbol, exchange),
    )

    reg.register(
        name="fundamental_analyse",
        description=(
            "Full fundamental analysis: PE, PB, ROE, ROCE, margins, growth, D/E, FCF, "
            "promoter/FII/DII holding (from NSE quarterly filings), pledge status, "
            "analyst consensus (target price, rating), governance risk, insider transactions, "
            "forward PE, earnings date, sector/industry. Score 0-100 and verdict."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'HDFCBANK'"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol: fund_analyse(symbol),
    )

    reg.register(
        name="score_fundamentals",
        description=(
            "Structured India fundamentals scorer (#171). Returns a per-metric breakdown "
            "using India-adjusted thresholds: ROE (>15% bull, <8% bear, weight 20%), "
            "Net Profit Margin (>15%/>5%, 15%), Revenue Growth 3Y CAGR (>15%/<5%, 15%), "
            "Debt/Equity (<0.5/>1.5, 15%), Promoter Holding (>50%/<25%, 10%), "
            "Pledged % (<10%/>30%, 10%), Dividend Yield (>2%, 5%), PE (<20/>40, 10%). "
            "Overall score -1.0 to +1.0; signal STRONG / NEUTRAL / WEAK."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'RELIANCE'"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol: score_fundamentals(symbol),
    )

    reg.register(
        name="signal_ensemble",
        description=(
            "Weighted multi-strategy signal ensemble (#167). Runs 5 strategies on OHLCV data: "
            "Trend (EMA+ADX, 25%), Mean Reversion (RSI+Bollinger, 20%), Momentum (1M/3M/6M, 25%), "
            "Volatility regime (ATR, 15%), Statistical (Hurst exponent, 15%). "
            "Returns BULLISH/NEUTRAL/BEARISH with confidence score and per-strategy breakdown."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'NIFTY'"},
                "days": {
                    "type": "integer",
                    "description": "Lookback window in trading days (default 250)",
                    "default": 250,
                },
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, days=250: _run_signal_ensemble(symbol, days),
    )

    reg.register(
        name="compute_greeks",
        description=(
            "Compute Black-Scholes Greeks (delta, gamma, theta, vega) and implied volatility "
            "for a specific options contract."
        ),
        parameters={
            "type": "object",
            "properties": {
                "spot": {"type": "number", "description": "Current spot price"},
                "strike": {"type": "number"},
                "expiry": {"type": "string", "description": "YYYY-MM-DD"},
                "option_type": {"type": "string", "enum": ["CE", "PE"]},
                "ltp": {"type": "number", "description": "Last traded price of option"},
            },
            "required": ["spot", "strike", "expiry", "option_type", "ltp"],
        },
        fn=lambda spot, strike, expiry, option_type, ltp: compute_greeks(
            spot, strike, expiry, option_type, ltp
        ),
    )

    reg.register(
        name="get_iv_rank",
        description=(
            "Get the IV Rank for a symbol (0–100), computed from 52-week historical realized volatility. "
            ">50 = volatility elevated (good for selling premium). <30 = volatility low (good for buying options)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol: {
            "iv_rank": __import__(
                "analysis.options", fromlist=["compute_iv_rank_from_history"]
            ).compute_iv_rank_from_history(symbol),
            "method": "30-day rolling realized volatility ranked over 52 weeks",
        },
    )

    reg.register(
        name="payoff_calculate",
        description=(
            "Calculate P&L payoff at expiry for a multi-leg options strategy. "
            "Returns max profit, max loss, breakeven points, and full payoff table. "
            "Use this for spreads, condors, straddles etc."
        ),
        parameters={
            "type": "object",
            "properties": {
                "legs": {
                    "type": "array",
                    "description": "List of strategy legs",
                    "items": {
                        "type": "object",
                        "properties": {
                            "option_type": {"type": "string", "enum": ["CE", "PE", "STOCK"]},
                            "transaction": {"type": "string", "enum": ["BUY", "SELL"]},
                            "strike": {"type": "number"},
                            "premium": {"type": "number"},
                            "lot_size": {"type": "integer"},
                            "lots": {"type": "integer", "default": 1},
                        },
                        "required": ["option_type", "transaction", "strike", "premium", "lot_size"],
                    },
                },
                "spot_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Optional [min_spot, max_spot] range for payoff calculation",
                },
            },
            "required": ["legs"],
        },
        fn=lambda legs, spot_range=None: calc_payoff(
            [PayoffLeg(**leg) for leg in legs],
            tuple(spot_range) if spot_range else None,
        ),
    )

    # ── News & Events ─────────────────────────────────────────
    from market.news import get_market_news, get_stock_news
    from market.events import get_upcoming_events, get_earnings_calendar
    from market.sentiment import get_fii_dii_data, get_market_breadth, get_sentiment

    reg.register(
        name="get_market_news",
        description="Get top Indian market headlines from ET, MoneyControl, Business Standard RSS feeds.",
        parameters={
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 10, "description": "Number of headlines"},
            },
            "required": [],
        },
        fn=lambda n=10: get_market_news(n),
    )

    reg.register(
        name="get_stock_news",
        description="Get recent news articles for a specific stock symbol.",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "n": {"type": "integer", "default": 8},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, n=8: get_stock_news(symbol, n),
    )

    reg.register(
        name="get_upcoming_events",
        description=(
            "Get all upcoming market events: F&O expiry dates, earnings calendar, "
            "RBI MPC meetings. Essential context before placing any trade."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 14},
            },
            "required": [],
        },
        fn=lambda days=14: get_upcoming_events(days),
    )

    reg.register(
        name="get_fii_dii_data",
        description=(
            "Get FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor) "
            "buy/sell activity in INR crore for the last N trading days. "
            "FII net buying = bullish signal; net selling = bearish."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 5},
            },
            "required": [],
        },
        fn=lambda days=5: get_fii_dii_data(days),
    )

    reg.register(
        name="get_market_breadth",
        description=(
            "Get advance/decline ratio for NSE (NIFTY 500 universe). "
            "A/D > 2 = broad rally; A/D < 0.5 = broad decline."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_market_breadth(),
    )

    reg.register(
        name="get_sentiment",
        description=(
            "India market sentiment aggregator for a symbol (#172). Combines four signals: "
            "FII/DII net flows (30%), news sentiment (25%), bulk deals (25%), "
            "market breadth (20%). Returns BULLISH/NEUTRAL/BEARISH with breakdown."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'INFY'"},
                "exchange": {"type": "string", "default": "NSE"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, exchange="NSE": get_sentiment(symbol, exchange),
    )

    # ── Alerts ─────────────────────────────────────────────────
    from engine.alerts import alert_manager

    reg.register(
        name="set_price_alert",
        description=(
            "Set a price alert for a stock or index. "
            "E.g. alert when NIFTY crosses 22500, or when RELIANCE goes above 2800."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'RELIANCE'"},
                "condition": {"type": "string", "enum": ["ABOVE", "BELOW", "CROSSES"]},
                "threshold": {"type": "number", "description": "Price level"},
                "exchange": {"type": "string", "default": "NSE"},
            },
            "required": ["symbol", "condition", "threshold"],
        },
        fn=lambda symbol, condition, threshold, exchange="NSE": {
            "status": "created",
            "alert": alert_manager.add_price_alert(
                symbol, condition, threshold, exchange
            ).describe(),
        },
    )

    reg.register(
        name="set_technical_alert",
        description=(
            "Set a technical indicator alert. "
            "E.g. alert when RELIANCE RSI goes above 70, or INFY RSI below 30."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "indicator": {"type": "string", "enum": ["RSI", "MACD", "ADX", "ATR"]},
                "condition": {"type": "string", "enum": ["ABOVE", "BELOW"]},
                "threshold": {"type": "number"},
                "exchange": {"type": "string", "default": "NSE"},
            },
            "required": ["symbol", "indicator", "condition", "threshold"],
        },
        fn=lambda symbol, indicator, condition, threshold, exchange="NSE": {
            "status": "created",
            "alert": alert_manager.add_technical_alert(
                symbol, indicator, condition, threshold, exchange
            ).describe(),
        },
    )

    reg.register(
        name="list_alerts",
        description="List all active price and technical alerts.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: {"alerts": alert_manager.list_alerts()},
    )

    reg.register(
        name="remove_alert",
        description="Remove an alert by its ID.",
        parameters={
            "type": "object",
            "properties": {
                "alert_id": {"type": "string", "description": "Alert ID to remove"},
            },
            "required": ["alert_id"],
        },
        fn=lambda alert_id: {
            "removed": alert_manager.remove_alert(alert_id),
        },
    )

    reg.register(
        name="set_conditional_alert",
        description=(
            "Set a conditional alert with AND logic — triggers only when ALL conditions are met. "
            "E.g. 'Alert when RELIANCE price > 2800 AND RSI > 60'. "
            "Each condition is either PRICE (above/below a price) or TECHNICAL (indicator above/below)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol"},
                "conditions": {
                    "type": "array",
                    "description": "List of conditions (all must be true)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "condition_type": {"type": "string", "enum": ["PRICE", "TECHNICAL"]},
                            "condition": {"type": "string", "enum": ["ABOVE", "BELOW"]},
                            "threshold": {"type": "number"},
                            "indicator": {
                                "type": "string",
                                "description": "For TECHNICAL: RSI, MACD, ADX, ATR",
                            },
                        },
                        "required": ["condition_type", "condition", "threshold"],
                    },
                },
            },
            "required": ["symbol", "conditions"],
        },
        fn=lambda symbol, conditions: {
            "status": "created",
            "alert": alert_manager.add_conditional_alert(symbol, conditions).describe(),
        },
    )

    # ── Portfolio Greeks ──────────────────────────────────────
    from engine.portfolio import get_position_greeks

    reg.register(
        name="get_portfolio_greeks",
        description=(
            "Get aggregated portfolio Greeks (Delta, Gamma, Theta, Vega) across all F&O positions. "
            "Shows net exposure and breakdown by underlying. "
            "Positive delta = net long, negative = net short. Negative theta = time decay cost."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: {
            "net_delta": get_position_greeks().net_delta,
            "net_theta": get_position_greeks().net_theta,
            "net_vega": get_position_greeks().net_vega,
            "net_gamma": get_position_greeks().net_gamma,
            "by_underlying": get_position_greeks().by_underlying,
            "positions": len(get_position_greeks().positions_with_greeks),
        },
    )

    # ── India Intelligence ─────────────────────────────────────
    from market.earnings import get_pre_earnings_iv
    from market.flow_intel import get_flow_analysis
    from engine.event_strategies import get_event_strategies

    reg.register(
        name="get_earnings_calendar",
        description=(
            "Get upcoming quarterly earnings dates for NIFTY 50 stocks or specific symbols. "
            "Shows expected result dates, historical avg post-earnings move %."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of symbols. Defaults to NIFTY 50.",
                },
            },
            "required": [],
        },
        fn=lambda symbols=None: [
            {
                "symbol": e.symbol,
                "date": e.result_date,
                "quarter": e.quarter,
                "avg_move": e.avg_move,
                "status": e.status,
            }
            for e in get_earnings_calendar(symbols)
        ],
    )

    reg.register(
        name="get_pre_earnings_iv",
        description=(
            "Check IV rank before earnings for a stock. Suggests whether to buy or sell "
            "options around the earnings event. High IV = sell premium, Low IV = buy straddle."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock symbol"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol: get_pre_earnings_iv(symbol),
    )

    reg.register(
        name="get_flow_intelligence",
        description=(
            "Comprehensive FII/DII flow analysis: streaks, 5-day totals, divergence detection, "
            "momentum, and a trading signal. E.g. 'FII selling 5 days straight, -8000 Cr'."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: {k: v for k, v in get_flow_analysis().__dict__.items() if k != "raw_data"},
    )

    reg.register(
        name="get_event_strategies",
        description=(
            "Get event-driven trading strategies for upcoming events (expiry, RBI, earnings, budget). "
            "Each strategy includes timing, instruments, risk level, and rationale."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days_ahead": {"type": "integer", "default": 7},
            },
            "required": [],
        },
        fn=lambda days_ahead=7: [
            {
                "event": s.event,
                "date": s.event_date,
                "days": s.days_away,
                "strategy": s.strategy,
                "risk": s.risk_level,
                "rationale": s.rationale,
            }
            for s in get_event_strategies(days_ahead=days_ahead)
        ],
    )

    # ── Backtest & Simulation ─────────────────────────────────
    from engine.backtest import run_backtest
    from engine.simulator import Simulator

    reg.register(
        name="run_backtest",
        description=(
            "Backtest a trading strategy on historical data. "
            "Strategies: rsi, ma (EMA crossover), macd, bb (Bollinger). "
            "Returns total return, Sharpe ratio, win rate, max drawdown vs buy-and-hold."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE symbol e.g. 'RELIANCE'"},
                "strategy": {
                    "type": "string",
                    "enum": ["rsi", "ma", "macd", "bb"],
                    "description": "Strategy to test",
                },
                "period": {
                    "type": "string",
                    "default": "1y",
                    "description": "Lookback: 1y, 2y, 3y, 5y",
                },
            },
            "required": ["symbol", "strategy"],
        },
        fn=lambda symbol, strategy="rsi", period="1y": {
            k: v
            for k, v in run_backtest(symbol, strategy, period=period).__dict__.items()
            if k not in ("trades", "equity_curve")
        },
    )

    reg.register(
        name="whatif_market_move",
        description=(
            "Simulate what happens to the user's portfolio if NIFTY moves by a given %. "
            "E.g. 'What if NIFTY drops 3%?' Shows position-wise impact."
        ),
        parameters={
            "type": "object",
            "properties": {
                "nifty_change_pct": {
                    "type": "number",
                    "description": "NIFTY change in %. Negative for drop, positive for rally.",
                },
            },
            "required": ["nifty_change_pct"],
        },
        fn=lambda nifty_change_pct: Simulator().scenario_market_move(nifty_change_pct).__dict__,
    )

    reg.register(
        name="whatif_stock_move",
        description=(
            "Simulate what happens if a specific stock moves by a given %. "
            "Shows impact on portfolio positions in that stock."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock symbol"},
                "change_pct": {"type": "number", "description": "% change (negative for drop)"},
            },
            "required": ["symbol", "change_pct"],
        },
        fn=lambda symbol, change_pct: Simulator().scenario_stock_move(symbol, change_pct).__dict__,
    )

    # ── Strategy Builder Tools ─────────────────────────────────

    def _find_similar(description: str) -> list:
        from engine.strategy_builder import find_similar_strategies

        return find_similar_strategies(description)

    reg.register(
        name="find_similar_strategies",
        description="Find existing strategies similar to a plain-English description. Returns matching built-in and user-saved strategies.",
        parameters={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Plain-English description of the strategy idea",
                },
            },
            "required": ["description"],
        },
        fn=_find_similar,
    )

    def _backtest_user_strategy(name: str, symbol: str = "", period: str = "1y") -> dict:
        from engine.strategy_builder import strategy_store
        from engine.backtest import Backtester

        strategy = strategy_store.load_strategy(name)
        meta = strategy_store.get_metadata(name)
        sym = symbol or (meta.get("default_symbol", "RELIANCE") if meta else "RELIANCE")
        bt = Backtester(symbol=sym, period=period)
        result = bt.run(strategy)
        return {
            "symbol": sym,
            "period": period,
            "strategy": name,
            "total_return": round(result.total_return, 2),
            "sharpe": round(result.sharpe_ratio, 2),
            "win_rate": round(result.win_rate, 1),
            "max_drawdown": round(result.max_drawdown, 2),
            "total_trades": result.total_trades,
            "buy_hold_return": round(result.buy_hold_return, 2),
        }

    reg.register(
        name="backtest_user_strategy",
        description="Backtest a user-saved custom strategy on a given symbol and period.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the saved strategy"},
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (default: strategy's default)",
                },
                "period": {
                    "type": "string",
                    "description": "Backtest period: 1y, 2y, 3y, 5y (default: 1y)",
                },
            },
            "required": ["name"],
        },
        fn=_backtest_user_strategy,
    )

    def _list_user_strategies() -> list:
        from engine.strategy_builder import strategy_store

        return strategy_store.list_strategies()

    reg.register(
        name="list_user_strategies",
        description="List all user-saved custom strategies with their metadata and last backtest results.",
        parameters={"type": "object", "properties": {}},
        fn=_list_user_strategies,
    )

    # ── Options Backtesting ────────────────────────────────────

    def _backtest_options(underlying: str, strategy: str = "straddle", period: str = "1y") -> dict:
        from engine.options_backtest import run_options_backtest

        result = run_options_backtest(underlying, strategy, period=period)
        return {
            "underlying": result.underlying,
            "strategy": result.strategy_name,
            "period": result.period,
            "total_pnl": result.total_pnl,
            "total_return": result.total_return,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "avg_win": result.avg_win,
            "avg_loss": result.avg_loss,
            "max_drawdown": result.max_drawdown,
            "sharpe": result.sharpe_ratio,
        }

    reg.register(
        name="backtest_options",
        description=(
            "Backtest an options strategy (straddle, iron-condor, covered-call, protective-put) "
            "on a given underlying and period. Uses Black-Scholes synthetic pricing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "underlying": {
                    "type": "string",
                    "description": "Underlying symbol (e.g., NIFTY, BANKNIFTY, RELIANCE)",
                },
                "strategy": {
                    "type": "string",
                    "description": "Options strategy: straddle, iron-condor, covered-call, protective-put",
                },
                "period": {
                    "type": "string",
                    "description": "Backtest period: 1y, 2y, 3y (default: 1y)",
                },
            },
            "required": ["underlying", "strategy"],
        },
        fn=_backtest_options,
    )

    # ── Greeks Management ────────────────────────────────────

    def _suggest_delta_hedge(target_delta: float = 0.0) -> dict:
        from engine.portfolio import get_position_greeks
        from engine.greeks_manager import compute_delta_hedge

        pg = get_position_greeks()
        s = compute_delta_hedge(pg.net_delta, target_delta)
        return {
            "current_delta": s.current_delta,
            "target_delta": s.target_delta,
            "gap": s.gap,
            "suggestions": s.suggestions,
        }

    reg.register(
        name="suggest_delta_hedge",
        description="Suggest trades to neutralize or adjust portfolio delta. Returns concrete hedge suggestions with lot counts.",
        parameters={
            "type": "object",
            "properties": {
                "target_delta": {
                    "type": "number",
                    "description": "Target delta (default 0 = delta-neutral)",
                },
            },
        },
        fn=_suggest_delta_hedge,
    )

    def _get_greeks_dashboard() -> dict:
        from engine.portfolio import get_position_greeks
        from engine.greeks_manager import build_dashboard

        pg = get_position_greeks()
        d = build_dashboard(pg.net_delta, pg.net_theta, pg.net_vega, pg.net_gamma)
        return {
            "net_delta": d.net_delta,
            "net_theta": d.net_theta,
            "net_vega": d.net_vega,
            "net_gamma": d.net_gamma,
            "risk_level": d.risk_level,
            "warnings": d.warnings,
            "actions": d.actions,
        }

    reg.register(
        name="get_greeks_dashboard",
        description="Get enhanced portfolio Greeks dashboard with risk warnings, action items, and risk level classification.",
        parameters={"type": "object", "properties": {}},
        fn=_get_greeks_dashboard,
    )

    # ── Shareholding & Active Stocks ─────────────────────────

    def _get_shareholding(symbol: str) -> dict:
        from analysis.fundamental import _fetch_nse_shareholding

        return _fetch_nse_shareholding(symbol) or {
            "error": "Shareholding data unavailable for this symbol"
        }

    reg.register(
        name="get_shareholding_pattern",
        description=(
            "Get quarterly shareholding pattern from NSE for a stock. "
            "Returns promoter %, FII %, DII %, mutual funds %, insurance %, retail %, "
            "pledge status, and the quarter of the filing."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (e.g., RELIANCE, HDFCBANK)",
                },
            },
            "required": ["symbol"],
        },
        fn=_get_shareholding,
    )

    def _get_most_active(by: str = "volume") -> list:
        from market.active_stocks import get_most_active

        stocks = get_most_active(by=by, limit=10)
        return [
            {
                "symbol": s.symbol,
                "volume": s.volume,
                "value_cr": s.value_cr,
                "ltp": s.ltp,
                "change_pct": s.change_pct,
            }
            for s in stocks
        ]

    reg.register(
        name="get_most_active_stocks",
        description="Get the most active stocks on NSE by volume or traded value. Shows unusual activity and retail interest.",
        parameters={
            "type": "object",
            "properties": {
                "by": {"type": "string", "description": "'volume' or 'value' (default: volume)"},
            },
        },
        fn=_get_most_active,
    )

    # ── Options Analytics (#33, #47, #48, #49, #58) ──────────

    reg.register(
        name="get_oi_profile",
        description="Get OI profile for an underlying — per-strike OI, max call/put OI (resistance/support), PCR.",
        parameters={
            "type": "object",
            "properties": {"underlying": {"type": "string"}},
            "required": ["underlying"],
        },
        fn=lambda underlying: __import__(
            "market.oi_profile", fromlist=["get_oi_profile"]
        ).get_oi_profile(underlying),
    )

    reg.register(
        name="get_gex_analysis",
        description="Gamma Exposure (GEX) analysis — dealer gamma positioning, flip point, regime (POSITIVE=pinning, NEGATIVE=breakout).",
        parameters={
            "type": "object",
            "properties": {"underlying": {"type": "string"}},
            "required": ["underlying"],
        },
        fn=lambda underlying: __import__(
            "analysis.gex", fromlist=["get_gex_analysis"]
        ).get_gex_analysis(underlying),
    )

    reg.register(
        name="scan_options",
        description="Scan F&O stocks for: high IV rank (sell premium), unusual OI buildup, heavy put writing. Returns actionable setups.",
        parameters={
            "type": "object",
            "properties": {
                "quick": {"type": "boolean", "description": "Quick scan (NIFTY+BANKNIFTY only)"}
            },
        },
        fn=lambda quick=True: __import__(
            "market.options_scanner", fromlist=["scan_options"]
        ).scan_options(quick=quick),
    )

    reg.register(
        name="get_bulk_block_deals",
        description="Get recent bulk and block deals from NSE — large institutional/promoter buy/sell transactions.",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Filter by symbol (optional)"}
            },
        },
        fn=lambda symbol=None: {
            "block": [
                d.__dict__
                for d in __import__(
                    "market.bulk_deals", fromlist=["get_block_deals"]
                ).get_block_deals()
            ],
            "bulk": [
                d.__dict__
                for d in __import__(
                    "market.bulk_deals", fromlist=["get_bulk_deals"]
                ).get_bulk_deals(symbol=symbol)
            ],
        },
    )

    # ── DCF Valuation ────────────────────────────────────────

    reg.register(
        name="compute_dcf",
        description=(
            "Compute DCF (Discounted Cash Flow) valuation for a stock. "
            "Returns intrinsic value per share, margin of safety vs current price, "
            "WACC, growth assumptions, and sensitivity table (growth x WACC grid). "
            "Auto-detects FCF, growth rate, beta from financial data."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock symbol (e.g., RELIANCE, TCS)"},
                "growth_rate": {
                    "type": "number",
                    "description": "Override growth rate % (optional, auto-detected if omitted)",
                },
                "wacc": {
                    "type": "number",
                    "description": "Override WACC % (optional, auto-computed if omitted)",
                },
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, growth_rate=None, wacc=None: __import__(
            "analysis.dcf", fromlist=["dcf_for_symbol"]
        ).dcf_for_symbol(symbol, growth_rate, wacc),
    )

    # ── Tag all registered tools as read-only + concurrency-safe ──
    # Every tool in the base registry is a read/analyse tool — none place orders.
    # Destructive tools (execute_trade) are added separately by the harness.
    for tool in reg._tools.values():
        tool["is_read_only"] = True
        tool["is_concurrency_safe"] = True
        tool["is_destructive"] = False
        tool["permission"] = "auto"

    return reg
