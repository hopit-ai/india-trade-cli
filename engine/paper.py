"""
engine/paper.py
───────────────
PaperBroker — a fully functional BrokerAPI implementation that simulates
order execution without placing real orders.

State is persisted to ~/.trading_platform/paper_portfolio.json so positions
survive across sessions.

Order fill logic:
  - MARKET orders fill immediately at LTP ± 0.05% slippage
  - LIMIT  orders fill immediately if price is favourable, else stay OPEN
  - SL / SL-M orders are marked OPEN (not auto-triggered in this version)

Margin simulation:
  - CNC (delivery): full trade value debited from cash
  - MIS (intraday): 20% of value (5× leverage)
  - NRML (F&O):    12% of notional value (~8× leverage)
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, date
from pathlib import Path

from brokers.base import (
    BrokerAPI,
    UserProfile,
    Funds,
    Holding,
    Position,
    Quote,
    OptionsContract,
    OrderRequest,
    OrderResponse,
    Order,
)

PAPER_FILE = Path.home() / ".trading_platform" / "paper_portfolio.json"

MIS_MARGIN = 0.20  # 20% margin for intraday
NRML_MARGIN = 0.12  # 12% margin for F&O NRML

DEFAULT_STATE: dict = {
    "cash": 200_000.0,
    "holdings": {},  # symbol → {qty, avg_price, product}
    "positions": {},  # symbol → {qty, avg_price, product, exchange}
    "orders": [],  # list of order record dicts
}


class PaperBroker(BrokerAPI):
    """
    In-memory + JSON-persisted paper trading broker.
    Implements the full BrokerAPI interface so it is a drop-in
    replacement for ZerodhaAPI / GrowwAPI anywhere in the platform.
    """

    def __init__(self, capital: float | None = None) -> None:
        import os

        start = capital or float(os.environ.get("TOTAL_CAPITAL", 200_000))
        self._state = self._load_or_init(start)
        self._profile = UserProfile(
            user_id="PAPER_001",
            name="Paper Trader",
            email="paper@localhost",
            broker="Paper",
        )

    # ── Persistence ───────────────────────────────────────────

    def _load_or_init(self, capital: float) -> dict:
        PAPER_FILE.parent.mkdir(parents=True, exist_ok=True)
        if PAPER_FILE.exists():
            try:
                data = json.loads(PAPER_FILE.read_text())
                # Ensure all expected keys exist (forward-compat)
                for k, v in DEFAULT_STATE.items():
                    data.setdefault(k, deepcopy(v))
                return data
            except (json.JSONDecodeError, KeyError):
                pass
        state = deepcopy(DEFAULT_STATE)
        state["cash"] = capital
        PAPER_FILE.write_text(json.dumps(state, indent=2))
        return state

    def _save(self) -> None:
        PAPER_FILE.write_text(json.dumps(self._state, indent=2, default=str))

    def reset(self, capital: float | None = None) -> None:
        """Wipe portfolio and start fresh with given capital."""
        import os

        cap = capital or float(os.environ.get("TOTAL_CAPITAL", 200_000))
        self._state = deepcopy(DEFAULT_STATE)
        self._state["cash"] = cap
        self._save()

    # ── Auth (paper = always authenticated) ───────────────────

    def get_login_url(self) -> str:
        return "paper://no-login-required"

    def complete_login(self, **kwargs) -> bool:
        return True

    def is_authenticated(self) -> bool:
        return True

    def logout(self) -> None:
        self._save()

    # ── Profile / Funds ───────────────────────────────────────

    def get_profile(self) -> UserProfile:
        return self._profile

    def get_funds(self) -> Funds:
        holdings_value = sum(
            h["qty"] * self._ltp(sym) for sym, h in self._state["holdings"].items() if h["qty"] > 0
        )
        pos_margin = sum(
            abs(p["qty"])
            * self._ltp(sym)
            * (MIS_MARGIN if p.get("product", "MIS") == "MIS" else NRML_MARGIN)
            for sym, p in self._state["positions"].items()
            if p["qty"] != 0
        )
        cash = self._state["cash"]
        total = cash + holdings_value
        return Funds(
            available_cash=round(max(0.0, cash - pos_margin), 2),
            used_margin=round(pos_margin, 2),
            total_balance=round(total, 2),
        )

    # ── Holdings ──────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        result = []
        for sym, h in self._state["holdings"].items():
            if h["qty"] <= 0:
                continue
            ltp = self._ltp(sym)
            pnl = (ltp - h["avg_price"]) * h["qty"]
            pnl_pct = (pnl / (h["avg_price"] * h["qty"]) * 100) if h["avg_price"] else 0.0
            result.append(
                Holding(
                    symbol=sym,
                    exchange=h.get("exchange", "NSE"),
                    quantity=h["qty"],
                    avg_price=round(h["avg_price"], 2),
                    last_price=round(ltp, 2),
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                )
            )
        return result

    # ── Positions ─────────────────────────────────────────────

    def get_positions(self) -> list[Position]:
        result = []
        for sym, p in self._state["positions"].items():
            if p["qty"] == 0:
                continue
            ltp = self._ltp(sym)
            pnl = (ltp - p["avg_price"]) * p["qty"]
            result.append(
                Position(
                    symbol=sym,
                    exchange=p.get("exchange", "NSE"),
                    product=p.get("product", "MIS"),
                    quantity=p["qty"],
                    avg_price=round(p["avg_price"], 2),
                    last_price=round(ltp, 2),
                    pnl=round(pnl, 2),
                )
            )
        return result

    # ── Orders ────────────────────────────────────────────────

    def get_orders(self) -> list[Order]:
        today = date.today().isoformat()
        fields = Order.__dataclass_fields__
        return [
            Order(**{k: v for k, v in o.items() if k in fields})
            for o in self._state["orders"]
            if str(o.get("placed_at", ""))[:10] == today
        ]

    def place_order(self, req: OrderRequest) -> OrderResponse:
        order_id = str(uuid.uuid4())[:16]
        ltp = self._ltp(req.symbol)
        fill_price = self._fill_price(req, ltp)

        if fill_price is None:
            # Limit price not met — record as OPEN, don't apply fill
            self._record_order(order_id, req, req.price or ltp, "OPEN")
            return OrderResponse(order_id=order_id, status="OPEN")

        try:
            self._apply(req, fill_price)
        except ValueError as e:
            self._record_order(order_id, req, fill_price, "REJECTED", str(e))
            return OrderResponse(order_id=order_id, status="REJECTED", message=str(e))

        self._record_order(order_id, req, fill_price, "COMPLETE")
        self._save()
        return OrderResponse(order_id=order_id, status="COMPLETE", average_price=fill_price)

    def cancel_order(self, order_id: str) -> bool:
        for o in self._state["orders"]:
            if o["order_id"] == order_id and o["status"] == "OPEN":
                o["status"] = "CANCELLED"
                self._save()
                return True
        return False

    # ── Market data (delegate to market layer) ────────────────

    def get_quote(self, instruments: list[str]) -> list[Quote]:
        from market.quotes import get_quote

        try:
            return get_quote(instruments)
        except Exception:
            return [Quote(instrument=i, last_price=0.0) for i in instruments]

    def get_options_chain(
        self, underlying: str, expiry: str | None = None
    ) -> list[OptionsContract]:
        from market.options import get_options_chain

        return get_options_chain(underlying, expiry)

    # ── Internal helpers ──────────────────────────────────────

    def _ltp(self, symbol: str) -> float:
        """Get last traded price; fallback to stored avg_price."""
        from market.quotes import get_ltp

        for exchange in ("NSE", "BSE", "NFO"):
            try:
                return get_ltp(f"{exchange}:{symbol}")
            except Exception:
                continue
        # Last resort — stored cost basis
        if symbol in self._state["holdings"]:
            return self._state["holdings"][symbol]["avg_price"]
        if symbol in self._state["positions"]:
            return self._state["positions"][symbol]["avg_price"]
        return 0.0

    @staticmethod
    def _fill_price(req: OrderRequest, ltp: float) -> float | None:
        """Return fill price or None if limit not met."""
        slip = ltp * 0.0005  # 0.05% slippage on market orders
        ot = (req.order_type or "MARKET").upper()
        side = req.transaction_type.upper()

        if ot == "MARKET":
            return round(ltp + slip if side == "BUY" else ltp - slip, 2)
        elif ot == "LIMIT":
            p = req.price or ltp
            if side == "BUY" and ltp <= p:
                return round(ltp, 2)
            if side == "SELL" and ltp >= p:
                return round(ltp, 2)
            return None  # limit not hit
        # SL / SL-M → mark OPEN for now (not auto-triggered)
        return None

    def _apply(self, req: OrderRequest, fill_price: float) -> None:
        """Apply an order fill to cash / holdings / positions."""
        qty = req.quantity
        sym = req.symbol.upper()
        prod = (req.product or "CNC").upper()
        value = fill_price * qty
        margin = (
            value
            if prod == "CNC"
            else (value * MIS_MARGIN if prod == "MIS" else value * NRML_MARGIN)
        )
        side = req.transaction_type.upper()

        if side == "BUY":
            if self._state["cash"] < margin:
                raise ValueError(
                    f"Insufficient funds: need ₹{margin:,.0f}, have ₹{self._state['cash']:,.0f}"
                )
            self._state["cash"] -= margin
            bucket = "holdings" if prod == "CNC" else "positions"
            entry = self._state[bucket].get(
                sym, {"qty": 0, "avg_price": 0.0, "product": prod, "exchange": req.exchange}
            )
            old_val = entry["qty"] * entry["avg_price"]
            new_qty = entry["qty"] + qty
            entry["avg_price"] = ((old_val + value) / new_qty) if new_qty else fill_price
            entry["qty"] = new_qty
            entry["product"] = prod
            entry["exchange"] = req.exchange
            self._state[bucket][sym] = entry

        else:  # SELL
            if prod == "CNC":
                h = self._state["holdings"].get(sym, {"qty": 0, "avg_price": 0.0})
                if h["qty"] < qty:
                    raise ValueError(f"Cannot sell {qty} — only {h['qty']} held")
                realised = (fill_price - h["avg_price"]) * qty
                self._state["cash"] += value
                h["qty"] -= qty
                self._state["holdings"][sym] = h
            else:
                p = self._state["positions"].get(sym, {"qty": 0, "avg_price": 0.0, "product": prod})
                realised = (fill_price - p["avg_price"]) * qty
                self._state["cash"] += margin + realised
                p["qty"] -= qty
                self._state["positions"][sym] = p

    def _record_order(
        self,
        order_id: str,
        req: OrderRequest,
        fill_price: float,
        status: str,
        message: str = "",
    ) -> None:
        self._state["orders"].append(
            {
                "order_id": order_id,
                "symbol": req.symbol,
                "exchange": req.exchange,
                "transaction_type": req.transaction_type,
                "quantity": req.quantity,
                "price": req.price,
                "average_price": fill_price if status == "COMPLETE" else None,
                "order_type": req.order_type,
                "product": req.product,
                "status": status,
                "placed_at": datetime.now().isoformat(),
                # 'message' not in Order dataclass — kept in raw state only
            }
        )
