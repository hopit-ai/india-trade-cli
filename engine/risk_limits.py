"""
engine/risk_limits.py
─────────────────────
Non-overridable hard risk limits.

Enforced BEFORE every order reaches the broker. Cannot be bypassed by
LLM reasoning, user prompts, or any code path.

Configuration via environment variables:
  MAX_DAILY_LOSS         — max cumulative loss per day in INR (default: 20000)
  MAX_DAILY_TRADES       — max total trades per day (default: 20)
  MAX_TRADES_PER_SYMBOL  — max trades per symbol per day (default: 5)
  RISK_DB_PATH           — path to SQLite DB (default: ~/.trading_platform/risk_limits.db)

Usage:
    from engine.risk_limits import risk_limits, RiskLimitError

    # Before placing order:
    risk_limits.check("INFY", "BUY", 10, 1400.0)

    # After order fills:
    risk_limits.record_trade("INFY", "BUY", 10, 1400.0, pnl=0.0)

    # Check status:
    status = risk_limits.get_status()
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional


class RiskLimitError(Exception):
    """Raised when an order would breach a hard risk limit."""


def _db_path() -> Path:
    path = os.environ.get("RISK_DB_PATH")
    if path:
        return Path(path)
    return Path.home() / ".trading_platform" / "risk_limits.db"


class RiskLimits:
    """
    Tracks daily P&L and trade counts in SQLite.
    Checks hard limits before every order.
    Persists across process restarts; resets at midnight.
    """

    def __init__(self) -> None:
        self._db = _db_path()
        self._db.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── Config ────────────────────────────────────────────────

    @property
    def max_daily_loss(self) -> float:
        return -abs(float(os.environ.get("MAX_DAILY_LOSS", "20000")))

    @property
    def max_daily_trades(self) -> int:
        return int(os.environ.get("MAX_DAILY_TRADES", "20"))

    @property
    def max_trades_per_symbol(self) -> int:
        return int(os.environ.get("MAX_TRADES_PER_SYMBOL", "5"))

    # ── DB setup ──────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_trades (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date  TEXT NOT NULL,
                    symbol      TEXT NOT NULL,
                    action      TEXT NOT NULL,
                    quantity    INTEGER NOT NULL,
                    price       REAL NOT NULL,
                    pnl         REAL NOT NULL DEFAULT 0.0,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trade_date
                ON daily_trades (trade_date)
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db))

    def _today(self) -> str:
        return date.today().isoformat()

    # ── Read helpers ──────────────────────────────────────────

    def _daily_loss(self) -> float:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl), 0.0) FROM daily_trades WHERE trade_date = ?",
                (self._today(),),
            ).fetchone()
        return float(row[0]) if row else 0.0

    def _trades_today(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM daily_trades WHERE trade_date = ?",
                (self._today(),),
            ).fetchone()
        return int(row[0]) if row else 0

    def _trades_today_for_symbol(self, symbol: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM daily_trades WHERE trade_date = ? AND symbol = ?",
                (self._today(), symbol.upper()),
            ).fetchone()
        return int(row[0]) if row else 0

    # ── Core check ────────────────────────────────────────────

    def check(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        current_position: Optional[dict] = None,
    ) -> None:
        """
        Validate an order against all hard risk limits.

        Args:
            symbol:           Stock/index symbol
            action:           "BUY" or "SELL"
            quantity:         Number of shares/lots
            price:            Order price (use 0 for market orders)
            current_position: Optional dict with {avg_price, quantity} for
                              pyramiding check. Pass None to skip pyramid check.

        Raises:
            RiskLimitError: if any limit would be breached.
        """
        sym = symbol.upper()
        action = action.upper()

        # ── 1. Daily loss cap ─────────────────────────────────
        current_loss = self._daily_loss()
        if current_loss <= self.max_daily_loss:
            raise RiskLimitError(
                f"Order blocked — daily loss cap reached.\n"
                f"  P&L today: -₹{abs(current_loss):,.0f}  "
                f"(limit: -₹{abs(self.max_daily_loss):,.0f})\n"
                f"  No more orders allowed today."
            )

        # ── 2. Max trades per day ─────────────────────────────
        trades = self._trades_today()
        if trades >= self.max_daily_trades:
            raise RiskLimitError(
                f"Order blocked — daily trade limit reached.\n"
                f"  Trades today: {trades} / {self.max_daily_trades}\n"
                f"  No more orders allowed today."
            )

        # ── 3. Max trades per symbol ──────────────────────────
        sym_trades = self._trades_today_for_symbol(sym)
        if sym_trades >= self.max_trades_per_symbol:
            raise RiskLimitError(
                f"Order blocked — {sym} trade limit reached.\n"
                f"  {sym} trades today: {sym_trades} / {self.max_trades_per_symbol}\n"
                f"  Try a different symbol or wait until tomorrow."
            )

        # ── 4. No pyramiding into losers ──────────────────────
        if current_position and action == "BUY" and quantity > 0:
            avg = float(current_position.get("avg_price", 0))
            if avg > 0 and price > 0 and price < avg:
                loss_pct = (avg - price) / avg * 100
                raise RiskLimitError(
                    f"Order blocked — pyramiding into a losing position.\n"
                    f"  {sym}: held at avg ₹{avg:,.2f}, current ₹{price:,.2f} "
                    f"({loss_pct:.1f}% below avg).\n"
                    f"  Cannot add to a losing position (anti-pyramid rule).\n"
                    f"  To override: close the losing position first."
                )

    # ── Record ────────────────────────────────────────────────

    def record_trade(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        pnl: float = 0.0,
    ) -> None:
        """Record a completed trade for daily tracking."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_trades
                    (trade_date, symbol, action, quantity, price, pnl, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._today(),
                    symbol.upper(),
                    action.upper(),
                    quantity,
                    price,
                    pnl,
                    datetime.now().isoformat(),
                ),
            )

    # ── Status ────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return current risk usage."""
        loss = self._daily_loss()
        trades = self._trades_today()
        remaining_loss = max(0.0, loss - self.max_daily_loss)

        return {
            "daily_loss": loss,
            "trades_today": trades,
            "max_daily_loss": self.max_daily_loss,
            "max_daily_trades": self.max_daily_trades,
            "max_trades_per_symbol": self.max_trades_per_symbol,
            "remaining_loss_room": -remaining_loss if loss < 0 else abs(self.max_daily_loss),
            "remaining_trades": max(0, self.max_daily_trades - trades),
            "limits_hit": loss <= self.max_daily_loss or trades >= self.max_daily_trades,
        }


# ── Singleton ─────────────────────────────────────────────────
risk_limits = RiskLimits()
