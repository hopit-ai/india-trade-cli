"""
brokers/groww.py
────────────────
Groww Partner API implementation of BrokerAPI.
Docs: https://groww.in/partner (partner portal)

NOTE: Groww's Partner API uses standard OAuth2 (auth code flow).
      All endpoints use Bearer token authentication.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

from .base import (
    BrokerAPI,
    Funds,
    Holding,
    Order,
    OptionsContract,
    OrderRequest,
    OrderResponse,
    Position,
    Quote,
    UserProfile,
)

TOKEN_FILE = Path.home() / ".trading_platform" / "groww.json"
BASE_URL   = "https://api.groww.in/v1"
AUTH_URL   = "https://groww.in/auth/oauth"


class GrowwAPI(BrokerAPI):
    """
    Full BrokerAPI implementation using Groww Partner REST API.
    Tokens are persisted in ~/.trading_platform/groww.json
    and automatically restored on construction.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8765/groww/callback",
    ) -> None:
        self.client_id     = client_id
        self.client_secret = client_secret
        self.redirect_uri  = redirect_uri
        self._token: dict  = self._load_token() or {}

    # ── Token management ──────────────────────────────────────

    def _save_token(self, data: dict) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["saved_at"] = datetime.now().isoformat()
        TOKEN_FILE.write_text(json.dumps(data))
        self._token = data

    def _load_token(self) -> dict | None:
        if TOKEN_FILE.exists():
            return json.loads(TOKEN_FILE.read_text())
        return None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token.get('access_token', '')}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        r = httpx.get(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = httpx.post(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            json=body,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        r = httpx.delete(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    # ── Authentication ────────────────────────────────────────

    def get_login_url(self) -> str:
        params = {
            "client_id":     self.client_id,
            "redirect_uri":  self.redirect_uri,
            "response_type": "code",
            "scope":         "portfolio orders profile",
        }
        return f"{AUTH_URL}/authorize?{urlencode(params)}"

    def complete_login(self, auth_code: str, **_) -> UserProfile:
        r = httpx.post(
            f"{AUTH_URL}/token",
            data={
                "grant_type":    "authorization_code",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri":  self.redirect_uri,
                "code":          auth_code,
            },
            timeout=10,
        )
        try:
            r.raise_for_status()
        except Exception:
            status = r.status_code
            if status == 401:
                raise RuntimeError(
                    "Groww login failed: invalid credentials.\n"
                    "Check your Client ID and Secret, then re-enter with:\n"
                    "  credentials delete GROWW_CLIENT_ID\n"
                    "  credentials delete GROWW_CLIENT_SECRET"
                )
            elif status == 429:
                raise RuntimeError("Groww login failed: rate limited. Wait a minute and try again.")
            else:
                raise RuntimeError(f"Groww login failed (HTTP {status}): {r.text[:200]}")
        self._save_token(r.json())
        return self.get_profile()

    def is_authenticated(self) -> bool:
        if not self._token.get("access_token"):
            return False
        try:
            self.get_profile()
            return True
        except Exception:
            return False

    def logout(self) -> None:
        try:
            httpx.post(
                f"{AUTH_URL}/revoke",
                data={
                    "token":           self._token.get("access_token", ""),
                    "client_id":       self.client_id,
                    "client_secret":   self.client_secret,
                },
                timeout=5,
            )
        except Exception:
            pass
        TOKEN_FILE.unlink(missing_ok=True)
        self._token = {}

    # ── Account ───────────────────────────────────────────────

    def get_profile(self) -> UserProfile:
        p = self._get("/user/profile")
        return UserProfile(
            user_id = p.get("userId", p.get("user_id", "")),
            name    = p.get("name", p.get("fullName", "")),
            email   = p.get("email", ""),
            broker  = "GROWW",
        )

    def get_funds(self) -> Funds:
        f = self._get("/funds")
        return Funds(
            available_cash = f.get("availableBalance", f.get("available_balance", 0.0)),
            used_margin    = f.get("usedMargin", f.get("used_margin", 0.0)),
            total_balance  = f.get("totalBalance", f.get("total_balance", 0.0)),
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        data = self._get("/holdings")
        items = data if isinstance(data, list) else data.get("holdings", [])
        holdings = []
        for h in items:
            avg   = h.get("averagePrice", h.get("average_price", 0.0))
            ltp   = h.get("ltp", h.get("last_price", 0.0))
            qty   = h.get("quantity", 0)
            pnl   = h.get("unrealisedPnl", h.get("unrealised_pnl", (ltp - avg) * qty))
            invested = avg * qty
            pnl_pct  = (pnl / invested * 100) if invested else 0.0
            holdings.append(Holding(
                symbol     = h.get("tradingSymbol", h.get("symbol", "")),
                exchange   = h.get("exchange", "NSE"),
                quantity   = qty,
                avg_price  = avg,
                last_price = ltp,
                pnl        = pnl,
                pnl_pct    = round(pnl_pct, 2),
            ))
        return holdings

    def get_positions(self) -> list[Position]:
        data = self._get("/positions")
        items = data if isinstance(data, list) else data.get("positions", [])
        positions = []
        for p in items:
            qty = p.get("netQuantity", p.get("quantity", 0))
            if qty == 0:
                continue
            positions.append(Position(
                symbol     = p.get("tradingSymbol", p.get("symbol", "")),
                exchange   = p.get("exchange", "NSE"),
                product    = p.get("productType", p.get("product", "MIS")),
                quantity   = qty,
                avg_price  = p.get("averagePrice", p.get("average_price", 0.0)),
                last_price = p.get("ltp", p.get("last_price", 0.0)),
                pnl        = p.get("unrealisedPnl", p.get("pnl", 0.0)),
            ))
        return positions

    # ── Market Data ───────────────────────────────────────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        result: dict[str, Quote] = {}
        for inst in instruments:
            # Accept "NSE:RELIANCE" or plain "RELIANCE"
            if ":" in inst:
                exchange, symbol = inst.split(":", 1)
            else:
                exchange, symbol = "NSE", inst
            try:
                q = self._get("/quotes", {
                    "symbol":   symbol,
                    "exchange": exchange,
                })
                close  = q.get("previousClose", q.get("close", q.get("ltp", 0.0)))
                ltp    = q.get("ltp", q.get("last_price", 0.0))
                change = ltp - close
                chg_pct = (change / close * 100) if close else 0.0
                result[inst] = Quote(
                    symbol     = symbol,
                    last_price = ltp,
                    open       = q.get("open", 0.0),
                    high       = q.get("high", 0.0),
                    low        = q.get("low", 0.0),
                    close      = close,
                    volume     = q.get("volume", 0),
                    change     = round(change, 2),
                    change_pct = round(chg_pct, 2),
                )
            except Exception:
                pass    # skip if individual quote fails
        return result

    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        params: dict = {"underlying": underlying}
        if expiry:
            params["expiry"] = expiry
        data = self._get("/options/chain", params)
        items = data if isinstance(data, list) else data.get("chain", [])
        contracts = []
        for c in items:
            contracts.append(OptionsContract(
                symbol      = c.get("tradingSymbol", c.get("symbol", "")),
                underlying  = underlying,
                expiry      = c.get("expiry", expiry or ""),
                strike      = c.get("strikePrice", c.get("strike", 0.0)),
                option_type = c.get("optionType", c.get("type", "CE")),
                last_price  = c.get("ltp", 0.0),
                oi          = c.get("oi", c.get("openInterest", 0)),
                oi_change   = c.get("oiChange", 0),
                volume      = c.get("volume", 0),
                iv          = c.get("iv", c.get("impliedVolatility")),
                lot_size    = c.get("lotSize", 1),
            ))
        return sorted(contracts, key=lambda c: (c.expiry, c.strike, c.option_type))

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> OrderResponse:
        body = {
            "tradingSymbol":   order.symbol,
            "exchange":        order.exchange,
            "transactionType": order.transaction_type,
            "quantity":        order.quantity,
            "orderType":       order.order_type,
            "productType":     order.product,
            "price":           order.price or 0,
            "triggerPrice":    order.trigger_price or 0,
            "validity":        order.validity,
        }
        r = self._post("/orders", body)
        return OrderResponse(
            order_id = str(r.get("orderId", r.get("order_id", ""))),
            status   = r.get("status", "OPEN"),
            message  = r.get("message", "Order placed"),
        )

    def get_orders(self) -> list[Order]:
        data = self._get("/orders")
        items = data if isinstance(data, list) else data.get("orders", [])
        orders = []
        for o in items:
            orders.append(Order(
                order_id         = str(o.get("orderId", o.get("order_id", ""))),
                symbol           = o.get("tradingSymbol", o.get("symbol", "")),
                exchange         = o.get("exchange", "NSE"),
                transaction_type = o.get("transactionType", o.get("transaction_type", "")),
                quantity         = o.get("quantity", 0),
                order_type       = o.get("orderType", o.get("order_type", "")),
                product          = o.get("productType", o.get("product", "")),
                status           = o.get("status", ""),
                price            = o.get("price"),
                average_price    = o.get("averagePrice", o.get("average_price")),
                filled_quantity  = o.get("filledQuantity", o.get("filled_quantity", 0)),
                placed_at        = o.get("createdAt", o.get("created_at", "")),
            ))
        return orders

    def cancel_order(self, order_id: str) -> bool:
        self._delete(f"/orders/{order_id}")
        return True

    # ── Historical Data ──────────────────────────────────────
    # Groww Partner API does not expose a historical candle endpoint.
    # Falls back to base class NotImplementedError.
