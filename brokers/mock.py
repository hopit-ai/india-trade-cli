"""
brokers/mock.py
───────────────
Mock broker for testing Phase A without real API credentials.
Returns realistic fake data for all BrokerAPI methods.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .base import (
    BrokerAPI, UserProfile, Funds, Holding,
    Position, Quote, OptionsContract,
    OrderRequest, OrderResponse, Order,
)
from market.history import _mock_ohlcv


class MockBrokerAPI(BrokerAPI):
    """
    Fully in-memory fake broker. No network calls, no credentials.
    Good for testing the full login → REPL → command flow.
    """

    def __init__(self, passthrough_market_data: bool = False) -> None:
        self._authenticated = False
        self._orders: list[Order] = []
        self._order_counter = 1000
        # When True, market data methods raise so fallback chain
        # goes to yfinance for real data instead of returning fakes
        self._passthrough_market_data = passthrough_market_data

    # ── Auth ──────────────────────────────────────────────────

    def get_login_url(self) -> str:
        return "https://mock-broker.local/login?token=DEMO"

    def complete_login(self, **kwargs) -> UserProfile:
        self._authenticated = True
        return UserProfile(
            user_id = "MOCK001",
            name    = "Demo Trader",
            email   = "demo@tradingplatform.local",
            broker  = "MOCK",
        )

    def is_authenticated(self) -> bool:
        return self._authenticated

    def logout(self) -> None:
        self._authenticated = False

    # ── Account ───────────────────────────────────────────────

    def get_profile(self) -> UserProfile:
        return UserProfile(
            user_id = "MOCK001",
            name    = "Demo Trader",
            email   = "demo@tradingplatform.local",
            broker  = "MOCK",
        )

    def get_funds(self) -> Funds:
        return Funds(
            available_cash = 1_85_432.50,
            used_margin    = 42_300.00,
            total_balance  = 2_27_732.50,
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        return [
            Holding(
                symbol="RELIANCE",   exchange="NSE", quantity=20,
                avg_price=2650.00,   last_price=2841.35,
                pnl=3827.00,         pnl_pct=7.22,
                day_change=23.50,    day_change_pct=0.83,
            ),
            Holding(
                symbol="HDFCBANK",   exchange="NSE", quantity=50,
                avg_price=1580.00,   last_price=1623.45,
                pnl=2172.50,         pnl_pct=2.75,
                day_change=-8.20,    day_change_pct=-0.50,
            ),
            Holding(
                symbol="INFY",       exchange="NSE", quantity=30,
                avg_price=1720.00,   last_price=1698.80,
                pnl=-636.00,         pnl_pct=-1.23,
                day_change=-15.40,   day_change_pct=-0.90,
            ),
            Holding(
                symbol="TCS",        exchange="NSE", quantity=10,
                avg_price=3800.00,   last_price=4012.60,
                pnl=2126.00,         pnl_pct=5.60,
                day_change=45.00,    day_change_pct=1.13,
            ),
        ]

    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol="NIFTY24APR22900CE", exchange="NFO",
                product="NRML",            quantity=1,
                avg_price=185.00,          last_price=234.50,
                pnl=3712.50,               instrument_type="CE",
                expiry="2024-04-25",       strike=22900.0,
                lot_size=75,
            ),
            Position(
                symbol="BANKNIFTY24APR48000PE", exchange="NFO",
                product="NRML",                quantity=-1,
                avg_price=320.00,              last_price=278.60,
                pnl=1736.00,                   instrument_type="PE",
                expiry="2024-04-18",           strike=48000.0,
                lot_size=15,
            ),
        ]

    # ── Market Data ───────────────────────────────────────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        # In passthrough mode, raise so fallback chain goes to yfinance
        if self._passthrough_market_data:
            raise NotImplementedError("Mock broker — use yfinance for real quotes")
        fake_prices = {
            "NSE:NIFTY 50":    (22847.00, 22700.00, 22920.00, 22650.00, 22720.00, 2_50_00_000),
            "NSE:NIFTY50":     (22847.00, 22700.00, 22920.00, 22650.00, 22720.00, 2_50_00_000),
            "NSE:BANKNIFTY":   (48210.00, 48000.00, 48450.00, 47800.00, 48100.00, 85_00_000),
            "NSE:RELIANCE":    (2841.35,  2820.00,  2860.00,  2810.00,  2817.85,  45_00_000),
            "NSE:HDFCBANK":    (1623.45,  1615.00,  1632.00,  1610.00,  1631.65,  62_00_000),
            "NSE:INFY":        (1698.80,  1690.00,  1715.00,  1685.00,  1714.20,  38_00_000),
            "NSE:TCS":         (4012.60,  3990.00,  4025.00,  3985.00,  3967.60,  22_00_000),
            "NSE:ICICIBANK":   (1095.40,  1085.00,  1102.00,  1080.00,  1087.20,  55_00_000),
            "NSE:SBIN":        (782.30,   775.00,   790.00,   772.00,   778.50,   90_00_000),
            "NSE:WIPRO":       (478.90,   472.00,   483.00,   470.00,   481.20,   28_00_000),
            "NSE:BAJFINANCE":  (6854.00,  6820.00,  6890.00,  6800.00,  6802.50,  18_00_000),
            "NSE:INDIA VIX":   (14.23,    13.80,    14.50,    13.60,    13.95,    0),
        }
        result = {}
        for inst in instruments:
            key  = inst.upper()
            data = fake_prices.get(key, (1000.0, 990.0, 1010.0, 985.0, 998.0, 10_00_000))
            ltp, open_, high, low, close, vol = data
            change     = round(ltp - close, 2)
            change_pct = round(change / close * 100, 2) if close else 0.0
            sym = inst.split(":")[-1] if ":" in inst else inst
            result[inst] = Quote(
                symbol=sym, last_price=ltp, open=open_,
                high=high, low=low, close=close, volume=vol,
                change=change, change_pct=change_pct,
            )
        return result

    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        if self._passthrough_market_data:
            raise NotImplementedError("Mock broker — use NSE/yfinance for options")
        expiry = expiry or "2024-04-25"
        base   = 22850 if underlying == "NIFTY" else 48000
        step   = 50    if underlying == "NIFTY" else 100
        lot    = 75    if underlying == "NIFTY" else 15

        contracts = []
        for i in range(-4, 5):
            strike = base + i * step
            # Simple fake pricing — ATM most expensive, OTM cheaper
            moneyness = abs(i)
            ce_price  = max(5.0, round(200 - moneyness * 40 + (4 - moneyness) * 10, 2))
            pe_price  = max(5.0, round(180 - moneyness * 35 + (4 - moneyness) * 8, 2))
            oi_ce     = max(10000, 500000 - moneyness * 80000)
            oi_pe     = max(10000, 450000 - moneyness * 70000)

            contracts.append(OptionsContract(
                symbol=f"{underlying}{expiry.replace('-','')[2:]}CE{int(strike)}",
                underlying=underlying, expiry=expiry, strike=float(strike),
                option_type="CE", last_price=ce_price, oi=oi_ce,
                oi_change=int(oi_ce * 0.05), volume=int(oi_ce * 0.3),
                iv=round(12.0 + moneyness * 0.8, 1), lot_size=lot,
            ))
            contracts.append(OptionsContract(
                symbol=f"{underlying}{expiry.replace('-','')[2:]}PE{int(strike)}",
                underlying=underlying, expiry=expiry, strike=float(strike),
                option_type="PE", last_price=pe_price, oi=oi_pe,
                oi_change=int(oi_pe * 0.04), volume=int(oi_pe * 0.25),
                iv=round(12.5 + moneyness * 0.9, 1), lot_size=lot,
            ))

        return sorted(contracts, key=lambda c: (c.strike, c.option_type))

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> OrderResponse:
        oid = f"MOCK{self._order_counter}"
        self._order_counter += 1
        self._orders.append(Order(
            order_id=oid, symbol=order.symbol, exchange=order.exchange,
            transaction_type=order.transaction_type, quantity=order.quantity,
            order_type=order.order_type, product=order.product,
            status="COMPLETE", price=order.price,
            average_price=order.price or 0.0,
            filled_quantity=order.quantity, placed_at="09:15:00",
        ))
        return OrderResponse(
            order_id=oid, status="COMPLETE",
            message="Mock order filled instantly",
            average_price=order.price or 0.0,
            filled_quantity=order.quantity,
        )

    def get_orders(self) -> list[Order]:
        # Return some pre-seeded orders + any placed in this session
        seeded = [
            Order(
                order_id="MOCK0901", symbol="RELIANCE", exchange="NSE",
                transaction_type="BUY", quantity=5, order_type="LIMIT",
                product="CNC", status="COMPLETE", price=2820.00,
                average_price=2820.00, filled_quantity=5, placed_at="09:32:14",
            ),
            Order(
                order_id="MOCK0902", symbol="NIFTY24APR22900CE", exchange="NFO",
                transaction_type="BUY", quantity=75, order_type="MARKET",
                product="NRML", status="COMPLETE", price=None,
                average_price=185.00, filled_quantity=75, placed_at="10:05:42",
            ),
        ]
        return seeded + self._orders

    def cancel_order(self, order_id: str) -> bool:
        self._orders = [o for o in self._orders if o.order_id != order_id]
        return True

    # ── Historical Data ──────────────────────────────────────

    def get_historical_data(
        self,
        symbol: str,
        exchange:  str = "NSE",
        interval:  str = "day",
        from_date: Optional[datetime] = None,
        to_date:   Optional[datetime] = None,
    ) -> list[dict]:
        to_date   = to_date   or datetime.now()
        from_date = from_date or datetime(to_date.year - 1, to_date.month, to_date.day)
        try:
            return _mock_ohlcv(symbol, from_date, to_date)
        except Exception as e:
            raise RuntimeError(f"Mock historical data error: {e}") from e
