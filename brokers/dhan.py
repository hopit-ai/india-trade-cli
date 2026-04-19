"""
brokers/dhan.py
───────────────
Dhan broker implementation for india-trade-cli (#155).

Reference: github.com/marketcalls/openalgo/tree/main/broker/dhan
Dhan API docs: https://dhanhq.co/docs/v2/

Auth: Token-based (no OAuth redirect).
  - Generate access token from Dhan trader portal
  - Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env

No live-API calls are made here — methods raise NotImplementedError
until implemented. This scaffold documents the mapping layer.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from brokers.base import (
    BrokerAPI,
    Funds,
    Holding,
    Order,
    OrderRequest,
    OrderResponse,
    OptionsContract,
    Position,
    Quote,
    UserProfile,
)

DHAN_BASE_URL = "https://api.dhan.co"
DHAN_PORTAL_URL = "https://web.dhan.co/trading"

# ── Exchange segment mapping ─────────────────────────────────
# Our standard → Dhan segment codes
_EXCHANGE_MAP = {
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "NFO": "NSE_FNO",
    "BFO": "BSE_FNO",
    "MCX": "MCX_COMM",
    "CDS": "NSE_CURRENCY",
}

# ── Product type mapping ─────────────────────────────────────
# Our standard → Dhan product codes
_PRODUCT_MAP = {
    "CNC": "CNC",  # Cash-and-carry delivery
    "MIS": "INTRADAY",  # Intraday (MIS equivalent)
    "NRML": "MARGIN",  # Overnight F&O (NRML equivalent)
    "BO": "BO",  # Bracket order
    "CO": "CO",  # Cover order
}

# ── Order type mapping ───────────────────────────────────────
_ORDER_TYPE_MAP = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "SL": "STOP_LOSS",
    "SL-M": "STOP_LOSS_MARKET",
}


class DhanBroker(BrokerAPI):
    """
    Dhan broker implementation.

    Authentication:
        export DHAN_CLIENT_ID=your_client_id
        export DHAN_ACCESS_TOKEN=your_access_token

    The access token is a long-lived JWT generated from the Dhan portal.
    No OAuth redirect is needed.
    """

    def __init__(self) -> None:
        self.client_id = os.environ.get("DHAN_CLIENT_ID", "")
        self.access_token = os.environ.get("DHAN_ACCESS_TOKEN", "")
        self._session = requests.Session()
        if self.access_token:
            self._session.headers.update(
                {
                    "access-token": self.access_token,
                    "client-id": self.client_id,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )

    # ── Mapping helpers ──────────────────────────────────────

    def _map_exchange(self, exchange: str) -> str:
        return _EXCHANGE_MAP.get(exchange.upper(), f"{exchange.upper()}_EQ")

    def _map_product(self, product: str) -> str:
        return _PRODUCT_MAP.get(product.upper(), product.upper())

    def _map_order_type(self, order_type: str) -> str:
        return _ORDER_TYPE_MAP.get(order_type.upper(), order_type.upper())

    # ── Authentication ───────────────────────────────────────

    def get_login_url(self) -> str:
        """Dhan uses token-based auth. Returns portal URL for token generation."""
        return DHAN_PORTAL_URL

    def complete_login(self, **kwargs) -> UserProfile:
        """
        Dhan token-based auth: no OAuth callback needed.
        Call this after setting DHAN_ACCESS_TOKEN env var.
        """
        client_id = kwargs.get("client_id") or self.client_id
        access_token = kwargs.get("access_token") or self.access_token
        if not access_token:
            raise ValueError("DHAN_ACCESS_TOKEN must be set")
        os.environ["DHAN_CLIENT_ID"] = client_id
        os.environ["DHAN_ACCESS_TOKEN"] = access_token
        self.client_id = client_id
        self.access_token = access_token
        self._session.headers.update(
            {
                "access-token": access_token,
                "client-id": client_id,
            }
        )
        return self.get_profile()

    def is_authenticated(self) -> bool:
        """True if access token is set in env or instance."""
        return bool(self.access_token)

    def logout(self) -> None:
        """Clear the access token from env and session."""
        os.environ.pop("DHAN_ACCESS_TOKEN", None)
        os.environ.pop("DHAN_CLIENT_ID", None)
        self.access_token = ""
        self.client_id = ""
        self._session.headers.pop("access-token", None)

    # ── Account ──────────────────────────────────────────────

    def get_profile(self) -> UserProfile:
        resp = self._get("/v2/profile")
        data = resp.get("data", {})
        return UserProfile(
            user_id=data.get("dhanClientId", self.client_id),
            name=data.get("userName", "Dhan User"),
            email=data.get("email", ""),
            broker="DHAN",
        )

    def get_funds(self) -> Funds:
        resp = self._get("/v2/fundlimit")
        data = resp.get("data", {})
        return Funds(
            available_cash=float(data.get("availabelBalance", 0)),
            used_margin=float(data.get("utilizedAmount", 0)),
            total_balance=float(data.get("sox", 0)),  # SOX = total account value
        )

    # ── Portfolio ────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        resp = self._get("/v2/holdings")
        holdings = []
        for item in resp.get("data", []):
            qty = int(item.get("totalQty", 0))
            avg = float(item.get("avgCostPrice", 0))
            ltp = float(item.get("lastTradedPrice", 0))
            pnl = (ltp - avg) * qty
            holdings.append(
                Holding(
                    symbol=item.get("tradingSymbol", ""),
                    exchange=item.get("exchange", "NSE"),
                    quantity=qty,
                    avg_price=avg,
                    last_price=ltp,
                    pnl=round(pnl, 2),
                    pnl_pct=round((ltp / avg - 1) * 100, 2) if avg else 0,
                )
            )
        return holdings

    def get_positions(self) -> list[Position]:
        resp = self._get("/v2/positions")
        positions = []
        for item in resp.get("data", []):
            qty = int(item.get("netQty", 0))
            avg = float(item.get("buyAvg", 0))
            ltp = float(item.get("lastTradedPrice", 0))
            positions.append(
                Position(
                    symbol=item.get("tradingSymbol", ""),
                    exchange=item.get("exchangeSegment", "NSE_EQ").replace("_EQ", ""),
                    product=item.get("productType", "CNC"),
                    quantity=qty,
                    avg_price=avg,
                    last_price=ltp,
                    pnl=round(float(item.get("unrealizedProfit", 0)), 2),
                )
            )
        return positions

    # ── Market Data ──────────────────────────────────────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        """
        instruments: ["NSE:RELIANCE", "NSE:INFY"]
        Dhan uses securityId-based quotes — requires symbol lookup first.
        """
        # Simplified: real implementation needs symbol→securityId mapping
        raise NotImplementedError(
            "Dhan quote API requires securityId lookup. "
            "Use marketFeed/ltp endpoint with securityId."
        )

    def get_options_chain(
        self, underlying: str, expiry: Optional[str] = None
    ) -> list[OptionsContract]:
        raise NotImplementedError(
            "Dhan options chain: use /v2/optionchain endpoint with underlyingSecurityId."
        )

    # ── Orders ───────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> OrderResponse:
        payload = {
            "dhanClientId": self.client_id,
            "transactionType": order.transaction_type.upper(),
            "exchangeSegment": self._map_exchange(order.exchange),
            "productType": self._map_product(order.product),
            "orderType": self._map_order_type(order.order_type),
            "validity": order.validity or "DAY",
            "tradingSymbol": order.symbol.upper(),
            "securityId": "",  # Must be resolved from symbol → securityId
            "quantity": order.quantity,
            "price": order.price or 0,
            "triggerPrice": order.trigger_price or 0,
            "disclosedQuantity": 0,
            "afterMarketOrder": False,
            "tag": order.tag or "",
        }
        resp = self._post("/v2/orders", payload)
        data = resp if isinstance(resp, dict) else {}
        return OrderResponse(
            order_id=str(data.get("orderId", "")),
            status=str(data.get("orderStatus", "OPEN")),
            message=str(data.get("remarks", "")),
        )

    def get_orders(self) -> list[Order]:
        resp = self._get("/v2/orders")
        orders = []
        for item in resp.get("data", []):
            orders.append(
                Order(
                    order_id=str(item.get("orderId", "")),
                    symbol=item.get("tradingSymbol", ""),
                    exchange=item.get("exchangeSegment", ""),
                    transaction_type=item.get("transactionType", ""),
                    quantity=int(item.get("quantity", 0)),
                    order_type=item.get("orderType", "MARKET"),
                    product=item.get("productType", "CNC"),
                    status=item.get("orderStatus", ""),
                    price=float(item.get("price", 0)) or None,
                    average_price=float(item.get("averageTradedPrice", 0)) or None,
                    filled_quantity=int(item.get("filledQty", 0)),
                    placed_at=item.get("createTime"),
                    tag=item.get("correlationId"),
                )
            )
        return orders

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._delete(f"/v2/orders/{order_id}")
            return True
        except Exception:
            return False

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, path: str) -> dict:
        url = DHAN_BASE_URL + path
        resp = self._session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict) -> dict:
        url = DHAN_BASE_URL + path
        resp = self._session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> dict:
        url = DHAN_BASE_URL + path
        resp = self._session.delete(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
