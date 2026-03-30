"""
brokers/base.py
───────────────
Unified broker abstraction. Every broker (Zerodha, Groww, …) must
implement BrokerAPI so the rest of the platform never needs to know
which broker is active.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Shared dataclasses ────────────────────────────────────────────────────────

@dataclass
class UserProfile:
    user_id: str
    name: str
    email: str
    broker: str                     # "ZERODHA" | "GROWW" | "PAPER"


@dataclass
class Funds:
    available_cash: float           # Cash available to trade
    used_margin: float              # Margin currently blocked
    total_balance: float            # Net account value
    currency: str = "INR"


@dataclass
class Holding:
    """A long-term delivery (CNC) position in the portfolio."""
    symbol: str
    exchange: str                   # NSE | BSE
    quantity: int
    avg_price: float
    last_price: float
    pnl: float                      # Unrealised P&L in INR
    pnl_pct: float                  # Unrealised P&L as %
    day_change: float = 0.0         # Today's change in INR
    day_change_pct: float = 0.0


@dataclass
class Position:
    """An open intraday or F&O position."""
    symbol: str
    exchange: str                   # NSE | BSE | NFO | MCX
    product: str                    # CNC | MIS | NRML
    quantity: int                   # Positive = long, negative = short
    avg_price: float
    last_price: float
    pnl: float
    instrument_type: str = "EQ"     # EQ | CE | PE | FUT
    expiry: Optional[str] = None    # For F&O: "YYYY-MM-DD"
    strike: Optional[float] = None  # For options
    lot_size: int = 1


@dataclass
class Quote:
    """Live market snapshot for a single instrument."""
    symbol: str
    last_price: float
    open: float
    high: float
    low: float
    close: float                    # Previous close
    volume: int
    oi: Optional[int] = None        # Open Interest (F&O only)
    bid: Optional[float] = None
    ask: Optional[float] = None
    change: float = 0.0             # Change from prev close in INR
    change_pct: float = 0.0         # Change as %


@dataclass
class OptionsContract:
    """A single row in the options chain."""
    symbol: str                     # Trading symbol e.g. NIFTY24APR22800CE
    underlying: str                 # e.g. NIFTY
    expiry: str                     # "YYYY-MM-DD"
    strike: float
    option_type: str                # CE | PE
    last_price: float
    oi: int                         # Open interest
    oi_change: int                  # OI change vs prev day
    volume: int
    iv: Optional[float] = None      # Implied Volatility (%)
    bid: Optional[float] = None
    ask: Optional[float] = None
    lot_size: int = 1
    exchange: str = "NFO"


@dataclass
class OrderRequest:
    """Parameters for placing an order."""
    symbol: str
    exchange: str                   # NSE | BSE | NFO | MCX
    transaction_type: str           # BUY | SELL
    quantity: int
    order_type: str                 # MARKET | LIMIT | SL | SL-M
    product: str                    # CNC | MIS | NRML
    price: Optional[float] = None   # Required for LIMIT / SL
    trigger_price: Optional[float] = None  # Required for SL / SL-M
    validity: str = "DAY"           # DAY | IOC
    tag: Optional[str] = None       # Custom tag for tracking


@dataclass
class OrderResponse:
    """Result of placing an order."""
    order_id: str
    status: str                     # OPEN | COMPLETE | REJECTED | CANCELLED
    message: str = ""
    average_price: Optional[float] = None
    filled_quantity: int = 0


@dataclass
class Order:
    """A historical or in-flight order."""
    order_id: str
    symbol: str
    exchange: str
    transaction_type: str
    quantity: int
    order_type: str
    product: str
    status: str
    price: Optional[float] = None
    average_price: Optional[float] = None
    filled_quantity: int = 0
    placed_at: Optional[str] = None
    tag: Optional[str] = None


# ── Abstract broker interface ─────────────────────────────────────────────────

class BrokerAPI(ABC):
    """
    Every broker must implement this interface.
    The rest of the platform only talks to BrokerAPI — never to a
    specific broker class directly (except through brokers/session.py).
    """

    # ── Authentication ────────────────────────────────────────

    @abstractmethod
    def get_login_url(self) -> str:
        """Return the OAuth / login URL to open in the browser."""
        ...

    @abstractmethod
    def complete_login(self, **kwargs) -> UserProfile:
        """
        Exchange the auth code / request token for an access token.
        Kwargs vary by broker:
          Zerodha -> request_token: str
          Groww   -> auth_code: str
        Saves the token locally and returns the user profile.
        """
        ...

    @abstractmethod
    def is_authenticated(self) -> bool:
        """True if a valid session token is present and not expired."""
        ...

    @abstractmethod
    def logout(self) -> None:
        """Invalidate the session and delete the local token file."""
        ...

    # ── Account ───────────────────────────────────────────────

    @abstractmethod
    def get_profile(self) -> UserProfile:
        """Return the logged-in user's profile."""
        ...

    @abstractmethod
    def get_funds(self) -> Funds:
        """Return available cash, used margin, and total balance."""
        ...

    # ── Portfolio ─────────────────────────────────────────────

    @abstractmethod
    def get_holdings(self) -> list[Holding]:
        """Return all long-term delivery holdings."""
        ...

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return all open intraday and F&O positions."""
        ...

    # ── Market Data ───────────────────────────────────────────

    @abstractmethod
    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        """
        Return live quotes for a list of instruments.
        Instrument format: "EXCHANGE:SYMBOL" e.g. "NSE:RELIANCE"
        Returns dict keyed by the same instrument strings.
        """
        ...

    @abstractmethod
    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        """
        Return the full options chain for an underlying.
        underlying: e.g. "NIFTY", "BANKNIFTY", "RELIANCE"
        expiry: "YYYY-MM-DD" -- if None, returns nearest expiry.
        """
        ...

    # ── Orders ────────────────────────────────────────────────

    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a new order. Raises on failure."""
        ...

    @abstractmethod
    def get_orders(self) -> list[Order]:
        """Return all orders placed today."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True on success."""
        ...

    # ── Historical Data ────────────────────────────────────────

    def get_historical_data(
        self,
        symbol:    str,
        exchange:  str = "NSE",
        interval:  str = "day",
        from_date: Optional[datetime] = None,
        to_date:   Optional[datetime] = None,
    ) -> list[dict]:
        """
        Return historical OHLCV candles as list of dicts.

        Each dict: {date, open, high, low, close, volume}

        Override in broker subclasses that support historical data.
        Falls back to NotImplementedError so the caller can use mock data.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support historical data"
        )

    # ── Convenience helpers (non-abstract, shared by all) ─────

    def get_ltp(self, instrument: str) -> float:
        """Quick last traded price for a single instrument."""
        quotes = self.get_quote([instrument])
        return quotes[instrument].last_price

    def get_net_pnl(self) -> float:
        """Sum of unrealised P&L across holdings + positions."""
        holdings_pnl  = sum(h.pnl for h in self.get_holdings())
        positions_pnl = sum(p.pnl for p in self.get_positions())
        return round(holdings_pnl + positions_pnl, 2)
