"""
agent/harness.py
────────────────
TradingHarness — Claude Code-style agentic loop for Indian markets.

The harness lets the LLM freely decide which tools to call, in what
order, based on what the user asks. Unlike the fixed multi-agent
pipeline (analyze), the harness is emergent — structure is determined
by the LLM, not the code.

Key differences from `ai <message>`:
  - Injects TRADER.md context (capital, risk, broker, recent trades)
  - Adds `execute_trade` tool that routes through the safety gate
  - Trading-focused system prompt — verdict + action, not just analysis
  - Isolated provider instance — doesn't pollute the main agent history

Usage:
    from agent.harness import run
    result = run("Should I buy RELIANCE? I have ₹2L", broker=broker)

REPL command:
    harness Should I buy RELIANCE? I have ₹2L
    harness What's the market doing today?
    harness Check my portfolio Greeks and suggest hedges
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from rich.console import Console

from agent.core import get_provider
from engine.trade_executor import execute_trade_plan

console = Console()

# Where TRADER.md lives on disk
TRADER_MD_PATH = Path.home() / ".trading_platform" / "TRADER.md"


# ── Broker helper (isolated so tests can patch it) ────────────


def _get_connected_broker():
    """Return the currently connected broker. Raises if none."""
    from brokers.session import get_broker

    return get_broker()


# ── TRADER.md ─────────────────────────────────────────────────


def _build_trader_context() -> str:
    """
    Build TRADER.md content from env, profile, and trade memory.
    Called when TRADER.md doesn't exist on disk.
    """
    capital = os.environ.get("TOTAL_CAPITAL", "200000")
    risk_pct = os.environ.get("DEFAULT_RISK_PCT", "2")
    mode = os.environ.get("TRADING_MODE", "PAPER")

    try:
        cap_int = int(capital)
        risk_int = int(risk_pct)
        max_risk_inr = cap_int * risk_int // 100
    except (ValueError, TypeError):
        cap_int, risk_int, max_risk_inr = 200000, 2, 4000

    # Broker name
    broker_name = "PAPER"
    try:
        profile = _get_connected_broker().get_profile()
        broker_name = profile.broker
    except Exception:
        pass

    # Recent trade memory
    memory_lines = ""
    try:
        from engine.memory import get_recent_trades

        trades = get_recent_trades(limit=5)
        if trades:
            memory_lines = "\n## Recent Trades\n" + "\n".join(f"- {t}" for t in trades)
    except Exception:
        pass

    return f"""# TRADER CONTEXT
Generated: {date.today().isoformat()}

## Profile
- Capital: ₹{cap_int:,}
- Risk per trade: {risk_int}% = ₹{max_risk_inr:,} max loss
- Broker: {broker_name}
- Mode: {mode}

## Risk Rules
- Never risk more than {risk_int}% per trade
- Max single stock exposure: 20% of capital (₹{cap_int * 20 // 100:,})
- Always define stop-loss before entry
- Paper trade new strategies first
{memory_lines}"""


def _load_trader_context() -> str:
    """Load TRADER.md from disk if it exists, otherwise build from env."""
    if TRADER_MD_PATH.exists():
        return TRADER_MD_PATH.read_text(encoding="utf-8")
    return _build_trader_context()


def save_trader_context(content: str) -> None:
    """Write TRADER.md to disk. Creates parent directories if needed."""
    TRADER_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADER_MD_PATH.write_text(content, encoding="utf-8")


# ── System prompt ─────────────────────────────────────────────


def _build_harness_system_prompt(trader_context: str) -> str:
    """Build the harness-specific system prompt with injected TRADER.md context."""
    today = date.today().strftime("%d %B %Y")
    mode = os.environ.get("TRADING_MODE", "PAPER")

    return f"""You are a trading harness for Indian financial markets (NSE/BSE/NFO).
Today is {today}. Mode: {mode}.

You have access to 45+ tools covering market data, technical analysis, fundamental analysis,
options analytics, broker operations, and trade execution. Use them freely — you decide
which tools to call, in what order, based on what the user asks.

## How you work
- Adaptive, not scripted: call the tools that make sense for the question
- Iterate: if first results raise questions, call more tools before concluding
- When you have enough data: give a clear BUY / SELL / WAIT verdict with specific levels
- Ask before executing: present the full trade plan, then ask for confirmation
- The execute_trade tool handles confirmation — never call place_order directly

## Before executing any trade
- State explicitly: LIVE ORDER or PAPER TRADE
- Show: symbol, action, quantity, price, stop-loss, target, R:R ratio
- The execute_trade tool will present a confirmation prompt — do not bypass it

## Output style (terminal-friendly)
- Bullet points and short tables, not long paragraphs
- Show the numbers: RSI, MACD, PE, OI, IV — don't say "technicals are strong"
- One clear verdict at the end with specific entry / SL / target levels

## Trader Context
{trader_context}"""


# ── execute_trade tool ────────────────────────────────────────


def _register_execute_tool(registry, broker) -> None:
    """
    Add the execute_trade tool to the registry.
    Routes through trade_executor.py's confirmation gate — never bypasses it.
    Only called when a real or paper broker is connected.
    """

    def _execute_trade(
        symbol: str,
        action: str,
        quantity: int,
        exchange: str = "NSE",
        product: str = "CNC",
        order_type: str = "MARKET",
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
    ) -> dict:
        from datetime import datetime

        from engine.trader import ExitPlan, OrderLeg, TradePlan

        leg = OrderLeg(
            action=action.upper(),
            instrument=symbol,
            exchange=exchange,
            product=product,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )

        exit_plan = None
        if stop_loss or target:
            exit_plan = ExitPlan(
                stop_loss=stop_loss or 0.0,
                stop_loss_pct=0.0,
                stop_loss_type="FIXED",
                target_1=target or 0.0,
                target_1_pct=0.0,
            )

        plan = TradePlan(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime.now().isoformat(),
            strategy_name="Harness Trade",
            direction="LONG" if action.upper() == "BUY" else "SHORT",
            instrument_type="EQUITY",
            timeframe="SWING",
            capital_deployed=quantity * (price or 0.0),
            capital_pct=0.0,
            max_risk=0.0,
            risk_pct=0.0,
            reward_risk=0.0,
            entry_orders=[leg],
            exit_plan=exit_plan,
        )

        results = execute_trade_plan(plan, broker)
        return {"orders": results, "count": len(results)}

    registry.register(
        name="execute_trade",
        description=(
            "Execute a trade order through the safety confirmation gate. "
            "Shows a full order preview and asks the user to confirm before "
            "placing any live order. Use ONLY after thorough analysis."
        ),
        parameters={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol e.g. RELIANCE, TCS",
                },
                "action": {
                    "type": "string",
                    "description": "BUY or SELL",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of shares or lots",
                },
                "exchange": {
                    "type": "string",
                    "description": "NSE | BSE | NFO (default: NSE)",
                },
                "product": {
                    "type": "string",
                    "description": "CNC (delivery) | MIS (intraday) | NRML (F&O) — default: CNC",
                },
                "order_type": {
                    "type": "string",
                    "description": "MARKET | LIMIT | SL | SL-M — default: MARKET",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price (required for LIMIT/SL orders)",
                },
                "stop_loss": {
                    "type": "number",
                    "description": "Stop-loss price to set as alert after entry",
                },
                "target": {
                    "type": "number",
                    "description": "Target price to set as alert after entry",
                },
            },
            "required": ["symbol", "action", "quantity"],
        },
        fn=_execute_trade,
    )


# ── Provider factory (isolated for testability) ───────────────


def _make_provider(registry, system_prompt: str):
    """
    Build a fresh LLM provider with the given registry and harness system prompt.
    get_provider() builds its own prompt internally; we override it after construction.
    """
    provider = get_provider(registry=registry)
    provider.system_prompt = system_prompt  # override with harness-specific prompt
    return provider


# ── Internal chat wrapper (isolated for testability) ──────────


def _get_agent_chat(provider, query: str) -> str:
    """Run one chat turn on the provider and return the response."""
    return provider.chat([{"role": "user", "content": query}], stream=True)


# ── Main entry point ──────────────────────────────────────────


def run(query: str, broker=None) -> str:
    """
    Run the trading harness for a natural language query.

    Creates a fresh isolated provider (separate from the main `ai` agent)
    with the harness system prompt and TRADER.md context injected.

    Args:
        query:  Natural language question or instruction from the user.
        broker: Connected broker instance (or None for no trade execution).

    Returns:
        Final response text from the LLM.
    """
    from agent.tools import build_registry

    # Build tool registry
    registry = build_registry()

    # Add execute_trade only when a broker is connected
    if broker is not None:
        _register_execute_tool(registry, broker)

    # Build system prompt with TRADER.md context
    trader_context = _load_trader_context()
    system_prompt = _build_harness_system_prompt(trader_context)

    # Fresh provider — isolated from the main `ai` agent
    provider = _make_provider(registry=registry, system_prompt=system_prompt)

    console.print()
    console.rule("[bold cyan]Trading Harness[/bold cyan]", style="cyan")

    response = _get_agent_chat(provider, query)

    console.rule(style="cyan")
    return response or ""
