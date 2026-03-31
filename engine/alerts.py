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
    condition_type: str          # "PRICE" or "TECHNICAL"
    condition:      str          # "ABOVE" or "BELOW"
    threshold:      float
    indicator:      Optional[str] = None  # for TECHNICAL: "RSI", "MACD", etc.

    def describe(self) -> str:
        if self.condition_type == "TECHNICAL":
            return f"{self.indicator} {self.condition} {self.threshold}"
        return f"price {self.condition} ₹{self.threshold:,.2f}"


@dataclass
class Alert:
    id:           str
    alert_type:   str                 # PRICE | TECHNICAL | CONDITIONAL
    symbol:       str                 # e.g. "RELIANCE"
    exchange:     str                 # e.g. "NSE"
    condition:    str                 # ABOVE | BELOW | CROSSES
    threshold:    float               # e.g. 2800.0
    indicator:    Optional[str] = None  # For technical: RSI, MACD_SIGNAL, etc.
    message:      str = ""
    created_at:   str = ""
    triggered:    bool = False
    triggered_at: Optional[str] = None
    # Conditional alert: multiple conditions joined by AND
    conditions:   list[dict] = field(default_factory=list)

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

class AlertManager:
    """Manages alerts with persistence and background polling."""

    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._poller_thread: Optional[threading.Thread] = None
        self._polling = False
        self._load()

    # ── Public API ────────────────────────────────────────────

    def add_price_alert(
        self,
        symbol:    str,
        condition: str,
        threshold: float,
        exchange:  str = "NSE",
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
        )
        alert.message = alert.describe()
        self._alerts.append(alert)
        self._save()
        return alert

    def add_technical_alert(
        self,
        symbol:    str,
        indicator: str,
        condition: str,
        threshold: float,
        exchange:  str = "NSE",
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
        )
        alert.message = alert.describe()
        self._alerts.append(alert)
        self._save()
        return alert

    def add_conditional_alert(
        self,
        symbol:     str,
        conditions: list[dict],
        exchange:   str = "NSE",
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

    def start_polling(self, interval: int = 60) -> None:
        """Start background alert checking (daemon thread)."""
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

    def _poll_loop(self, interval: int) -> None:
        while self._polling:
            if self.active_count() > 0:
                triggered = self.check_alerts()
                for alert in triggered:
                    self._notify(alert)
            time.sleep(interval)

    def _notify(self, alert: Alert) -> None:
        console.print()
        console.print(Panel(
            f"[bold white]{alert.describe()}[/bold white]\n"
            f"[dim]Triggered at {alert.triggered_at}[/dim]",
            title="[bold yellow]🔔 ALERT TRIGGERED[/bold yellow]",
            border_style="yellow",
        ))
        print("\a", end="", flush=True)  # system bell

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
            "RSI":   getattr(snapshot, "rsi", None),
            "RSI14": getattr(snapshot, "rsi", None),
            "MACD":  getattr(snapshot, "macd", None),
            "ADX":   getattr(snapshot, "adx", None),
            "ATR":   getattr(snapshot, "atr", None),
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

alert_manager = AlertManager()
