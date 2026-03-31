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
import json
import logging
import os
import threading
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lazy imports to avoid startup overhead ───────────────────

def _get_telegram():
    try:
        from telegram import Update, Bot
        from telegram.ext import (
            ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters,
        )
        return Update, Bot, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError:
        raise RuntimeError(
            "python-telegram-bot not installed. Run:\n"
            "  pip install python-telegram-bot"
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
        "/analyze RELIANCE — quick analysis\n"
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
    """Handle /analyze SYMBOL — quick scorecard (no full debate)."""
    if not context.args:
        await update.message.reply_text("Usage: /analyze RELIANCE")
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(f"Analyzing {symbol}... (this takes ~30s)")

    try:
        from agent.tools import build_registry
        from agent.multi_agent import (
            TechnicalAnalyst, FundamentalAnalyst, OptionsAnalyst,
            SentimentAnalyst, RiskAnalyst, compute_scorecard,
        )

        os.environ["_CLI_BATCH_MODE"] = "1"
        registry = build_registry()

        analysts = [
            TechnicalAnalyst(registry),
            FundamentalAnalyst(registry),
            OptionsAnalyst(registry),
            SentimentAnalyst(registry),
            RiskAnalyst(registry),
        ]

        reports = []
        for a in analysts:
            try:
                reports.append(a.analyze(symbol))
            except Exception:
                pass

        os.environ.pop("_CLI_BATCH_MODE", None)

        scorecard = compute_scorecard(reports)

        lines = [f"📊 Quick Analysis: {symbol}\n"]
        for r in reports:
            if not r.error:
                emoji = "🟢" if r.verdict == "BULLISH" else "🔴" if r.verdict == "BEARISH" else "🟡"
                lines.append(f"{emoji} {r.analyst}: {r.verdict} ({r.confidence}%)")

        lines.append(f"\nScorecard: {scorecard.verdict} ({scorecard.weighted_total:+.1f})")
        lines.append(f"Agreement: {scorecard.agreement:.0f}%")
        if scorecard.conflicts:
            lines.append(f"Conflicts: {', '.join(scorecard.conflicts)}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Analysis failed: {e}")


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
            lines.append(f"USD/INR: {snap.usdinr:.2f} ({snap.usdinr_change:+.2f}%)" if snap.usdinr_change else f"USD/INR: {snap.usdinr:.2f}")
        if snap.crude_oil:
            lines.append(f"Crude: ${snap.crude_oil:.1f}/bbl ({snap.crude_change:+.1f}%)" if snap.crude_change else f"Crude: ${snap.crude_oil:.1f}")
        if snap.gold:
            lines.append(f"Gold: ${snap.gold:.0f}/oz ({snap.gold_change:+.1f}%)" if snap.gold_change else f"Gold: ${snap.gold:.0f}")
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
            lines.append(f"  [{r.id}] {r.timestamp[:10]} {r.symbol}: {r.verdict} ({r.confidence}%){outcome}")
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
    await update.message.reply_text(
        "Unknown command. Type /help for available commands."
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
        logger.info("Alert manager patched for Telegram push notifications")
    except Exception:
        pass


# ── Bot Runner ───────────────────────────────────────────────

def run_bot() -> None:
    """Start the Telegram bot (blocking — runs the event loop)."""
    Update, Bot, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters = _get_telegram()

    token = _get_bot_token()

    app = ApplicationBuilder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("quote", cmd_quote))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("flows", cmd_flows))
    app.add_handler(CommandHandler("earnings", cmd_earnings))
    app.add_handler(CommandHandler("events", cmd_events))
    app.add_handler(CommandHandler("macro", cmd_macro))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(CommandHandler("memory", cmd_memory))
    app.add_handler(CommandHandler("pnl", cmd_pnl))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_unknown))

    # Patch alerts for push notifications
    patch_alert_manager()

    logger.info("Telegram bot starting... (Ctrl+C to stop)")
    print("\n  Telegram bot running. Send /start to your bot to begin.\n")
    app.run_polling()


def run_bot_background() -> threading.Thread:
    """Start the bot in a background thread (non-blocking, for REPL integration)."""
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    return t


# ── CLI entry point ──────────────────────────────────────────

if __name__ == "__main__":
    run_bot()
