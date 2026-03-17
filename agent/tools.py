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

import json
import traceback
from typing import Any, Callable


# ── Tool registry ─────────────────────────────────────────────

class ToolRegistry:
    """Holds all tools with their schemas and Python implementations."""

    def __init__(self) -> None:
        self._tools: dict[str, dict] = {}   # name → {fn, description, params}

    def register(
        self,
        name:        str,
        description: str,
        parameters:  dict,           # JSON Schema object for the params
        fn:          Callable,
    ) -> None:
        self._tools[name] = {
            "fn":          fn,
            "description": description,
            "parameters":  parameters,
        }

    def anthropic_schema(self) -> list[dict]:
        return [
            {
                "name":         name,
                "description":  t["description"],
                "input_schema": t["parameters"],
            }
            for name, t in self._tools.items()
        ]

    def openai_schema(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name":        name,
                    "description": t["description"],
                    "parameters":  t["parameters"],
                },
            }
            for name, t in self._tools.items()
        ]

    def execute(self, name: str, arguments: dict) -> Any:
        """Run a tool by name with given arguments. Returns JSON-serialisable result."""
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        try:
            result = self._tools[name]["fn"](**arguments)
            return _serialise(result)
        except Exception as exc:
            return {"error": str(exc), "trace": traceback.format_exc()[-500:]}

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
    if isinstance(obj, float) and (obj != obj):   # NaN
        return None
    return obj


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
    from market.quotes  import get_quote
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
            "day change %, and an overall market posture (BULLISH/BEARISH/NEUTRAL/VOLATILE)."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda: get_market_snapshot(),
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
                "expiry":     {"type": "string", "description": "Optional expiry date YYYY-MM-DD"},
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
                "expiry":     {"type": "string"},
            },
            "required": ["underlying"],
        },
        fn=lambda underlying, expiry=None: {"max_pain": get_max_pain(underlying, expiry)},
    )

    # ── Analysis ──────────────────────────────────────────────
    from analysis.technical    import analyse as tech_analyse
    from analysis.fundamental  import analyse as fund_analyse
    from analysis.options      import (
        compute_greeks, payoff as calc_payoff,
        PayoffLeg, mock_iv_rank,
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
                "symbol":   {"type": "string", "description": "NSE symbol e.g. 'RELIANCE'"},
                "exchange": {"type": "string", "default": "NSE"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol, exchange="NSE": tech_analyse(symbol, exchange),
    )

    reg.register(
        name="fundamental_analyse",
        description=(
            "Fundamental analysis from Screener.in: PE, PB, ROE, ROCE, revenue & profit growth, "
            "debt/equity, promoter holding, pledged %. Returns a score 0–100 and verdict."
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
        name="compute_greeks",
        description=(
            "Compute Black-Scholes Greeks (delta, gamma, theta, vega) and implied volatility "
            "for a specific options contract."
        ),
        parameters={
            "type": "object",
            "properties": {
                "spot":        {"type": "number", "description": "Current spot price"},
                "strike":      {"type": "number"},
                "expiry":      {"type": "string", "description": "YYYY-MM-DD"},
                "option_type": {"type": "string", "enum": ["CE", "PE"]},
                "ltp":         {"type": "number", "description": "Last traded price of option"},
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
            "Get the IV Rank for a symbol (0–100). "
            ">50 = IV elevated (good for selling premium). <30 = IV low (good for buying)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
            },
            "required": ["symbol"],
        },
        fn=lambda symbol: {"iv_rank": mock_iv_rank(symbol)},
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
                            "strike":      {"type": "number"},
                            "premium":     {"type": "number"},
                            "lot_size":    {"type": "integer"},
                            "lots":        {"type": "integer", "default": 1},
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
    from market.news      import get_market_news, get_stock_news
    from market.events    import get_upcoming_events, get_expiry_dates, get_earnings_calendar
    from market.sentiment import get_fii_dii_data, get_market_breadth, score_news_batch

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
                "n":      {"type": "integer", "default": 8},
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

    return reg
