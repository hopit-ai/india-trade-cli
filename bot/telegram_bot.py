"""
bot/telegram_bot.py
───────────────────
Telegram bot for the India Trade CLI platform.

Commands:
  /start          — Welcome + command list
  /quote SYM      — Live quote for a stock
  /analyze SYM    — Quick analysis (scorecard, no full debate)
  /brief          — Morning market brief
  /flows          — FII/DII flow intelligence
  /earnings       — Upcoming earnings calendar
  /events         — Event-driven strategy recommendations
  /macro          — USD/INR, crude, gold snapshot
  /alert SYM above 2800  — Set a price alert
  /alerts         — List active alerts
  /memory         — Recent trade analyses
  /pnl            — Portfolio P&L summary
  /help           — Command reference

Also receives push notifications:
  - Alert triggers (price/technical/conditional)
  - Morning brief (scheduled, if configured)

Setup:
  1. Create a bot via @BotFather on Telegram → get the token
  2. Save: credentials setup → Telegram Bot Token
  3. Start: `telegram` command in REPL, or `python -m bot.telegram_bot`

Install: pip install python-telegram-bot
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress chatty third-party loggers at import time so they never
# flood the REPL regardless of when the bot thread starts.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("market.websocket").setLevel(logging.WARNING)
logging.getLogger("market").setLevel(logging.WARNING)


class _BotThreadFilter(logging.Filter):
    """
    Attached to the root logger's handlers.
    Only allows log records from the main thread (the REPL) through.
    All background threads (telegram-bot, executor pool, websocket, etc.)
    are silenced so their output never appears in the REPL.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return threading.current_thread().name == "MainThread"


class _BotThreadFileWrapper:
    """
    Wraps any file-like object and suppresses all writes from the
    telegram-bot thread at call time.

    Used in two places:
      1. Replaces sys.stdout so plain print() calls are silenced.
      2. Replaces the _file attribute on every existing Rich Console
         instance so that console.print() / progress spinners are
         silenced too (Rich stores a direct file reference at init time,
         so replacing sys.stdout alone is not enough).

    Thread-safe: the thread check happens at write time.
    """

    _bot_patched = True  # sentinel to avoid double-wrapping

    def __init__(self, wrapped: object) -> None:
        self._wrapped = wrapped

    def _is_bot_thread(self) -> bool:
        # Only the main thread (REPL) is allowed to produce terminal output.
        # All other threads (telegram-bot, executor pool, websocket, etc.)
        # are silenced.
        return threading.current_thread().name != "MainThread"

    def write(self, s: str) -> int:
        if self._is_bot_thread() or self._wrapped is None:
            return len(s) if isinstance(s, str) else 0
        return self._wrapped.write(s)  # type: ignore[union-attr]

    def flush(self) -> None:
        if not self._is_bot_thread() and self._wrapped is not None:
            self._wrapped.flush()  # type: ignore[union-attr]

    def __getattr__(self, name: str) -> object:
        return getattr(self._wrapped, name)


# ── Telegram → REPL status badge ─────────────────────────────

import functools
from bot.status import set_active, clear_active


def _track_command(func):
    """Decorator that sets/clears the REPL status badge around a handler."""

    @functools.wraps(func)
    async def wrapper(update, context):
        cmd_text = update.message.text if update.message else func.__name__
        set_active(cmd_text)
        try:
            return await func(update, context)
        finally:
            clear_active()

    return wrapper


# ── Lazy imports to avoid startup overhead ───────────────────


def _get_telegram():
    try:
        from telegram import Update, Bot
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            filters,
        )

        return (
            Update,
            Bot,
            ApplicationBuilder,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            filters,
        )
    except ImportError:
        raise RuntimeError(
            "python-telegram-bot not installed. Run:\n  pip install python-telegram-bot"
        )


# ── Bot token management ─────────────────────────────────────


def _get_bot_token() -> str:
    """Get Telegram bot token from keychain or env."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            from config.credentials import _kr_get

            token = _kr_get("TELEGRAM_BOT_TOKEN") or ""
        except Exception:
            pass
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN not set.\n"
            "1. Talk to @BotFather on Telegram → create a bot → copy the token\n"
            "2. Run: credentials setup → enter Telegram Bot Token\n"
            "   Or set TELEGRAM_BOT_TOKEN in .env"
        )
    return token


# Chat ID for push notifications (set on first /start)
_chat_id: Optional[int] = None

# Background bot thread — kept here to prevent starting duplicates
_bot_thread: Optional[threading.Thread] = None

# Thread-local flag: set to True on any thread that should produce no output.
# Used to silence executor threads spawned by run_in_executor during analysis,
# which have a different name from "telegram-bot" and would otherwise bypass
# the _BotThreadFileWrapper name check.
_suppress_output = threading.local()
_CHAT_ID_FILE = os.path.expanduser("~/.trading_platform/telegram_chat_id")


def _save_chat_id(chat_id: int) -> None:
    global _chat_id
    _chat_id = chat_id
    try:
        os.makedirs(os.path.dirname(_CHAT_ID_FILE), exist_ok=True)
        with open(_CHAT_ID_FILE, "w") as f:
            f.write(str(chat_id))
    except Exception:
        pass


def _load_chat_id() -> Optional[int]:
    global _chat_id
    if _chat_id:
        return _chat_id
    try:
        with open(_CHAT_ID_FILE) as f:
            _chat_id = int(f.read().strip())
            return _chat_id
    except Exception:
        return None


# ── Command Handlers ─────────────────────────────────────────


async def cmd_start(update, context) -> None:
    """Handle /start command."""
    _save_chat_id(update.effective_chat.id)
    await update.message.reply_text(
        "Welcome to India Trade CLI Bot!\n\n"
        "Commands:\n"
        "/quote RELIANCE — live price\n"
        "/analyze RELIANCE — full analysis (3-4 min)\n"
        "/deepanalyze RELIANCE — deep LLM analysis (7-10 min)\n"
        "/brief — morning market brief\n"
        "/flows — FII/DII flow signals\n"
        "/earnings — upcoming results\n"
        "/events — event strategies\n"
        "/macro — USD/INR, crude, gold\n"
        "/alert RELIANCE above 2800\n"
        "/alerts — list alerts\n"
        "/memory — recent analyses\n"
        "/pnl — portfolio P&L\n"
        "/help — this message\n\n"
        "Alerts will be pushed here automatically."
    )


async def cmd_help(update, context) -> None:
    await cmd_start(update, context)


async def cmd_quote(update, context) -> None:
    """Handle /quote SYMBOL."""
    if not context.args:
        await update.message.reply_text("Usage: /quote RELIANCE")
        return

    symbol = context.args[0].upper()
    try:
        from market.quotes import get_quote

        quotes = get_quote([f"NSE:{symbol}"])
        q = quotes.get(f"NSE:{symbol}")
        if q and q.last_price:
            chg_emoji = "📈" if (q.change or 0) >= 0 else "📉"
            await update.message.reply_text(
                f"{chg_emoji} {symbol}\n"
                f"LTP: ₹{q.last_price:,.2f}\n"
                f"Change: {q.change:+.2f} ({q.change_pct:+.2f}%)\n"
                f"Open: ₹{q.open:,.2f} | High: ₹{q.high:,.2f} | Low: ₹{q.low:,.2f}\n"
                f"Volume: {q.volume:,}"
            )
        else:
            await update.message.reply_text(f"Could not get quote for {symbol}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_analyze(update, context) -> None:
    """Handle /analyze SYMBOL — full multi-agent analysis, same as CLI."""
    if not context.args:
        await update.message.reply_text("Usage: /analyze RELIANCE")
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(
        f"🔍 Running full analysis on {symbol}...\n"
        f"(7 analysts + debate + synthesis — takes 3-4 min)"
    )

    def _run_analysis() -> tuple:
        """Synchronous full pipeline — run in executor to avoid blocking event loop."""
        _suppress_output.active = True
        # Log to file — stdout and logging are both suppressed on this thread
        import tempfile
        import pathlib

        _logfile = pathlib.Path(tempfile.gettempdir()) / "tg_analyze.log"

        def _log(msg):  # noqa: E731
            with open(_logfile, "a") as f:
                f.write(f"{msg}\n")

        try:
            _log(f"Starting analysis for {symbol}")
            from agent.tools import build_registry
            from agent.multi_agent import MultiAgentAnalyzer, compute_scorecard
            from agent.core import get_provider

            os.environ["_CLI_BATCH_MODE"] = "1"
            registry = build_registry()
            _log("Registry built")
            provider = get_provider()
            _log(f"Provider: {provider}")
            analyzer = MultiAgentAnalyzer(registry, provider, verbose=False)

            # Run all 7 analysts
            reports = []
            for i, a in enumerate(analyzer.analysts):
                try:
                    _log(f"Analyst {i + 1}/{len(analyzer.analysts)}: {a.__class__.__name__}")
                    reports.append(a.analyze(symbol))
                except Exception as ex:
                    _log(f"Analyst {a.__class__.__name__} failed: {ex}")

            _log(f"Got {len(reports)} reports, computing scorecard")
            scorecard = compute_scorecard(reports)

            verdict_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}
            analyst_lines = []
            for r in reports:
                if not r.error:
                    e = verdict_emoji.get(r.verdict, "⚪")
                    analyst_lines.append(f"{e} {r.analyst}: {r.verdict} ({r.confidence}%)")

            # Run debate + synthesis
            _log("Running debate")
            debate = analyzer._run_debate(symbol, "NSE", reports)
            _log("Running synthesis")
            synthesis = analyzer._run_synthesis(symbol, "NSE", reports, debate)
            _log("Pipeline complete")

            # ── Message 1: analyst scorecard ─────────────────────
            score_emoji = verdict_emoji.get(scorecard.verdict, "🟡")
            msg1 = (
                f"📊 {symbol} — Full Analysis\n\n"
                + "\n".join(analyst_lines)
                + f"\n\n{score_emoji} Scorecard: {scorecard.verdict} ({scorecard.weighted_total:+.1f})\n"
                f"Agreement: {scorecard.agreement:.0f}%"
            )
            if scorecard.conflicts:
                msg1 += f"\nConflicts: {', '.join(scorecard.conflicts)}"

            # ── Message 2: debate ─────────────────────────────────
            msg2 = ""
            if debate:
                parts = ["🥊 Bull vs Bear Debate\n"]
                if debate.bull_argument:
                    parts.append(f"🟢 BULL (Round 1)\n{debate.bull_argument.strip()[:800]}")
                if debate.bear_argument:
                    parts.append(f"\n🔴 BEAR (Round 1)\n{debate.bear_argument.strip()[:800]}")
                if debate.bull_rebuttal:
                    parts.append(f"\n🟢 BULL (Rebuttal)\n{debate.bull_rebuttal.strip()[:600]}")
                if debate.bear_rebuttal:
                    parts.append(f"\n🔴 BEAR (Rebuttal)\n{debate.bear_rebuttal.strip()[:600]}")
                if debate.facilitator:
                    parts.append(f"\n🎙 Facilitator\n{debate.facilitator.strip()[:600]}")
                if debate.winner:
                    win_e = "🟢" if debate.winner == "BULL" else "🔴"
                    parts.append(f"\nVerdict: {win_e} {debate.winner} prevailed")
                msg2 = "\n".join(parts)[:3800]

            # ── Message 3: synthesis ──────────────────────────────
            synth_text = (synthesis or "").strip()[:3800]
            msg3 = f"🧠 Synthesis\n\n{synth_text}" if synth_text else ""

            os.environ.pop("_CLI_BATCH_MODE", None)
            _log(f"Returning msgs: {len(msg1)} / {len(msg2)} / {len(msg3)} chars")
            return msg1, msg2, msg3

        except Exception as e:
            os.environ.pop("_CLI_BATCH_MODE", None)
            import traceback

            _log(f"FAILED: {e}\n{traceback.format_exc()}")
            return f"Analysis failed: {e}", "", ""
        finally:
            _suppress_output.active = False

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_analysis),
            timeout=300,  # 5 minute hard timeout
        )
        msg1, msg2, msg3 = (
            result if isinstance(result, tuple) and len(result) == 3 else (str(result), "", "")
        )
        # Send as plain text — LLM output can contain any characters that
        # would break Telegram's HTML/Markdown parsers.
        # Telegram limit is 4096 chars per message.
        if msg1:
            await update.message.reply_text(msg1[:4000])
        if msg2:
            await update.message.reply_text(msg2[:4000])
        if msg3:
            await update.message.reply_text(msg3[:4000])
        if not msg1:
            await update.message.reply_text("Analysis completed but produced no output.")
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Analysis timed out after 5 minutes. Try again later.")
    except Exception as e:
        err = str(e)[:500]
        await update.message.reply_text(f"Analysis failed: {err}")


async def cmd_deepanalyze(update, context) -> None:
    """Handle /deepanalyze SYMBOL — full LLM deep analysis (11 calls)."""
    if not context.args:
        await update.message.reply_text("Usage: /deepanalyze RELIANCE")
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(
        f"🔬 Running deep analysis on {symbol}...\n"
        f"(11 LLM calls — every analyst uses AI — takes 7-10 min)"
    )

    def _run_deep() -> tuple:
        _suppress_output.active = True
        import tempfile
        import pathlib

        _logfile = pathlib.Path(tempfile.gettempdir()) / "tg_deepanalyze.log"

        def _log(msg):
            with open(_logfile, "a") as f:
                f.write(f"{msg}\n")

        try:
            _log(f"Starting deep analysis for {symbol}")
            from agent.tools import build_registry
            from agent.deep_agent import DeepAnalyzer
            from agent.core import get_provider

            os.environ["_CLI_BATCH_MODE"] = "1"
            registry = build_registry()
            provider = get_provider()
            deep = DeepAnalyzer(registry, provider, verbose=False)

            # Run the full pipeline — returns a text report
            full_report = deep.analyze(symbol)
            _log(f"Deep analysis complete, report length: {len(full_report or '')}")

            if not full_report:
                return "Deep analysis produced no output.", "", ""

            # Split into 3 telegram-friendly messages
            # Message 1: analyst scorecard section
            # Message 2: debate section
            # Message 3: synthesis section
            parts = full_report.split("=" * 60)

            msg1 = f"🔬 {symbol} — Deep Analysis (Full LLM)\n\n"
            msg2 = ""
            msg3 = ""

            # Parse sections from the report
            for i, part in enumerate(parts):
                stripped = part.strip()
                if stripped.startswith("LLM ANALYST REPORTS"):
                    # Next section is the analyst reports
                    if i + 1 < len(parts):
                        msg1 += parts[i + 1].strip()[:3800]
                elif stripped.startswith("BULL/BEAR DEBATE"):
                    if i + 1 < len(parts):
                        msg2 = f"🥊 Deep Debate\n\n{parts[i + 1].strip()[:3800]}"
                elif stripped.startswith("FUND MANAGER SYNTHESIS"):
                    if i + 1 < len(parts):
                        msg3 = f"🧠 Deep Synthesis\n\n{parts[i + 1].strip()[:3800]}"

            # Fallback: if parsing didn't split well, send as chunks
            if not msg1 or msg1 == f"🔬 {symbol} — Deep Analysis (Full LLM)\n\n":
                msg1 = full_report[:4000]
                msg2 = full_report[4000:8000] if len(full_report) > 4000 else ""
                msg3 = full_report[8000:12000] if len(full_report) > 8000 else ""

            os.environ.pop("_CLI_BATCH_MODE", None)
            return msg1, msg2, msg3

        except Exception as e:
            os.environ.pop("_CLI_BATCH_MODE", None)
            import traceback

            _log(f"FAILED: {e}\n{traceback.format_exc()}")
            return f"Deep analysis failed: {e}", "", ""
        finally:
            _suppress_output.active = False

    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_deep),
            timeout=600,  # 10 minute timeout for deep analysis
        )
        msg1, msg2, msg3 = (
            result if isinstance(result, tuple) and len(result) == 3 else (str(result), "", "")
        )
        if msg1:
            await update.message.reply_text(msg1[:4000])
        if msg2:
            await update.message.reply_text(msg2[:4000])
        if msg3:
            await update.message.reply_text(msg3[:4000])
        if not msg1:
            await update.message.reply_text("Deep analysis completed but produced no output.")
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Deep analysis timed out after 10 minutes.")
    except Exception as e:
        err = str(e)[:500]
        await update.message.reply_text(f"Deep analysis failed: {err}")


async def cmd_brief(update, context) -> None:
    """Handle /brief — market snapshot."""
    try:
        from market.indices import get_market_snapshot

        snap = get_market_snapshot()
        nifty = snap.nifty
        vix = snap.vix

        n_emoji = "📈" if nifty.change_pct >= 0 else "📉"
        await update.message.reply_text(
            f"🇮🇳 Market Brief\n\n"
            f"{n_emoji} NIFTY: {nifty.ltp:,.0f} ({nifty.change_pct:+.2f}%)\n"
            f"{'📈' if snap.banknifty.change_pct >= 0 else '📉'} BANKNIFTY: {snap.banknifty.ltp:,.0f} ({snap.banknifty.change_pct:+.2f}%)\n"
            f"⚡ VIX: {vix.ltp:.1f}\n"
            f"\nPosture: {snap.posture}\n{snap.posture_reason}"
        )
    except Exception as e:
        await update.message.reply_text(f"Brief failed: {e}")


async def cmd_flows(update, context) -> None:
    """Handle /flows — FII/DII intelligence."""
    try:
        from market.flow_intel import get_flow_analysis

        a = get_flow_analysis()
        await update.message.reply_text(
            f"💰 FII/DII Flows\n\n"
            f"FII today: {a.fii_net_today:+,.0f} Cr\n"
            f"DII today: {a.dii_net_today:+,.0f} Cr\n"
            f"FII 5-day: {a.fii_5d_net:+,.0f} Cr\n"
            f"FII streak: {a.fii_streak} days\n"
            f"{'⚠️ Divergence: ' + a.divergence_type if a.divergence else ''}\n"
            f"\nSignal: {a.signal} ({a.confidence}%)\n"
            f"{a.signal_reason}"
        )
    except Exception as e:
        await update.message.reply_text(f"Flow data failed: {e}")


async def cmd_earnings(update, context) -> None:
    """Handle /earnings."""
    try:
        from market.earnings import get_earnings_calendar, _current_quarter

        syms = [a.upper() for a in context.args] if context.args else None
        calendar = get_earnings_calendar(syms)

        if not calendar:
            await update.message.reply_text("No upcoming earnings found.")
            return

        lines = [f"📅 Earnings — {_current_quarter()}\n"]
        for e in calendar[:10]:
            move = f" (±{e.avg_move:.1f}%)" if e.avg_move else ""
            lines.append(f"  {e.symbol}: {e.result_date}{move}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Earnings failed: {e}")


async def cmd_events(update, context) -> None:
    """Handle /events."""
    try:
        from engine.event_strategies import get_event_strategies

        strategies = get_event_strategies(days_ahead=7)

        if not strategies:
            await update.message.reply_text("No events in next 7 days.")
            return

        lines = ["📆 Event Strategies (7 days)\n"]
        for s in strategies:
            risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(s.risk_level, "⚪")
            lines.append(f"{risk_emoji} {s.event} (in {s.days_away}d)")
            lines.append(f"   {s.strategy[:80]}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Events failed: {e}")


async def cmd_macro(update, context) -> None:
    """Handle /macro."""
    try:
        from market.macro import get_macro_snapshot

        snap = get_macro_snapshot()
        lines = ["🌍 Macro Snapshot\n"]
        if snap.usdinr:
            lines.append(
                f"USD/INR: {snap.usdinr:.2f} ({snap.usdinr_change:+.2f}%)"
                if snap.usdinr_change
                else f"USD/INR: {snap.usdinr:.2f}"
            )
        if snap.crude_oil:
            lines.append(
                f"Crude: ${snap.crude_oil:.1f}/bbl ({snap.crude_change:+.1f}%)"
                if snap.crude_change
                else f"Crude: ${snap.crude_oil:.1f}"
            )
        if snap.gold:
            lines.append(
                f"Gold: ${snap.gold:.0f}/oz ({snap.gold_change:+.1f}%)"
                if snap.gold_change
                else f"Gold: ${snap.gold:.0f}"
            )
        if snap.us_10y:
            lines.append(f"US 10Y: {snap.us_10y:.2f}%")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Macro failed: {e}")


async def cmd_alert(update, context) -> None:
    """Handle /alert SYMBOL above/below PRICE."""
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /alert RELIANCE above 2800")
        return

    try:
        from engine.alerts import alert_manager

        symbol = context.args[0].upper()
        condition = context.args[1].upper()
        threshold = float(context.args[2])
        alert = alert_manager.add_price_alert(symbol, condition, threshold)
        await update.message.reply_text(f"✅ Alert set: {alert.describe()} (ID: {alert.id})")
    except Exception as e:
        await update.message.reply_text(f"Alert failed: {e}")


async def cmd_alerts(update, context) -> None:
    """Handle /alerts — list active alerts."""
    try:
        from engine.alerts import alert_manager

        active = [a for a in alert_manager._alerts if not a.triggered]
        if not active:
            await update.message.reply_text("No active alerts.")
            return
        lines = ["🔔 Active Alerts\n"]
        for a in active:
            lines.append(f"  [{a.id}] {a.describe()}")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Alerts failed: {e}")


async def cmd_memory(update, context) -> None:
    """Handle /memory — recent analyses."""
    try:
        from engine.memory import trade_memory

        recent = list(reversed(trade_memory._records[-5:]))
        if not recent:
            await update.message.reply_text("No analyses stored yet.")
            return
        lines = ["📝 Recent Analyses\n"]
        for r in recent:
            outcome = f" → {r.outcome}" if r.outcome else ""
            lines.append(
                f"  [{r.id}] {r.timestamp[:10]} {r.symbol}: {r.verdict} ({r.confidence}%){outcome}"
            )
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Memory failed: {e}")


async def cmd_pnl(update, context) -> None:
    """Handle /pnl — portfolio summary."""
    try:
        from engine.portfolio import get_portfolio_summary

        summary = get_portfolio_summary()
        pnl_emoji = "📈" if summary.total_pnl >= 0 else "📉"
        await update.message.reply_text(
            f"💼 Portfolio\n\n"
            f"Value: ₹{summary.total_value:,.0f}\n"
            f"{pnl_emoji} P&L: ₹{summary.total_pnl:+,.0f}\n"
            f"Day P&L: ₹{summary.day_pnl:+,.0f}\n"
            f"Risk: {summary.risk.risk_rating} ({summary.risk.deployment_pct:.0f}% deployed)"
        )
    except Exception as e:
        await update.message.reply_text(f"Portfolio failed: {e}")


async def cmd_unknown(update, context) -> None:
    """Handle unknown messages."""
    await update.message.reply_text("Unknown command. Type /help for available commands.")


# ── Token validation ─────────────────────────────────────────


def validate_token(token: str) -> tuple[bool, str]:
    """
    Validate a bot token by calling the Telegram getMe API.

    Returns:
        (True,  "@username (Bot Name)")  on success
        (False, "error description")     on failure
    """
    try:
        import httpx

        resp = httpx.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            info = data["result"]
            return True, f"@{info.get('username', '?')} ({info.get('first_name', '?')})"
        return False, data.get("description", "Unknown error from Telegram API")
    except Exception as e:
        return False, f"Could not reach Telegram: {e}"


def send_test_push(chat_id: Optional[int] = None, token: Optional[str] = None) -> bool:
    """
    Send a test message to verify the full setup is working.
    Uses the provided chat_id/token or falls back to stored values.
    Returns True if the message was delivered successfully.
    """
    cid = chat_id or _load_chat_id()
    if not cid:
        return False
    try:
        tok = token or _get_bot_token()
    except Exception:
        return False
    try:
        import httpx

        resp = httpx.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={
                "chat_id": cid,
                "text": (
                    "✅ India Trade CLI connected!\n\n"
                    "You'll receive notifications here for:\n"
                    "  • Price alert triggers\n"
                    "  • Paper trade executions\n"
                    "  • Strategy signals\n\n"
                    "Try /help to see all available commands."
                ),
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        return resp.json().get("ok", False)
    except Exception:
        return False


def wait_for_start(timeout: int = 120) -> bool:
    """
    Wait (poll) until the user sends /start to the bot, which saves the chat ID.
    The bot must already be running in the background before calling this.

    Args:
        timeout: Maximum seconds to wait (default 120).

    Returns:
        True if the chat ID was received within the timeout, False otherwise.
    """
    import time

    for _ in range(timeout):
        if _load_chat_id():
            return True
        time.sleep(1)
    return False


def run_setup_wizard() -> None:
    """
    Full end-to-end interactive Telegram setup wizard.

    Flow:
      Step 1 — Collect / confirm bot token
      Step 2 — Validate token with Telegram API
      Step 3 — Start bot, wait for user to send /start, send test message
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()

    console.print("\n[bold cyan]━━━ Telegram Bot Setup ━━━[/bold cyan]")
    console.print("[dim]Connects your bot for push notifications and Telegram commands.[/dim]\n")

    # ── Step 1: Token ─────────────────────────────────────────
    console.print("[bold]Step 1 of 3 — Bot Token[/bold]")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            from config.credentials import _kr_get

            token = _kr_get("TELEGRAM_BOT_TOKEN") or ""
        except Exception:
            pass

    if token:
        console.print("  [green]✓ Token found in keychain/env[/green]")
    else:
        console.print(
            "\n  No token found. Here's how to create one:\n\n"
            "    1. Open Telegram → search [bold cyan]@BotFather[/bold cyan]\n"
            "    2. Send [cyan]/newbot[/cyan]\n"
            "    3. Choose a name    e.g. [dim]My Trade Bot[/dim]\n"
            "    4. Choose a username ending in [bold]bot[/bold]    e.g. [dim]mytrade_bot[/dim]\n"
            "    5. Copy the token BotFather gives you\n"
        )
        token = Prompt.ask("  Paste your bot token", password=True).strip()
        if not token:
            console.print("[red]No token provided. Setup cancelled.[/red]")
            return

        try:
            from config.credentials import _kr_set

            if _kr_set("TELEGRAM_BOT_TOKEN", token):
                os.environ["TELEGRAM_BOT_TOKEN"] = token
                console.print("  [green]✓ Token saved to keychain[/green]")
            else:
                os.environ["TELEGRAM_BOT_TOKEN"] = token
                console.print(
                    "  [yellow]⚠  Keychain unavailable — token active for this session only.[/yellow]"
                )
        except Exception:
            os.environ["TELEGRAM_BOT_TOKEN"] = token

    # ── Step 2: Validate ──────────────────────────────────────
    console.print("\n[bold]Step 2 of 3 — Validate Token[/bold]")
    console.print("  Checking with Telegram...")

    ok, info = validate_token(token)
    if not ok:
        console.print(
            f"  [red]✗ Token rejected: {info}[/red]\n"
            "  [dim]Double-check the token from @BotFather and run [bold]telegram setup[/bold] again.[/dim]"
        )
        return

    console.print(f"  [green]✓ Bot verified: {info}[/green]")

    # ── Step 3: Connect chat ───────────────────────────────────
    console.print("\n[bold]Step 3 of 3 — Connect Your Chat[/bold]")

    existing = _load_chat_id()
    if existing:
        console.print(f"  [green]✓ Chat already connected (ID: {existing})[/green]")
        console.print("  Sending test notification...")
        if send_test_push(existing, token):
            console.print("  [green]✓ Test message sent! Check your Telegram.[/green]")
        else:
            console.print("  [yellow]⚠  Message failed — check the bot isn't blocked.[/yellow]")
    else:
        bot_handle = info.split("(")[0].strip()  # e.g. "@mytrade_bot"
        console.print(
            f"\n  Open Telegram and send [bold]/start[/bold] to your bot [cyan]{bot_handle}[/cyan]\n"
            "  Waiting up to 2 minutes...\n"
        )

        run_bot_background()

        if wait_for_start(timeout=120):
            chat_id = _load_chat_id()
            console.print(f"  [green]✓ Connected! (Chat ID: {chat_id})[/green]")
            console.print("  Sending test notification...")
            if send_test_push(chat_id, token):
                console.print("  [green]✓ Test message delivered. Check your Telegram.[/green]")
            else:
                console.print(
                    "  [yellow]⚠  Bot connected but test message failed — try /start again.[/yellow]"
                )
        else:
            console.print(
                "\n  [yellow]⏱  Timed out — didn't receive /start within 2 minutes.[/yellow]\n"
                "  The bot is still running in the background.\n"
                "  [dim]Send /start to your bot whenever you're ready.[/dim]"
            )
            return

    console.print(
        "\n[bold green]✓  Telegram setup complete![/bold green]\n"
        "[dim]The bot will push alerts, paper trade signals, and strategy\n"
        "notifications here automatically. Use [bold]telegram[/bold] in the\n"
        "REPL to restart the bot in future sessions.[/dim]\n"
    )


# ── Push Notifications ───────────────────────────────────────


def send_push(message: str) -> None:
    """
    Send a push notification to the configured Telegram chat.
    Called from alerts, morning brief scheduler, etc.
    Non-blocking — runs in a background thread.
    """
    chat_id = _load_chat_id()
    if not chat_id:
        return

    try:
        token = _get_bot_token()
    except Exception:
        return

    def _send():
        try:
            import httpx

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            httpx.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def push_alert(alert_desc: str) -> None:
    """Push an alert trigger notification."""
    send_push(f"🔔 ALERT TRIGGERED\n\n{alert_desc}")


def push_brief(brief_text: str) -> None:
    """Push a morning brief."""
    send_push(f"🇮🇳 Morning Brief\n\n{brief_text}")


# ── Alert Integration ────────────────────────────────────────


def patch_alert_manager() -> None:
    """
    Monkey-patch AlertManager._notify to also send Telegram push.
    Call this when the bot starts.
    """
    try:
        from engine.alerts import alert_manager

        original_notify = alert_manager._notify

        def _patched_notify(alert):
            original_notify(alert)
            push_alert(alert.describe())

        alert_manager._notify = _patched_notify
        logger.debug("Alert manager patched for Telegram push notifications")
    except Exception:
        pass


# ── Bot Runner ───────────────────────────────────────────────


def run_bot() -> None:
    """Start the Telegram bot (blocking — runs the event loop)."""
    Update, Bot, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters = (
        _get_telegram()
    )

    token = _get_bot_token()

    app = ApplicationBuilder().token(token).build()

    # Register command handlers (wrapped with _track_command for REPL badge)
    app.add_handler(CommandHandler("start", _track_command(cmd_start)))
    app.add_handler(CommandHandler("help", _track_command(cmd_help)))
    app.add_handler(CommandHandler("quote", _track_command(cmd_quote)))
    app.add_handler(CommandHandler("analyze", _track_command(cmd_analyze)))
    app.add_handler(CommandHandler("deepanalyze", _track_command(cmd_deepanalyze)))
    app.add_handler(CommandHandler("brief", _track_command(cmd_brief)))
    app.add_handler(CommandHandler("flows", _track_command(cmd_flows)))
    app.add_handler(CommandHandler("earnings", _track_command(cmd_earnings)))
    app.add_handler(CommandHandler("events", _track_command(cmd_events)))
    app.add_handler(CommandHandler("macro", _track_command(cmd_macro)))
    app.add_handler(CommandHandler("alert", _track_command(cmd_alert)))
    app.add_handler(CommandHandler("alerts", _track_command(cmd_alerts)))
    app.add_handler(CommandHandler("memory", _track_command(cmd_memory)))
    app.add_handler(CommandHandler("pnl", _track_command(cmd_pnl)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _track_command(cmd_unknown)))

    # Patch alerts for push notifications
    patch_alert_manager()

    logger.debug("Telegram bot starting...")

    # ── Silence ALL output from this thread ──────────────────────────────
    # 1. Logging filter: blocks log records (httpx, websocket, LLM API, etc.)
    _thread_filter = _BotThreadFilter()
    for _handler in logging.root.handlers:
        _handler.addFilter(_thread_filter)

    # Also silence any logger that adds its own handlers (e.g. FyersDataSocket)
    logging.getLogger("FyersDataSocket").setLevel(logging.CRITICAL)

    # 2. Stdout wrapper: blocks plain print() calls from this thread.
    import sys

    if not isinstance(sys.stdout, _BotThreadFileWrapper):
        sys.stdout = _BotThreadFileWrapper(sys.stdout)

    # 3. Rich Console patch: Rich stores a direct reference to sys.stdout at
    #    Console() creation time, so replacing sys.stdout is not enough.
    #    Walk every live Console instance and wrap its _file attribute too.
    try:
        import gc
        from rich.console import Console as _RichConsole

        for _obj in gc.get_objects():
            if isinstance(_obj, _RichConsole):
                if _obj._file is not None and not getattr(_obj._file, "_bot_patched", False):
                    _obj._file = _BotThreadFileWrapper(_obj._file)
    except Exception:
        pass

    # run_polling() registers OS signal handlers which only work on the main
    # thread. Use the lower-level async API instead — no signal handlers at all.
    async def _run() -> None:
        async with app:
            await app.start()
            await app.updater.start_polling()
            # Keep running until the daemon thread is killed on process exit
            while True:
                await asyncio.sleep(3600)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    except Exception:
        pass
    finally:
        loop.close()


def run_bot_background() -> threading.Thread:
    """Start the bot in a background thread (non-blocking, for REPL integration).
    If the bot is already running, returns the existing thread without starting a new one.
    """
    global _bot_thread
    if _bot_thread is not None and _bot_thread.is_alive():
        logger.debug("Bot thread already running — skipping duplicate start.")
        return _bot_thread
    _bot_thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
    _bot_thread.start()
    return _bot_thread


# ── CLI entry point ──────────────────────────────────────────

if __name__ == "__main__":
    run_bot()
