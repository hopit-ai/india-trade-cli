"""
brokers/upstox.py
──────────────────
Upstox API v3 implementation of BrokerAPI.

Upstox offers a free developer API (no monthly fee).
Great for live market data via WebSocket and solid options data.

Credentials needed (store via `credentials setup`):
    UPSTOX_API_KEY    — from developer.upstox.com
    UPSTOX_API_SECRET — client secret from app dashboard
    UPSTOX_REDIRECT_URL — registered redirect URI
                          (default: http://localhost:8765/upstox/callback)

Login flow:
  1. `get_login_url()` returns the Upstox OAuth2 authorize URL
  2. User logs in via browser → redirected to callback URL with ?code=...
  3. `complete_login(auth_code=...)` exchanges the code for access token

Session token is saved to ~/.trading_platform/upstox.json and reused.

Docs: https://upstox.com/developer/api-documentation/
"""

from __future__ import annotations

import json
import time
from datetime import datetime, date, timedelta
from pathlib  import Path
from typing   import Optional

import httpx

from brokers.base import (
    BrokerAPI, UserProfile, Funds, Holding, Position,
    Quote, OptionsContract, OrderRequest, OrderResponse, Order,
)

TOKEN_FILE = Path.home() / ".trading_platform" / "upstox.json"

UPSTOX_BASE   = "https://api.upstox.com/v2"
AUTH_BASE     = "https://api.upstox.com"
TOKEN_EXPIRY  = 6 * 3600          # Upstox tokens typically valid 6 h


class UpstoxAPI(BrokerAPI):
    """
    Upstox API v3 broker.

    Docs: https://upstox.com/developer/api-documentation/
    """

    def __init__(
        self,
        api_key:      str,
        api_secret:   str,
        redirect_uri: str = "http://localhost:8765/upstox/callback",
    ) -> None:
        self._api_key      = api_key
        self._api_secret   = api_secret
        self._redirect_uri = redirect_uri
        self._access_token = ""
        self._profile: Optional[UserProfile] = None
        self._token_ts: float = 0.0
        self._load_token()

    # ── Token persistence ──────────────────────────────────────

    def _load_token(self) -> None:
        try:
            if TOKEN_FILE.exists():
                data = json.loads(TOKEN_FILE.read_text())
                ts   = data.get("timestamp", 0)
                if time.time() - ts < TOKEN_EXPIRY:
                    self._access_token = data.get("access_token", "")
                    self._token_ts     = ts
        except Exception:
            pass

    def _save_token(self, token: str) -> None:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps({
            "access_token": token,
            "timestamp":    time.time(),
        }))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept":        "application/json",
        }

    def _get(self, path: str, **params) -> dict:
        url  = f"{UPSTOX_BASE}{path}"
        resp = httpx.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        url  = f"{UPSTOX_BASE}{path}"
        resp = httpx.post(url, headers={**self._headers(), "Content-Type": "application/json"},
                          json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Auth ──────────────────────────────────────────────────

    def get_login_url(self) -> str:
        return (
            f"{AUTH_BASE}/index/dialog/login?"
            f"client_id={self._api_key}&"
            f"redirect_uri={self._redirect_uri}&"
            "response_type=code"
        )

    def complete_login(self, auth_code: str = "", **kwargs) -> UserProfile:
        """Exchange the auth code received after browser login for an access token."""
        resp = httpx.post(
            f"{AUTH_BASE}/login/authorization/token",
            data={
                "code":          auth_code,
                "client_id":     self._api_key,
                "client_secret": self._api_secret,
                "redirect_uri":  self._redirect_uri,
                "grant_type":    "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        token   = payload.get("access_token", "")
        if not token:
            raise RuntimeError(f"Upstox login failed: {payload}")

        self._access_token = token
        self._token_ts     = time.time()
        self._save_token(token)
        return self.get_profile()

    def is_authenticated(self) -> bool:
        if not self._access_token:
            return False
        if time.time() - self._token_ts >= TOKEN_EXPIRY:
            return False
        try:
            self.get_profile()
            return True
        except Exception:
            return False

    def logout(self) -> None:
        self._access_token = ""
        self._profile      = None
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Profile & Funds ───────────────────────────────────────

    def get_profile(self) -> UserProfile:
        if self._profile:
            return self._profile
        data    = self._get("/user/profile")
        payload = data.get("data", {})
        self._profile = UserProfile(
            user_id  = payload.get("user_id", ""),
            name     = payload.get("user_name", ""),
            email    = payload.get("email", ""),
            broker   = "Upstox",
            metadata = payload,
        )
        return self._profile

    def get_funds(self) -> Funds:
        data    = self._get("/user/fund-margin")
        payload = data.get("data", {})
        equity  = payload.get("equity", {})
        return Funds(
            available_cash = float(equity.get("available_margin", 0)),
            used_margin    = float(equity.get("used_margin", 0)),
            total_balance  = float(equity.get("net", 0)),
            metadata       = payload,
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        data     = self._get("/portfolio/long-term-holdings")
        holdings = []
        for item in data.get("data", []):
            qty     = int(item.get("quantity", 0))
            avg_px  = float(item.get("average_price", 0))
            ltp     = float(item.get("last_price", avg_px))
            isin    = item.get("isin", "")
            symbol  = item.get("tradingsymbol", isin)
            holdings.append(Holding(
                symbol        = symbol,
                quantity      = qty,
                avg_price     = avg_px,
                last_price    = ltp,
                pnl           = (ltp - avg_px) * qty,
                day_change    = 0.0,
                day_change_pct= 0.0,
                current_value = ltp * qty,
                isin          = isin,
            ))
        return holdings

    def get_positions(self) -> list[Position]:
        data      = self._get("/portfolio/short-term-positions")
        positions = []
        for item in data.get("data", []):
            qty   = int(item.get("quantity", 0))
            if qty == 0:
                continue
            avg   = float(item.get("average_price", 0))
            ltp   = float(item.get("last_price", avg))
            positions.append(Position(
                symbol         = item.get("tradingsymbol", ""),
                quantity       = qty,
                avg_price      = avg,
                last_price     = ltp,
                pnl            = float(item.get("pnl", 0)),
                day_change     = 0.0,
                day_change_pct = 0.0,
                product        = item.get("product", "D"),
                exchange       = item.get("exchange", "NSE"),
                instrument_type= item.get("instrument_type", "EQ"),
            ))
        return positions

    # ── Quotes ────────────────────────────────────────────────

    def get_quote(self, symbols: list[str]) -> dict[str, Quote]:
        """Get LTP + OHLC for a list of instrument keys (e.g. NSE_EQ|INE009A01021)."""
        # Upstox uses instrument_key format; fall back to a simple lookup
        instruments = ",".join(f"NSE_EQ|{s}" for s in symbols)
        try:
            data   = self._get("/market-quote/ltp", instrument_key=instruments)
            result = {}
            for sym, q in data.get("data", {}).items():
                tradingsym = sym.split("|")[-1] if "|" in sym else sym
                ltp = float(q.get("last_price", 0))
                result[tradingsym] = Quote(
                    symbol        = tradingsym,
                    last_price    = ltp,
                    open          = ltp,
                    high          = ltp,
                    low           = ltp,
                    close         = ltp,
                    volume        = 0,
                    oi            = 0,
                    timestamp     = datetime.now(),
                )
            return result
        except Exception:
            return {s: Quote(symbol=s, last_price=0, open=0, high=0, low=0, close=0,
                             volume=0, oi=0, timestamp=datetime.now()) for s in symbols}

    def get_options_chain(self, underlying: str, expiry: date) -> list[OptionsContract]:
        """Fetch options chain via Upstox option chain endpoint."""
        expiry_str = expiry.strftime("%Y-%m-%d")
        try:
            data  = self._get(
                "/option/chain",
                instrument_key=f"NSE_INDEX|{underlying}",
                expiry_date=expiry_str,
            )
            chain = []
            for item in data.get("data", []):
                for opt_type, key in [("CE", "call_options"), ("PE", "put_options")]:
                    opt = item.get(key, {})
                    if not opt:
                        continue
                    mkt = opt.get("market_data", {})
                    grk = opt.get("option_greeks", {})
                    chain.append(OptionsContract(
                        strike      = float(item.get("strike_price", 0)),
                        expiry      = expiry,
                        option_type = opt_type,
                        last_price  = float(mkt.get("ltp", 0)),
                        oi          = int(mkt.get("oi", 0)),
                        volume      = int(mkt.get("volume", 0)),
                        iv          = float(grk.get("iv", 0)),
                        delta       = float(grk.get("delta", 0)),
                        theta       = float(grk.get("theta", 0)),
                        vega        = float(grk.get("vega", 0)),
                        gamma       = float(grk.get("gamma", 0)),
                    ))
            return chain
        except Exception:
            return []

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, req: OrderRequest) -> OrderResponse:
        payload = {
            "quantity":         req.quantity,
            "product":          self._map_product(req.product),
            "validity":         "DAY",
            "price":            req.price if req.order_type == "LIMIT" else 0,
            "tag":              "india-trade-cli",
            "instrument_token": f"NSE_EQ|{req.symbol}",
            "order_type":       req.order_type,
            "transaction_type": req.transaction_type,
            "disclosed_quantity": 0,
            "trigger_price":    req.trigger_price if req.trigger_price else 0,
            "is_amo":           False,
        }
        data = self._post("/order/place", payload)
        return OrderResponse(
            order_id = data.get("data", {}).get("order_id", ""),
            status   = "OPEN",
            message  = "Order placed",
            metadata = data,
        )

    def get_orders(self) -> list[Order]:
        data   = self._get("/order/retrieve-all")
        orders = []
        for item in data.get("data", []):
            orders.append(Order(
                order_id         = item.get("order_id", ""),
                symbol           = item.get("tradingsymbol", ""),
                transaction_type = item.get("transaction_type", ""),
                product          = item.get("product", ""),
                order_type       = item.get("order_type", ""),
                quantity         = int(item.get("quantity", 0)),
                price            = float(item.get("price", 0)),
                status           = item.get("status", ""),
                filled_quantity  = int(item.get("filled_quantity", 0)),
                avg_price        = float(item.get("average_price", 0)),
                timestamp        = datetime.fromisoformat(item["order_timestamp"])
                                   if item.get("order_timestamp") else datetime.now(),
            ))
        return orders

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._delete(f"/order/cancel", order_id=order_id)
            return True
        except Exception:
            return False

    def _delete(self, path: str, **params) -> dict:
        url  = f"{UPSTOX_BASE}{path}"
        resp = httpx.delete(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Historical Data ──────────────────────────────────────

    def get_historical_data(
        self,
        symbol:    str,
        exchange:  str = "NSE",
        interval:  str = "day",
        from_date: Optional[datetime] = None,
        to_date:   Optional[datetime] = None,
    ) -> list[dict]:
        interval_map = {
            "day":      "1d",
            "minute":   "1minute",
            "5minute":  "5minute",
            "15minute": "15minute",
            "30minute": "30minute",
            "60minute": "60minute",
        }
        upstox_interval = interval_map.get(interval, "1d")
        to_date   = to_date   or datetime.now()
        from_date = from_date or datetime(to_date.year - 1, to_date.month, to_date.day)

        to_str   = to_date.strftime("%Y-%m-%d")
        from_str = from_date.strftime("%Y-%m-%d")

        # Upstox instrument key format for equities: NSE_EQ|<symbol>
        exchange_seg = f"{exchange}_EQ"
        instrument_key = f"{exchange_seg}|{symbol}"

        try:
            url = f"{UPSTOX_BASE}/historical-candle/{instrument_key}/{upstox_interval}/{to_str}/{from_str}"
            resp = httpx.get(url, headers=self._headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()

            candles = data.get("data", {}).get("candles", [])
            # Each candle: [timestamp, open, high, low, close, volume, oi]
            return [
                {
                    "date":   candle[0],
                    "open":   candle[1],
                    "high":   candle[2],
                    "low":    candle[3],
                    "close":  candle[4],
                    "volume": candle[5],
                }
                for candle in candles
            ]
        except Exception as e:
            raise RuntimeError(f"Upstox historical data error: {e}") from e

    # ── Helpers ───────────────────────────────────────────────

    def _map_product(self, product: str) -> str:
        return {
            "CNC": "D",    # Delivery
            "MIS": "I",    # Intraday
            "NRML": "D",   # Normal (F&O)
        }.get(product.upper(), "D")
