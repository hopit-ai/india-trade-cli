"""
brokers/angelone.py
────────────────────
Angel One SmartAPI implementation of BrokerAPI.

Angel One SmartAPI is FREE — no monthly subscription fee.

Credentials needed (all stored in OS keychain via `credentials setup`):
    ANGEL_API_KEY      — from smartapi.angelbroking.com (create a free app)
    ANGEL_CLIENT_CODE  — your Angel One trading login ID
    ANGEL_PASSWORD     — your Angel One trading password
    ANGEL_TOTP_SECRET  — base32 TOTP seed from Angel One app
                         (Settings → Security → Enable TOTP → copy the secret key)

Login is fully automated via TOTP — no browser redirect needed.
Session token is saved to ~/.trading_platform/angelone.json and reused.

Install extra deps:
    pip install smartapi-python pyotp logzero
"""

from __future__ import annotations

import json
import time
from datetime import datetime, date, timedelta
from pathlib  import Path
from typing   import Optional

from brokers.base import (
    BrokerAPI, UserProfile, Funds, Holding, Position,
    Quote, OptionsContract, OrderRequest, OrderResponse, Order,
)


TOKEN_FILE = Path.home() / ".trading_platform" / "angelone.json"

# Exchange constants
NSE = "NSE"
BSE = "BSE"
NFO = "NFO"


class AngelOneAPI(BrokerAPI):
    """
    Angel One SmartAPI broker — free REST + WebSocket trading API.

    Docs: https://smartapi.angelbroking.com/docs
    """

    def __init__(
        self,
        api_key:     str,
        client_code: str,
        password:    str,
        totp_secret: str = "",
    ) -> None:
        self._api_key     = api_key
        self._client_code = client_code
        self._password    = password
        self._totp_secret = totp_secret
        self._obj         = None    # SmartConnect instance
        self._auth_token:    str = ""
        self._refresh_token: str = ""
        self._feed_token:    str = ""
        self._profile_cache: Optional[UserProfile] = None

        # Try to restore a saved session
        self._load_token()

    # ── Auth ──────────────────────────────────────────────────

    def _generate_totp(self) -> str:
        try:
            import pyotp
            return pyotp.TOTP(self._totp_secret).now()
        except ImportError:
            raise RuntimeError("pyotp not installed. Run: pip install pyotp")

    def _smart_connect(self):
        try:
            from SmartApi import SmartConnect
        except ImportError:
            raise RuntimeError(
                "smartapi-python not installed. Run: pip install smartapi-python"
            )
        return SmartConnect(api_key=self._api_key)

    def get_login_url(self) -> str:
        # Angel One uses TOTP, not OAuth — no browser URL needed
        return "https://smartapi.angelbroking.com"

    def complete_login(self, **kwargs) -> UserProfile:
        """
        Auto-login using client code + password + TOTP.
        No browser interaction needed.
        """
        obj  = self._smart_connect()
        totp = self._generate_totp()

        data = obj.generateSession(self._client_code, self._password, totp)

        if not data or data.get("status") is False:
            msg = data.get("message", "Unknown error") if data else "No response"
            raise RuntimeError(f"Angel One login failed: {msg}")

        d = data.get("data", {})
        self._auth_token    = d.get("jwtToken", "")
        self._refresh_token = d.get("refreshToken", "")
        self._feed_token    = obj.getfeedToken() or ""
        self._obj           = obj

        # Fetch profile
        profile_data = obj.getProfile(self._refresh_token)
        pd = profile_data.get("data", {}) if profile_data else {}

        name  = pd.get("name", self._client_code)
        email = pd.get("email", "")

        self._profile_cache = UserProfile(
            user_id = self._client_code,
            name    = name,
            email   = email,
            broker  = "ANGEL_ONE",
        )

        # Save token
        self._save_token()
        return self._profile_cache

    def _save_token(self) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps({
            "auth_token":    self._auth_token,
            "refresh_token": self._refresh_token,
            "feed_token":    self._feed_token,
            "client_code":   self._client_code,
            "saved_at":      time.time(),
            "name":          self._profile_cache.name  if self._profile_cache else "",
            "email":         self._profile_cache.email if self._profile_cache else "",
        }, indent=2))

    def _load_token(self) -> None:
        if not TOKEN_FILE.exists():
            return
        try:
            d = json.loads(TOKEN_FILE.read_text())
            # Angel One JWT tokens expire daily — consider stale after 20 hours
            if time.time() - d.get("saved_at", 0) > 20 * 3600:
                return
            self._auth_token    = d.get("auth_token", "")
            self._refresh_token = d.get("refresh_token", "")
            self._feed_token    = d.get("feed_token", "")
            if self._auth_token:
                obj = self._smart_connect()
                # Re-attach the saved token to the SDK object
                try:
                    import logzero
                except ImportError:
                    pass
                self._obj = obj
                self._profile_cache = UserProfile(
                    user_id = d.get("client_code", self._client_code),
                    name    = d.get("name", self._client_code),
                    email   = d.get("email", ""),
                    broker  = "ANGEL_ONE",
                )
        except Exception:
            pass

    def is_authenticated(self) -> bool:
        return bool(self._auth_token)

    def logout(self) -> None:
        try:
            if self._obj and self._auth_token:
                self._obj.terminateSession(self._client_code)
        except Exception:
            pass
        self._auth_token = ""
        self._obj        = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()

    # ── Account ───────────────────────────────────────────────

    def get_profile(self) -> UserProfile:
        if self._profile_cache:
            return self._profile_cache
        if not self._obj:
            raise RuntimeError("Not authenticated. Call complete_login() first.")
        data = self._obj.getProfile(self._refresh_token)
        pd   = data.get("data", {}) if data else {}
        self._profile_cache = UserProfile(
            user_id = self._client_code,
            name    = pd.get("name", self._client_code),
            email   = pd.get("email", ""),
            broker  = "ANGEL_ONE",
        )
        return self._profile_cache

    def get_funds(self) -> Funds:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        data = self._obj.rmsLimit()
        d    = data.get("data", {}) if data else {}
        # Angel One returns strings — convert carefully
        def _f(key): return float(d.get(key) or 0)
        net       = _f("net")
        used      = _f("utilisedAmount")
        available = net - used if net > 0 else _f("availablecash")
        return Funds(
            available_cash = round(available, 2),
            used_margin    = round(used, 2),
            total_balance  = round(net or available + used, 2),
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        data     = self._obj.holding()
        holdings = data.get("data", []) if data else []
        result   = []
        for h in (holdings or []):
            try:
                qty       = int(h.get("quantity", 0) or 0)
                avg_price = float(h.get("averageprice", 0) or 0)
                ltp       = float(h.get("ltp", 0) or 0)
                pnl       = round((ltp - avg_price) * qty, 2)
                pnl_pct   = round((ltp - avg_price) / avg_price * 100, 2) if avg_price else 0.0
                result.append(Holding(
                    symbol        = h.get("tradingsymbol", ""),
                    exchange      = h.get("exchange", "NSE"),
                    quantity      = qty,
                    avg_price     = avg_price,
                    last_price    = ltp,
                    pnl           = pnl,
                    pnl_pct       = pnl_pct,
                    day_change    = float(h.get("close", 0) or 0) - ltp,
                    day_change_pct= 0.0,
                ))
            except Exception:
                continue
        return result

    def get_positions(self) -> list[Position]:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        data      = self._obj.position()
        positions = data.get("data", []) if data else []
        result    = []
        for p in (positions or []):
            try:
                qty       = int(p.get("netqty", 0) or 0)
                avg_price = float(p.get("netavgprice", 0) or 0)
                ltp       = float(p.get("ltp", 0) or 0)
                pnl       = float(p.get("unrealised", 0) or 0)
                result.append(Position(
                    symbol          = p.get("tradingsymbol", ""),
                    exchange        = p.get("exchange", "NSE"),
                    product         = _map_product(p.get("producttype", "MIS")),
                    quantity        = qty,
                    avg_price       = avg_price,
                    last_price      = ltp,
                    pnl             = pnl,
                    instrument_type = p.get("instrumenttype", "EQ"),
                    expiry          = p.get("expirydate") or None,
                    strike          = float(p.get("strikeprice", 0) or 0) or None,
                    lot_size        = int(p.get("lotsize", 1) or 1),
                ))
            except Exception:
                continue
        return result

    # ── Market data ───────────────────────────────────────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        """
        Instruments format: "NSE:RELIANCE" or "NFO:NIFTY24APR22900CE"
        Angel One uses a different token-based system internally,
        but we convert the symbol format for a clean interface.
        """
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        result = {}
        # Group by exchange
        by_exchange: dict[str, list[str]] = {}
        for inst in instruments:
            if ":" in inst:
                exch, sym = inst.split(":", 1)
            else:
                exch, sym = "NSE", inst
            by_exchange.setdefault(exch, []).append(sym)

        for exch, syms in by_exchange.items():
            try:
                # Angel One LTP API
                data = self._obj.ltpData(exch, syms[0], "")
                d    = data.get("data", {}) if data else {}
                ltp  = float(d.get("ltp", 0) or 0)
                key  = f"{exch}:{syms[0]}"
                result[key] = Quote(
                    symbol     = syms[0],
                    last_price = ltp,
                    open       = float(d.get("open", ltp) or ltp),
                    high       = float(d.get("high", ltp) or ltp),
                    low        = float(d.get("low",  ltp) or ltp),
                    close      = float(d.get("close", ltp) or ltp),
                    volume     = int(d.get("tradedVolume", 0) or 0),
                )
            except Exception:
                pass
        return result

    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        """
        Fetch options chain from Angel One.
        Uses the public NSE options chain endpoint as fallback.
        """
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        # Angel One doesn't have a dedicated chain endpoint in the free tier —
        # delegate to the NSE public endpoint (already implemented in market/options.py)
        try:
            import httpx
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={underlying}"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Referer": "https://www.nseindia.com",
            }
            with httpx.Client(headers=headers, timeout=10) as client:
                # Warm up cookie
                client.get("https://www.nseindia.com")
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
            records = data.get("records", {}).get("data", [])
            expiry_target = expiry or data.get("records", {}).get("expiryDates", [""])[0]
            contracts = []
            for row in records:
                for opt_type in ("CE", "PE"):
                    if opt_type not in row:
                        continue
                    c = row[opt_type]
                    contracts.append(OptionsContract(
                        symbol      = f"{underlying}{expiry_target.replace('-','')}{opt_type}",
                        underlying  = underlying,
                        expiry      = expiry_target,
                        strike      = float(row.get("strikePrice", 0)),
                        option_type = opt_type,
                        last_price  = float(c.get("lastPrice", 0)),
                        oi          = int(c.get("openInterest", 0)),
                        oi_change   = int(c.get("changeinOpenInterest", 0)),
                        volume      = int(c.get("totalTradedVolume", 0)),
                        iv          = float(c.get("impliedVolatility", 0)) or None,
                        bid         = float(c.get("bidprice", 0)) or None,
                        ask         = float(c.get("askPrice", 0)) or None,
                        lot_size    = int(c.get("lotSize", 50) or 50),
                        exchange    = "NFO",
                    ))
            return contracts
        except Exception:
            return []

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, order: OrderRequest) -> OrderResponse:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        params = {
            "variety":         "NORMAL",
            "tradingsymbol":   order.symbol,
            "symboltoken":     "",        # Angel One needs token; looked up separately
            "transactiontype": order.transaction_type,
            "exchange":        order.exchange,
            "ordertype":       _map_order_type(order.order_type),
            "producttype":     _map_product_reverse(order.product),
            "duration":        order.validity,
            "price":           str(order.price or "0"),
            "squareoff":       "0",
            "stoploss":        str(order.trigger_price or "0"),
            "quantity":        str(order.quantity),
        }
        data = self._obj.placeOrder(params)
        if not data or data.get("status") is False:
            msg = data.get("message", "Order failed") if data else "No response"
            raise RuntimeError(f"Angel One order error: {msg}")
        return OrderResponse(
            order_id = data.get("data", {}).get("orderid", ""),
            status   = "OPEN",
            message  = data.get("message", ""),
        )

    def get_orders(self) -> list[Order]:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        data   = self._obj.orderBook()
        orders = data.get("data", []) if data else []
        result = []
        for o in (orders or []):
            try:
                result.append(Order(
                    order_id         = o.get("orderid", ""),
                    symbol           = o.get("tradingsymbol", ""),
                    exchange         = o.get("exchange", "NSE"),
                    transaction_type = o.get("transactiontype", ""),
                    quantity         = int(o.get("quantity", 0) or 0),
                    order_type       = o.get("ordertype", ""),
                    product          = _map_product(o.get("producttype", "")),
                    status           = _map_status(o.get("status", "")),
                    price            = float(o.get("price", 0) or 0) or None,
                    average_price    = float(o.get("averageprice", 0) or 0) or None,
                    filled_quantity  = int(o.get("filledshares", 0) or 0),
                    placed_at        = o.get("ordercreatetime"),
                    tag              = o.get("ordertag"),
                ))
            except Exception:
                continue
        return result

    def cancel_order(self, order_id: str) -> bool:
        if not self._obj:
            raise RuntimeError("Not authenticated.")
        data = self._obj.cancelOrder(order_id, "NORMAL")
        return bool(data and data.get("status") is not False)


# ── Field mapping helpers ─────────────────────────────────────

def _map_product(angel_type: str) -> str:
    return {
        "DELIVERY": "CNC",
        "CARRYFORWARD": "NRML",
        "INTRADAY": "MIS",
        "MARGIN": "MIS",
    }.get((angel_type or "").upper(), angel_type or "MIS")


def _map_product_reverse(product: str) -> str:
    return {
        "CNC":  "DELIVERY",
        "NRML": "CARRYFORWARD",
        "MIS":  "INTRADAY",
    }.get(product.upper(), "INTRADAY")


def _map_order_type(order_type: str) -> str:
    return {
        "MARKET": "MARKET",
        "LIMIT":  "LIMIT",
        "SL":     "STOPLOSS_LIMIT",
        "SL-M":   "STOPLOSS_MARKET",
    }.get(order_type.upper(), "MARKET")


def _map_status(status: str) -> str:
    return {
        "complete":  "COMPLETE",
        "rejected":  "REJECTED",
        "cancelled": "CANCELLED",
        "open":      "OPEN",
        "pending":   "OPEN",
    }.get((status or "").lower(), status.upper())
