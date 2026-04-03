"""
web/openclaw.py
───────────────
OpenClaw skill manifest for india-trade-cli.

Served at /.well-known/openclaw.json — OpenClaw agents read this to
discover available skills, their input schemas, and descriptions.

How an OpenClaw agent uses this:
  1. Agent fetches /.well-known/openclaw.json to discover skills
  2. Reads the input_schema for the skill it wants to call
  3. POSTs to /skills/<skill_name> with a JSON body matching the schema
  4. Gets back { "status": "ok", "data": { ... } }
"""

MANIFEST: dict = {
    "name": "india-trade-cli",
    "description": (
        "India stock market analysis platform. "
        "Provides live quotes, multi-agent AI analysis, FII/DII flows, "
        "options chain, backtesting, pair trading, macro data, and more — "
        "all focused on NSE/BSE listed instruments."
    ),
    "version": "1.0.0",
    "base_url": "",  # filled in at runtime from request host
    "auth": {
        "type": "none",
        # NOTE: skills server is intended for local use (127.0.0.1) only.
        # Do not expose on 0.0.0.0 without adding bearer token auth first.
    },
    "skills": [
        {
            "name": "quote",
            "path": "/skills/quote",
            "method": "POST",
            "description": "Get live price, OHLCV, and change% for an NSE/BSE symbol.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol, e.g. RELIANCE or NSE:RELIANCE",
                    },
                    "exchange": {
                        "type": "string",
                        "description": "Exchange: NSE (default) or BSE",
                        "default": "NSE",
                    },
                },
                "required": ["symbol"],
            },
            "output_description": "Quote with last_price, open, high, low, close, volume, change, change_pct.",
        },
        {
            "name": "options_chain",
            "path": "/skills/options_chain",
            "method": "POST",
            "description": "Full options chain for an underlying (all strikes, all expiries).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Underlying symbol, e.g. NIFTY or RELIANCE",
                    },
                    "exchange": {"type": "string", "default": "NSE"},
                },
                "required": ["symbol"],
            },
            "output_description": "List of OptionsContract with strike, expiry, CE/PE, IV, OI, volume, Greeks.",
        },
        {
            "name": "flows",
            "path": "/skills/flows",
            "method": "POST",
            "description": "FII and DII institutional flow data with buy/sell signals.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "output_description": "FlowAnalysis with fii_buy, fii_sell, dii_buy, dii_sell, net flows, signal, streak.",
        },
        {
            "name": "earnings",
            "path": "/skills/earnings",
            "method": "POST",
            "description": "Upcoming quarterly earnings calendar for NSE stocks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of symbols to filter. Omit for full calendar.",
                    },
                },
                "required": [],
            },
            "output_description": "List of EarningsEntry with symbol, company, expected_date, quarter, estimate.",
        },
        {
            "name": "macro",
            "path": "/skills/macro",
            "method": "POST",
            "description": "Macro snapshot: USD/INR, crude oil, gold, US 10Y yield.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional stock symbol to get macro linkage context.",
                    },
                },
                "required": [],
            },
            "output_description": "MacroSnapshot with usd_inr, crude_oil, gold, us_10y and their change_pct.",
        },
        {
            "name": "deals",
            "path": "/skills/deals",
            "method": "POST",
            "description": "Bulk and block deals from NSE. Large institutional trades.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional stock symbol to filter deals.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 5)",
                        "default": 5,
                    },
                },
                "required": [],
            },
            "output_description": "List of Deal with symbol, client, quantity, price, deal_type (BULK/BLOCK), entity_type.",
        },
        {
            "name": "backtest",
            "path": "/skills/backtest",
            "method": "POST",
            "description": "Backtest a trading strategy on historical NSE data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol, e.g. INFY"},
                    "strategy": {
                        "type": "string",
                        "description": "Strategy name: rsi, ma, ema, macd, or bb (Bollinger Bands)",
                        "enum": ["rsi", "ma", "ema", "macd", "bb"],
                        "default": "rsi",
                    },
                    "period": {
                        "type": "string",
                        "description": "History period: 6mo, 1y, 2y, 5y",
                        "default": "1y",
                    },
                    "exchange": {"type": "string", "default": "NSE"},
                },
                "required": ["symbol"],
            },
            "output_description": "BacktestResult with total_return, sharpe_ratio, max_drawdown, win_rate, total_trades.",
        },
        {
            "name": "pairs",
            "path": "/skills/pairs",
            "method": "POST",
            "description": "Pair trading analysis: correlation, spread, mean reversion signals between two stocks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "stock_a": {
                        "type": "string",
                        "description": "First stock symbol, e.g. HDFCBANK",
                    },
                    "stock_b": {
                        "type": "string",
                        "description": "Second stock symbol, e.g. ICICIBANK",
                    },
                },
                "required": ["stock_a", "stock_b"],
            },
            "output_description": "PairAnalysis with correlation, spread_zscore, half_life, signal (LONG_A/LONG_B/NEUTRAL).",
        },
        {
            "name": "analyze",
            "path": "/skills/analyze",
            "method": "POST",
            "description": (
                "Full multi-agent analysis: 7 analysts (Technical, Fundamental, Options, "
                "News/Macro, Sentiment, Sector Rotation, Risk) debate in parallel, "
                "followed by bull/bear researcher debate and fund manager synthesis. "
                "Returns full text report + 3 trade plans (aggressive/neutral/conservative). "
                "NOTE: 8 LLM calls — expect 30–90 seconds."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol, e.g. RELIANCE"},
                    "exchange": {"type": "string", "default": "NSE"},
                },
                "required": ["symbol"],
            },
            "output_description": "report (full text), trade_plans (aggressive/neutral/conservative with entry/stop/target).",
        },
        {
            "name": "deep_analyze",
            "path": "/skills/deep_analyze",
            "method": "POST",
            "description": (
                "Deep analysis — every analyst uses AI (not rule-based Python). "
                "More thorough than analyze but significantly slower. "
                "NOTE: 11+ LLM calls — expect 3–8 minutes."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol, e.g. INFY"},
                    "exchange": {"type": "string", "default": "NSE"},
                },
                "required": ["symbol"],
            },
            "output_description": "report (full text with all analyst perspectives and synthesis).",
        },
        {
            "name": "chat",
            "path": "/skills/chat",
            "method": "POST",
            "description": (
                "Multi-turn AI chat with the trading agent. "
                "The agent has access to all market tools (quotes, technicals, fundamentals, "
                "options chain, FII/DII flows, news, portfolio) and calls them autonomously. "
                "Sessions are maintained by session_id — reuse the same ID to keep context."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Your message or question to the trading agent.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier for multi-turn context (default: 'default')",
                        "default": "default",
                    },
                },
                "required": ["message"],
            },
            "output_description": "response (agent reply text), session_id, history_length.",
        },
        {
            "name": "alerts_add",
            "path": "/skills/alerts/add",
            "method": "POST",
            "description": (
                "Create a price, technical, or conditional alert. "
                "Supply a webhook_url to get a POST callback when the alert fires — "
                "no polling needed. Alerts persist across server restarts."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock symbol, e.g. RELIANCE"},
                    "exchange": {"type": "string", "default": "NSE"},
                    "condition": {
                        "type": "string",
                        "description": "ABOVE | BELOW | CROSSES (price/technical alerts)",
                        "enum": ["ABOVE", "BELOW", "CROSSES"],
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Price or indicator level to trigger at",
                    },
                    "indicator": {
                        "type": "string",
                        "description": "Technical indicator: RSI, MACD, ADX, ATR, SCORE (omit for price alert)",
                    },
                    "conditions": {
                        "type": "array",
                        "description": "List of conditions for AND logic (conditional alert)",
                        "items": {"type": "object"},
                    },
                    "webhook_url": {
                        "type": "string",
                        "description": "Optional URL to POST when alert triggers",
                    },
                },
                "required": ["symbol"],
            },
            "output_description": "Created Alert with id, alert_type, description, created_at.",
        },
        {
            "name": "alerts_list",
            "path": "/skills/alerts/list",
            "method": "POST",
            "description": "List all active (not yet triggered) alerts.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_description": "List of active Alert objects with id, type, symbol, condition, threshold.",
        },
        {
            "name": "alerts_remove",
            "path": "/skills/alerts/remove",
            "method": "POST",
            "description": "Remove an alert by its ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert ID returned when the alert was created",
                    },
                },
                "required": ["alert_id"],
            },
            "output_description": "removed: true if the alert was found and deleted.",
        },
        {
            "name": "alerts_check",
            "path": "/skills/alerts/check",
            "method": "POST",
            "description": (
                "Manually evaluate all active alerts right now. "
                "Returns alerts that triggered during this call. "
                "Use this for polling-based agents. Prefer webhook_url for push-based agents."
            ),
            "input_schema": {"type": "object", "properties": {}, "required": []},
            "output_description": "triggered (list of fired alerts), active_remaining (count still watching).",
        },
        {
            "name": "chat_reset",
            "path": "/skills/chat/reset",
            "method": "POST",
            "description": "Clear the conversation history for a session and start fresh.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "default": "default"},
                },
                "required": [],
            },
            "output_description": "cleared: true when session history has been wiped.",
        },
        {
            "name": "morning_brief",
            "path": "/skills/morning_brief",
            "method": "POST",
            "description": (
                "Daily market brief: NIFTY/BANKNIFTY snapshot, FII/DII flows, "
                "top 5 news, market breadth (advance/decline), upcoming events. "
                "Fast — no LLM calls, pure data."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "output_description": (
                "market_snapshot, institutional_flows, top_news, "
                "market_breadth, upcoming_events — all as structured JSON."
            ),
        },
    ],
}
