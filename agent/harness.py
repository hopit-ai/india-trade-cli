"""
agent/harness.py
────────────────
TradingHarness — Claude Code-style agentic loop for Indian markets.

The harness lets the LLM freely decide which tools to call, in what
order, based on what the user asks. Unlike the fixed multi-agent
pipeline (analyze), the harness is emergent — structure is determined
by the LLM, not the code.

Inspired by Claude Code's architecture:
  - Hierarchical TRADER.md loading (global → project → local override)
  - 3-level permission system (trust boundary → mode → per-tool rules)
  - Tool flags: isReadOnly, isDestructive, isConcurrencySafe
  - Isolated provider instance per harness call

## TRADER.md loading order (like CLAUDE.md in Claude Code)
  ~/.trading_platform/TRADER.md   — global profile (capital, risk tolerance)
  ./TRADER.md                     — project-level rules (this strategy)
  ./TRADER.local.md               — local override (today's watchlist, not committed)

Later files in the chain extend/override earlier ones.

## Permission modes (HARNESS_MODE env var)
  prompt (default) — ask user before any destructive tool (execute_trade)
  plan             — run all analysis, show full plan, confirm once at end
  auto             — never ask; paper mode only, blocks live orders entirely

## Tool permission levels (set on each tool via ToolRegistry.register)
  permission="auto"  — run freely (all read-only analysis tools)
  permission="ask"   — always prompt (execute_trade, any live-state mutation)
  permission="deny"  — blocked entirely (place_order is not in registry at all)

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

# ── Permission modes ──────────────────────────────────────────

HARNESS_MODE_PROMPT = "prompt"  # ask before destructive tools (default)
HARNESS_MODE_PLAN = "plan"  # analyse first, confirm once at end
HARNESS_MODE_AUTO = "auto"  # never ask; paper only


def harness_mode() -> str:
    """Return current HARNESS_MODE from env. Defaults to 'prompt'."""
    return os.environ.get("HARNESS_MODE", HARNESS_MODE_PROMPT).lower()


# ── Hierarchical TRADER.md paths ──────────────────────────────

TRADER_MD_GLOBAL = Path.home() / ".trading_platform" / "TRADER.md"
TRADER_MD_PROJECT = Path.cwd() / "TRADER.md"
TRADER_MD_LOCAL = Path.cwd() / "TRADER.local.md"

# Canonical path for save_trader_context (always writes global)
TRADER_MD_PATH = TRADER_MD_GLOBAL


# ── Broker helper (isolated so tests can patch it) ────────────


def _get_connected_broker():
    """Return the currently connected broker. Raises if none."""
    from brokers.session import get_broker

    return get_broker()


# ── TRADER.md: build ─────────────────────────────────────────


def _build_trader_context() -> str:
    """
    Auto-generate TRADER.md content from env, broker profile, and trade memory.
    Called when no TRADER.md files exist on disk.
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

    broker_name = "PAPER"
    try:
        profile = _get_connected_broker().get_profile()
        broker_name = profile.broker
    except Exception:
        pass

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


# ── TRADER.md: hierarchical load (like CLAUDE.md in Claude Code) ──


def _load_trader_context(
    global_path: Path | None = None,
    project_path: Path | None = None,
    local_path: Path | None = None,
) -> str:
    """
    Load TRADER.md context using a hierarchical chain (like Claude Code's CLAUDE.md):

      1. ~/.trading_platform/TRADER.md  — global profile
      2. ./TRADER.md                    — project-level rules (extends global)
      3. ./TRADER.local.md              — local override (extends project, not committed)

    Later files are appended to/override earlier ones.
    Falls back to auto-generated content if no files exist.
    """
    g = global_path if global_path is not None else TRADER_MD_GLOBAL
    p = project_path if project_path is not None else TRADER_MD_PROJECT
    lo = local_path if local_path is not None else TRADER_MD_LOCAL

    sections: list[str] = []

    if g.exists():
        sections.append(g.read_text(encoding="utf-8").strip())
    if p.exists():
        sections.append(p.read_text(encoding="utf-8").strip())
    if lo.exists():
        sections.append(lo.read_text(encoding="utf-8").strip())

    if sections:
        return "\n\n".join(sections)

    # Nothing on disk — auto-generate
    return _build_trader_context()


def save_trader_context(content: str) -> None:
    """Write the global TRADER.md to disk. Creates parent directories if needed."""
    TRADER_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADER_MD_PATH.write_text(content, encoding="utf-8")


# ── System prompt ─────────────────────────────────────────────


def _build_harness_system_prompt(trader_context: str) -> str:
    """Build harness-specific system prompt with injected TRADER.md context."""
    today = date.today().strftime("%d %B %Y")
    mode = os.environ.get("TRADING_MODE", "PAPER")
    hmode = harness_mode()

    execution_rules = {
        HARNESS_MODE_PROMPT: (
            "Ask for confirmation before calling execute_trade. "
            "The tool itself will present a preview and prompt."
        ),
        HARNESS_MODE_PLAN: (
            "Complete ALL analysis first. Then present the full trade plan "
            "and ask ONCE for confirmation before calling execute_trade."
        ),
        HARNESS_MODE_AUTO: (
            "Do NOT call execute_trade. This session is read-only analysis only. "
            "Present your recommendation but do not execute any orders."
        ),
    }.get(hmode, "Ask for confirmation before calling execute_trade.")

    return f"""You are a trading harness for Indian financial markets (NSE/BSE/NFO).
Today is {today}. Trading mode: {mode}. Harness mode: {hmode}.

You have access to 45+ tools covering market data, technical analysis, fundamental analysis,
options analytics, broker operations, and trade execution. You decide which tools to call,
in what order, based on what the user asks. No fixed pipeline — be adaptive.

## Execution rules ({hmode} mode)
{execution_rules}

## How you work
- Call tools until you have enough data to give a confident verdict
- Show the numbers: RSI, MACD, PE, OI, IV — never say "technicals are strong"
- Give a clear BUY / SELL / WAIT verdict with specific entry / SL / target levels
- Never call place_order directly — always use execute_trade

## Trader Context
{trader_context}"""


# ── execute_trade tool ────────────────────────────────────────


def _register_execute_tool(registry, broker) -> None:
    """
    Add execute_trade to the registry as a DESTRUCTIVE tool (permission="ask").
    Routes through trade_executor.py's confirmation gate — never bypasses it.
    Blocked entirely when HARNESS_MODE=auto.
    """
    mode = harness_mode()
    if mode == HARNESS_MODE_AUTO:
        # In auto mode, register the tool as denied so the LLM can't call it
        registry.register(
            name="execute_trade",
            description="Trade execution is disabled in auto mode.",
            parameters={"type": "object", "properties": {}},
            fn=lambda **_: {"error": "execute_trade is disabled in auto mode."},
            is_destructive=True,
            permission="deny",
        )
        return

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
                "symbol": {"type": "string", "description": "Stock symbol e.g. RELIANCE, TCS"},
                "action": {"type": "string", "description": "BUY or SELL"},
                "quantity": {"type": "integer", "description": "Number of shares or lots"},
                "exchange": {"type": "string", "description": "NSE | BSE | NFO (default: NSE)"},
                "product": {
                    "type": "string",
                    "description": "CNC (delivery) | MIS (intraday) | NRML (F&O) — default: CNC",
                },
                "order_type": {
                    "type": "string",
                    "description": "MARKET | LIMIT | SL | SL-M — default: MARKET",
                },
                "price": {"type": "number", "description": "Limit price (for LIMIT/SL orders)"},
                "stop_loss": {"type": "number", "description": "Stop-loss price"},
                "target": {"type": "number", "description": "Target price"},
            },
            "required": ["symbol", "action", "quantity"],
        },
        fn=_execute_trade,
        is_destructive=True,
        is_read_only=False,
        is_concurrency_safe=False,
        permission="ask",
    )


# ── Provider factory (isolated for testability) ───────────────


def _make_provider(registry, system_prompt: str):
    """
    Build a fresh LLM provider with the given registry and harness system prompt.
    get_provider() builds its own prompt internally; we override after construction.
    """
    provider = get_provider(registry=registry)
    provider.system_prompt = system_prompt
    return provider


# ── Internal chat wrapper (isolated for testability) ──────────


def _get_agent_chat(provider, query: str) -> str:
    """Run one chat turn on the provider and return the response."""
    return provider.chat([{"role": "user", "content": query}], stream=True)


# ── Main entry point ──────────────────────────────────────────


def run(query: str, broker=None) -> str:
    """
    Run the trading harness for a natural language query.

    Creates an isolated provider (separate from the main `ai` agent history)
    with the harness system prompt and merged TRADER.md context.

    Args:
        query:  Natural language question or instruction from the user.
        broker: Connected broker instance (or None — disables execute_trade).

    Returns:
        Final response text from the LLM.
    """
    from agent.tools import build_registry

    registry = build_registry()

    if broker is not None:
        _register_execute_tool(registry, broker)

    trader_context = _load_trader_context()
    system_prompt = _build_harness_system_prompt(trader_context)

    provider = _make_provider(registry=registry, system_prompt=system_prompt)

    mode_label = {
        HARNESS_MODE_PROMPT: "[cyan]prompt[/cyan]",
        HARNESS_MODE_PLAN: "[yellow]plan[/yellow]",
        HARNESS_MODE_AUTO: "[green]auto (read-only)[/green]",
    }.get(harness_mode(), harness_mode())

    console.print()
    console.rule(f"[bold cyan]Trading Harness[/bold cyan] · {mode_label}", style="cyan")

    response = _get_agent_chat(provider, query)

    console.rule(style="cyan")
    return response or ""
