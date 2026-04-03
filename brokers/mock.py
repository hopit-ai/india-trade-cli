"""
brokers/mock.py
───────────────
Mock broker for --no-broker mode and paper trading.

Principles:
  - NO fake market data — always delegates to yfinance via passthrough
  - NO hardcoded holdings/positions/orders — starts empty
  - Paper trades are tracked in engine/paper.py (separate file)
  - Account data (funds) uses configured TOTAL_CAPITAL env var
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from .base import (
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


class MockBrokerAPI(BrokerAPI):
    """
    Mock broker — no real API, delegates market data to yfinance.

    Starts with empty portfolio. Holdings/positions only appear
    after paper-trading via the paper execution engine.
    """

    _is_mock = True  # Used by market/history.py to route to yfinance

    def __init__(self, passthrough_market_data: bool = True) -> None:
        self._authenticated = False
        self._orders: list[Order] = []
        self._order_counter = 1000
        # Always passthrough to yfinance — no fake market data
        self._passthrough_market_data = passthrough_market_data

    # ── Auth ──────────────────────────────────────────────────

    def get_login_url(self) -> str:
        return "https://mock-broker.local/login?token=DEMO"

    def complete_login(self, **kwargs) -> UserProfile:
        self._authenticated = True
        return UserProfile(
            user_id="PAPER001",
            name="Paper Trader",
            email="paper@tradingplatform.local",
            broker="PAPER",
        )

    def is_authenticated(self) -> bool:
        return self._authenticated

    def logout(self) -> None:
        self._authenticated = False

    # ── Account ───────────────────────────────────────────────

    def get_profile(self) -> UserProfile:
        return UserProfile(
            user_id="PAPER001",
            name="Paper Trader",
            email="paper@tradingplatform.local",
            broker="PAPER",
        )

    def get_funds(self) -> Funds:
        capital = float(os.environ.get("TOTAL_CAPITAL", "200000"))
        return Funds(
            available_cash=capital,
            used_margin=0.0,
            total_balance=capital,
        )

    # ── Portfolio (starts empty — paper trades tracked separately) ──

    def get_holdings(self) -> list[Holding]:
        return []

    def get_positions(self) -> list[Position]:
        return []

    # ── Market Data (always passthrough to yfinance) ──────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        raise NotImplementedError("Mock broker — use yfinance for real quotes")

    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        raise NotImplementedError("Mock broker — use NSE/yfinance for options")

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> OrderResponse:
        oid = f"PAPER{self._order_counter}"
        self._order_counter += 1
        self._orders.append(
            Order(
                order_id=oid,
                symbol=order.symbol,
                exchange=order.exchange,
                transaction_type=order.transaction_type,
                quantity=order.quantity,
                order_type=order.order_type,
                product=order.product,
                status="COMPLETE",
                price=order.price,
                average_price=order.price or 0.0,
                filled_quantity=order.quantity,
                placed_at=datetime.now().strftime("%H:%M:%S"),
            )
        )
        return OrderResponse(
            order_id=oid,
            status="COMPLETE",
            message="Paper order filled",
            average_price=order.price or 0.0,
            filled_quantity=order.quantity,
        )

    def get_orders(self) -> list[Order]:
        return list(self._orders)

    def cancel_order(self, order_id: str) -> bool:
        self._orders = [o for o in self._orders if o.order_id != order_id]
        return True

    # ── Historical Data (passthrough to yfinance) ─────────────

    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: str = "day",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict]:
        raise NotImplementedError("Mock broker — use yfinance for historical data")
