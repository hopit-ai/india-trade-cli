"""
engine/alerts.py
────────────────
Price and technical alerts with background polling.

Usage:
    from engine.alerts import alert_manager

    alert_manager.add_price_alert("RELIANCE", "ABOVE", 2800)
    alert_manager.add_technical_alert("INFY", "RSI", "ABOVE", 70)
    alert_manager.start_polling()       # daemon thread, 60s interval
    alert_manager.list_alerts()         # show all active alerts
    alert_manager.remove_alert(id)      # cancel an alert
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

ALERTS_FILE = Path.home() / ".trading_platform" / "alerts.json"


# ── Data model ────────────────────────────────────────────────


@dataclass
class AlertCondition:
    """A single condition within a conditional alert."""

    condition_type: str  # "PRICE" or "TECHNICAL"
    condition: str  # "ABOVE" or "BELOW"
    threshold: float
    indicator: Optional[str] = None  # for TECHNICAL: "RSI", "MACD", etc.

    def describe(self) -> str:
        if self.condition_type == "TECHNICAL":
            return f"{self.indicator} {self.condition} {self.threshold}"
        return f"price {self.condition} ₹{self.threshold:,.2f}"


@dataclass
class Alert:
    id: str
    alert_type: str  # PRICE | TECHNICAL | CONDITIONAL
    symbol: str  # e.g. "RELIANCE"
    exchange: str  # e.g. "NSE"
    condition: str  # ABOVE | BELOW | CROSSES
    threshold: float  # e.g. 2800.0
    indicator: Optional[str] = None  # For technical: RSI, MACD_SIGNAL, etc.
    message: str = ""
    created_at: str = ""
    triggered: bool = False
    triggered_at: Optional[str] = None
    # Conditional alert: multiple conditions joined by AND
    conditions: list[dict] = field(default_factory=list)
    # OpenClaw / external callback: POST alert payload here when triggered
    webhook_url: Optional[str] = None

    def describe(self) -> str:
        if self.alert_type == "CONDITIONAL" and self.conditions:
            parts = []
            for c in self.conditions:
                cond = AlertCondition(**c) if isinstance(c, dict) else c
                parts.append(cond.describe())
            return f"{self.symbol} ({' AND '.join(parts)})"
        if self.alert_type == "TECHNICAL":
            return f"{self.symbol} {self.indicator} {self.condition} {self.threshold}"
        return f"{self.symbol} price {self.condition} ₹{self.threshold:,.2f}"


# ── Alert Manager ─────────────────────────────────────────────


def _is_market_hours() -> bool:
    """
    Returns True only during NSE trading hours: Mon–Fri, 9:15–15:30 IST.
    Prevents alerts firing on stale prices outside market hours.
    """
    from datetime import timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


class AlertManager:
    """Manages alerts with persistence and background polling."""

    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._poller_thread: Optional[threading.Thread] = None
        self._polling = False
        self._lock = threading.Lock()  # protects triggered flag against tick races
        self._load()

    # ── Public API ────────────────────────────────────────────

    def add_price_alert(
        self,
        symbol: str,
        condition: str,
        threshold: float,
        exchange: str = "NSE",
        webhook_url: Optional[str] = None,
    ) -> Alert:
        """Create a price-based alert (ABOVE / BELOW / CROSSES)."""
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            alert_type="PRICE",
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            condition=condition.upper(),
            threshold=float(threshold),
            created_at=datetime.now().isoformat(timespec="seconds"),
            webhook_url=webhook_url,
        )
        alert.message = alert.describe()
        self._alerts.append(alert)
        self._save()
        self._auto_subscribe(alert)
        return alert

    def add_technical_alert(
        self,
        symbol: str,
        indicator: str,
        condition: str,
        threshold: float,
        exchange: str = "NSE",
        webhook_url: Optional[str] = None,
    ) -> Alert:
        """Create a technical-indicator alert (RSI > 70, etc.)."""
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            alert_type="TECHNICAL",
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            condition=condition.upper(),
            threshold=float(threshold),
            indicator=indicator.upper(),
            created_at=datetime.now().isoformat(timespec="seconds"),
            webhook_url=webhook_url,
        )
        alert.message = alert.describe()
        self._alerts.append(alert)
        self._save()
        return alert

    def add_conditional_alert(
        self,
        symbol: str,
        conditions: list[dict],
        exchange: str = "NSE",
        webhook_url: Optional[str] = None,
    ) -> Alert:
        """
        Create a conditional alert with AND logic.

        conditions: list of dicts, each with:
            condition_type: "PRICE" or "TECHNICAL"
            condition: "ABOVE" or "BELOW"
            threshold: float
            indicator: str (only for TECHNICAL, e.g. "RSI")

        Example:
            add_conditional_alert("RELIANCE", [
                {"condition_type": "PRICE", "condition": "ABOVE", "threshold": 2800},
                {"condition_type": "TECHNICAL", "condition": "ABOVE", "threshold": 60, "indicator": "RSI"},
            ])
            → Triggers when RELIANCE price > 2800 AND RSI > 60
        """
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            alert_type="CONDITIONAL",
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            condition="AND",
            threshold=0,
            conditions=conditions,
            created_at=datetime.now().isoformat(timespec="seconds"),
            webhook_url=webhook_url,
        )
        alert.message = alert.describe()
        self._alerts.append(alert)
        self._save()
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        before = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.id != alert_id]
        removed = len(self._alerts) < before
        if removed:
            self._save()
        return removed

    def list_alerts(self) -> list[dict]:
        """Return all active (non-triggered) alerts as dicts."""
        return [asdict(a) for a in self._alerts if not a.triggered]

    def active_count(self) -> int:
        return sum(1 for a in self._alerts if not a.triggered)

    def print_alerts(self) -> None:
        """Display alerts as a Rich table."""
        active = [a for a in self._alerts if not a.triggered]
        if not active:
            console.print("[dim]No active alerts.[/dim]")
            return

        table = Table(title="Active Alerts", show_lines=False)
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Type", width=10)
        table.add_column("Alert", style="bold")
        table.add_column("Created", style="dim")

        for a in active:
            table.add_row(a.id, a.alert_type, a.describe(), a.created_at)
        console.print(table)

    # ── Polling ───────────────────────────────────────────────

    def start_realtime(self) -> None:
        """
        Register with WebSocket for real-time alert evaluation.
        Fires on every tick — instant alerts instead of 60s polling.
        Falls back to polling if WebSocket is not connected.
        """
        try:
            from market.websocket import ws_manager

            if ws_manager.connected:
                ws_manager.on_tick(self._on_tick)
                # Subscribe to all alerted symbols
                symbols = list(
                    {f"{a.exchange}:{a.symbol}" for a in self._alerts if not a.triggered}
                )
                if symbols:
                    ws_manager.subscribe(symbols)
                console.print("[dim]  Alerts: real-time via WebSocket[/dim]")
                return
        except Exception:
            pass

        # Fallback to polling
        self.start_polling(interval=60)

    def _on_tick(self, tick) -> None:
        """Called on every WebSocket tick — evaluate price alerts instantly.

        Uses a lock to prevent the race condition where multiple rapid ticks
        all see triggered=False simultaneously and each fire a notification.
        Only fires during market hours (9:15–15:30 IST, Mon–Fri).
        """
        if self.active_count() == 0:
            return
        if not _is_market_hours():
            return

        ltp = tick.ltp if hasattr(tick, "ltp") else 0
        if ltp <= 0:
            return

        tick_sym = tick.symbol if hasattr(tick, "symbol") else ""

        to_notify: list[tuple[Alert, float]] = []

        with self._lock:
            for alert in self._alerts:
                if alert.triggered:
                    continue
                if alert.alert_type != "PRICE":
                    continue

                alert_sym_variants = [
                    f"{alert.exchange}:{alert.symbol}-EQ",
                    f"{alert.exchange}:{alert.symbol}",
                ]
                if tick_sym not in alert_sym_variants:
                    continue

                condition_met = False
                if alert.condition == "ABOVE" and ltp >= alert.threshold:
                    condition_met = True
                elif alert.condition == "BELOW" and ltp <= alert.threshold:
                    condition_met = True
                elif alert.condition == "CROSSES" and ltp >= alert.threshold:
                    condition_met = True

                if condition_met:
                    # Set inside lock — prevents other threads double-firing
                    alert.triggered = True
                    alert.triggered_at = datetime.now().isoformat(timespec="seconds")
                    to_notify.append((alert, ltp))

        if to_notify:
            self._save()
            for alert, price in to_notify:
                self._notify(alert, ltp=price)

    def start_polling(self, interval: int = 60) -> None:
        """Start background alert checking (daemon thread). Fallback when no WebSocket."""
        if self._polling:
            return
        self._polling = True
        self._poller_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval,),
            daemon=True,
        )
        self._poller_thread.start()

    def stop_polling(self) -> None:
        self._polling = False

    def check_alerts(self) -> list[Alert]:
        """Check all active alerts and return any that just triggered."""
        triggered: list[Alert] = []
        for alert in self._alerts:
            if alert.triggered:
                continue
            try:
                if self._evaluate(alert):
                    alert.triggered = True
                    alert.triggered_at = datetime.now().isoformat(timespec="seconds")
                    triggered.append(alert)
            except Exception:
                pass  # Skip alerts that fail to evaluate (broker down, etc.)
        if triggered:
            self._save()
        return triggered

    # ── Private ───────────────────────────────────────────────

    def _auto_subscribe(self, alert: Alert) -> None:
        """Auto-subscribe the alert's symbol to WebSocket for real-time ticks."""
        try:
            from market.websocket import ws_manager

            if ws_manager.connected:
                ws_manager.subscribe([f"{alert.exchange}:{alert.symbol}"])
        except Exception:
            pass

    def _poll_loop(self, interval: int) -> None:
        while self._polling:
            if self.active_count() > 0 and _is_market_hours():
                triggered = self.check_alerts()
                for alert in triggered:
                    self._notify(alert)
            time.sleep(interval)

    def _notify(self, alert: Alert, ltp: Optional[float] = None) -> None:
        """
        Multi-channel alert notification:
          1. Terminal (Rich panel + system bell)
          2. macOS desktop notification
          3. Telegram push (if bot is configured)
        """
        desc = alert.describe()
        ltp_str = f"  LTP: ₹{ltp:,.2f}" if ltp else ""

        # 1. Terminal
        console.print()
        console.print(
            Panel(
                f"[bold white]{desc}[/bold white]{ltp_str}\n"
                f"[dim]Triggered at {alert.triggered_at}[/dim]",
                title="[bold yellow]🔔 ALERT TRIGGERED[/bold yellow]",
                border_style="yellow",
            )
        )
        print("\a", end="", flush=True)  # system bell

        # 2. macOS desktop notification
        _desktop_notify(
            title="Alert Triggered",
            message=f"{desc}{ltp_str}",
        )

        # 3. Telegram push
        _telegram_notify(f"🔔 ALERT TRIGGERED\n\n{desc}{ltp_str}")

        # 4. Webhook (OpenClaw / external agents)
        if alert.webhook_url:
            _webhook_notify(alert, ltp=ltp)

    def _evaluate(self, alert: Alert) -> bool:
        """Check if an alert's condition is met right now."""
        if alert.alert_type == "PRICE":
            return self._check_price(alert)
        elif alert.alert_type == "TECHNICAL":
            return self._check_technical(alert)
        elif alert.alert_type == "CONDITIONAL":
            return self._check_conditional(alert)
        return False

    def _check_price(self, alert: Alert) -> bool:
        instrument = f"{alert.exchange}:{alert.symbol}"

        # Try WebSocket first (instant)
        try:
            from market.websocket import ws_manager

            ws_ltp = ws_manager.get_ltp(instrument)
            if ws_ltp and ws_ltp > 0:
                ltp = ws_ltp
            else:
                raise ValueError("no ws tick")
        except Exception:
            # Fall back to REST
            try:
                from market.quotes import get_ltp

                ltp = get_ltp(instrument)
            except Exception:
                return False

        if alert.condition == "ABOVE":
            return ltp >= alert.threshold
        elif alert.condition == "BELOW":
            return ltp <= alert.threshold
        elif alert.condition == "CROSSES":
            return ltp >= alert.threshold  # simplified: treated as ABOVE
        return False

    def _check_technical(self, alert: Alert) -> bool:
        from analysis.technical import analyse as tech_analyse

        snapshot = tech_analyse(alert.symbol, alert.exchange)
        indicator_key = (alert.indicator or "").upper()

        # Extract the indicator value from the TechnicalSnapshot
        value_map = {
            "RSI": getattr(snapshot, "rsi", None),
            "RSI14": getattr(snapshot, "rsi", None),
            "MACD": getattr(snapshot, "macd", None),
            "ADX": getattr(snapshot, "adx", None),
            "ATR": getattr(snapshot, "atr", None),
            "SCORE": getattr(snapshot, "score", None),
        }
        value = value_map.get(indicator_key)
        if value is None:
            return False

        if alert.condition == "ABOVE":
            return float(value) >= alert.threshold
        elif alert.condition == "BELOW":
            return float(value) <= alert.threshold
        return False

    def _check_conditional(self, alert: Alert) -> bool:
        """
        Check a conditional alert — ALL conditions must be true (AND logic).
        Each condition is either PRICE or TECHNICAL.
        """
        if not alert.conditions:
            return False

        from brokers.session import get_broker

        for cond_dict in alert.conditions:
            cond = AlertCondition(**cond_dict) if isinstance(cond_dict, dict) else cond_dict

            if cond.condition_type == "PRICE":
                try:
                    broker = get_broker()
                    instrument = f"{alert.exchange}:{alert.symbol}"
                    ltp = broker.get_ltp(instrument)
                except Exception:
                    try:
                        from market.quotes import get_ltp

                        ltp = get_ltp(f"{alert.exchange}:{alert.symbol}")
                    except Exception:
                        return False

                if cond.condition == "ABOVE" and ltp < cond.threshold:
                    return False
                elif cond.condition == "BELOW" and ltp > cond.threshold:
                    return False

            elif cond.condition_type == "TECHNICAL":
                try:
                    from analysis.technical import analyse as tech_analyse

                    snapshot = tech_analyse(alert.symbol, alert.exchange)
                    indicator_key = (cond.indicator or "").upper()
                    value_map = {
                        "RSI": getattr(snapshot, "rsi", None),
                        "MACD": getattr(snapshot, "macd", None),
                        "ADX": getattr(snapshot, "adx", None),
                        "ATR": getattr(snapshot, "atr", None),
                        "SCORE": getattr(snapshot, "score", None),
                    }
                    value = value_map.get(indicator_key)
                    if value is None:
                        return False

                    if cond.condition == "ABOVE" and float(value) < cond.threshold:
                        return False
                    elif cond.condition == "BELOW" and float(value) > cond.threshold:
                        return False
                except Exception:
                    return False

        return True  # all conditions passed

    # ── Persistence ───────────────────────────────────────────

    def _save(self) -> None:
        try:
            ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(a) for a in self._alerts]
            ALERTS_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load(self) -> None:
        try:
            if ALERTS_FILE.exists():
                data = json.loads(ALERTS_FILE.read_text())
                self._alerts = [Alert(**d) for d in data]
        except Exception:
            self._alerts = []


# ── Singleton ─────────────────────────────────────────────────

# ── Notification Helpers ──────────────────────────────────────


def _desktop_notify(title: str, message: str) -> None:
    """
    Send a macOS desktop notification via osascript.
    Non-blocking — runs in a background thread.
    Falls back silently on non-macOS systems.
    """
    import subprocess
    import sys

    if sys.platform != "darwin":
        return

    def _send():
        try:
            # Escape quotes for AppleScript
            t = title.replace('"', '\\"')
            m = message.replace('"', '\\"')
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{m}" with title "{t}" sound name "Glass"',
                ],
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def _telegram_notify(message: str) -> None:
    """
    Send a Telegram push notification.
    Non-blocking — runs in background thread.
    """
    try:
        from bot.telegram_bot import send_push

        send_push(message)
    except Exception:
        pass


def _webhook_notify(alert: Alert, ltp: Optional[float] = None) -> None:
    """
    POST alert payload to the registered webhook_url.
    Non-blocking — runs in a background thread.
    """
    import json as _json

    def _send():
        try:
            import urllib.request

            payload = {
                "event": "alert_triggered",
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "symbol": alert.symbol,
                "exchange": alert.exchange,
                "description": alert.describe(),
                "triggered_at": alert.triggered_at,
                "ltp": ltp,
            }
            body = _json.dumps(payload).encode()
            req = urllib.request.Request(
                alert.webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


alert_manager = AlertManager()
