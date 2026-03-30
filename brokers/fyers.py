"""
brokers/fyers.py
─────────────────
Fyers API v3 implementation of BrokerAPI.

Fyers offers a free developer API with excellent options chain data
and live market feeds. No monthly subscription fee.

Credentials needed (store via `credentials setup`):
    FYERS_APP_ID      — from myapi.fyers.in (format: XXXX-100 or your App ID)
    FYERS_SECRET_KEY  — client secret from app dashboard
    FYERS_REDIRECT_URL — registered redirect URI
                         (default: http://localhost:8765/fyers/callback)

Login flow:
  1. `get_login_url()` returns the Fyers auth URL
  2. User logs in via browser → redirected with ?auth_code=...&state=...
  3. `complete_login(auth_code=...)` exchanges code for access token

Session token is saved to ~/.trading_platform/fyers.json and reused.

Docs: https://myapi.fyers.in/docs
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, date
from pathlib  import Path
from typing   import Optional

import httpx

from brokers.base import (
    BrokerAPI, UserProfile, Funds, Holding, Position,
    Quote, OptionsContract, OrderRequest, OrderResponse, Order,
)

TOKEN_FILE   = Path.home() / ".trading_platform" / "fyers.json"
FYERS_BASE   = "https://api-t1.fyers.in/api/v3"
AUTH_BASE    = "https://api-t2.fyers.in/api/v3"
TOKEN_EXPIRY = 12 * 3600    # Fyers tokens valid ~12 h


class FyersAPI(BrokerAPI):
    """
    Fyers API v3 broker — free, excellent options data.

    Docs: https://myapi.fyers.in/docs
    """

    def __init__(
        self,
        app_id:       str,
        secret_key:   str,
        redirect_uri: str = "http://localhost:8765/fyers/callback",
    ) -> None:
        self._app_id       = app_id
        self._secret_key   = secret_key
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
        # Fyers uses "<app_id>:<access_token>" as the Authorization header
        return {
            "Authorization": f"{self._app_id}:{self._access_token}",
            "Content-Type":  "application/json",
        }

    def _get(self, path: str, **params) -> dict:
        url  = f"{FYERS_BASE}{path}"
        resp = httpx.get(url, headers=self._headers(), params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        url  = f"{FYERS_BASE}{path}"
        resp = httpx.post(url, headers=self._headers(), json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Auth ──────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Returns the Fyers OAuth2 authorization URL."""
        app_hash = hashlib.sha256(
            f"{self._app_id}:{self._secret_key}".encode()
        ).hexdigest()
        return (
            f"{AUTH_BASE}/generate-authcode?"
            f"client_id={self._app_id}&"
            f"redirect_uri={self._redirect_uri}&"
            f"response_type=code&"
            f"state=india_trade_cli&"
            f"nonce={app_hash[:16]}"
        )

    def complete_login(self, auth_code: str = "", **kwargs) -> UserProfile:
        """Exchange the auth code for an access token."""
        # Fyers requires SHA-256 hash of app_id:app_secret for validation
        app_id_hash = hashlib.sha256(
            f"{self._app_id}:{self._secret_key}".encode()
        ).hexdigest()

        resp = httpx.post(
            f"{AUTH_BASE}/validate-authcode",
            json={
                "grant_type": "authorization_code",
                "appIdHash":  app_id_hash,
                "code":       auth_code,
            },
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        token   = payload.get("access_token", "")
        if not token:
            raise RuntimeError(f"Fyers login failed: {payload}")

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
        data    = self._get("/profile")
        payload = data.get("data", {})
        self._profile = UserProfile(
            user_id  = payload.get("fy_id", ""),
            name     = payload.get("name", ""),
            email    = payload.get("email_id", ""),
            broker   = "Fyers",
            metadata = payload,
        )
        return self._profile

    def get_funds(self) -> Funds:
        data    = self._get("/funds")
        payload = data.get("fund_limit", [])
        # fund_limit is a list of {id, title, equityAmount, commodityAmount}
        cash   = next((float(x.get("equityAmount", 0)) for x in payload
                       if x.get("id") == 10), 0.0)   # id=10 → Available Balance
        margin = next((float(x.get("equityAmount", 0)) for x in payload
                       if x.get("id") == 12), 0.0)   # id=12 → Utilised Margin
        total  = next((float(x.get("equityAmount", 0)) for x in payload
                       if x.get("id") == 1), 0.0)    # id=1  → Total Balance
        return Funds(
            available_cash = cash,
            used_margin    = margin,
            total_balance  = total,
            metadata       = {"fund_limit": payload},
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        data     = self._get("/holdings")
        holdings = []
        for item in data.get("holdings", []):
            qty    = int(item.get("quantity", 0))
            avg_px = float(item.get("costPrice", 0))
            ltp    = float(item.get("ltp", avg_px))
            symbol = item.get("symbol", "")
            # symbol format: "NSE:RELIANCE-EQ" → extract ticker
            ticker = symbol.split(":")[-1].split("-")[0] if ":" in symbol else symbol
            holdings.append(Holding(
                symbol         = ticker,
                quantity       = qty,
                avg_price      = avg_px,
                last_price     = ltp,
                pnl            = float(item.get("pl", 0)),
                day_change     = 0.0,
                day_change_pct = 0.0,
                current_value  = ltp * qty,
                isin           = item.get("isin", ""),
            ))
        return holdings

    def get_positions(self) -> list[Position]:
        data      = self._get("/positions")
        positions = []
        for item in data.get("netPositions", []):
            qty = int(item.get("netQty", 0))
            if qty == 0:
                continue
            avg = float(item.get("avgPrice", 0))
            ltp = float(item.get("ltp", avg))
            symbol = item.get("symbol", "")
            ticker = symbol.split(":")[-1].split("-")[0] if ":" in symbol else symbol
            positions.append(Position(
                symbol          = ticker,
                quantity        = qty,
                avg_price       = avg,
                last_price      = ltp,
                pnl             = float(item.get("pl", 0)),
                day_change      = 0.0,
                day_change_pct  = 0.0,
                product         = item.get("productType", "CNC"),
                exchange        = item.get("exchange", "NSE"),
                instrument_type = "EQ",
            ))
        return positions

    # ── Quotes ────────────────────────────────────────────────

    def get_quote(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes. Symbols are in Fyers format: NSE:RELIANCE-EQ"""
        fyers_symbols = [f"NSE:{s}-EQ" for s in symbols]
        try:
            data   = self._get("/quotes", symbols=",".join(fyers_symbols))
            result = {}
            for item in data.get("d", []):
                raw     = item.get("n", "")
                ticker  = raw.split(":")[-1].split("-")[0] if ":" in raw else raw
                v       = item.get("v", {})
                result[ticker] = Quote(
                    symbol     = ticker,
                    last_price = float(v.get("lp", 0)),
                    open       = float(v.get("open_price", 0)),
                    high       = float(v.get("high_price", 0)),
                    low        = float(v.get("low_price", 0)),
                    close      = float(v.get("prev_close_price", 0)),
                    volume     = int(v.get("volume", 0)),
                    oi         = int(v.get("oi", 0)),
                    timestamp  = datetime.now(),
                )
            return result
        except Exception:
            return {s: Quote(symbol=s, last_price=0, open=0, high=0, low=0, close=0,
                             volume=0, oi=0, timestamp=datetime.now()) for s in symbols}

    def get_options_chain(self, underlying: str, expiry: date) -> list[OptionsContract]:
        """Fyers has excellent options chain data via optionchain endpoint."""
        expiry_str = expiry.strftime("%d-%b-%Y").upper()   # e.g. 25-JAN-2025
        try:
            data  = self._get(
                "/data/optionchain",
                symbol=f"NSE:{underlying}-INDEX",
                strikecount=20,
                timestamp=expiry_str,
            )
            chain = []
            for item in data.get("optionsChain", []):
                for opt_type in ["CE", "PE"]:
                    opt = item.get(opt_type, {})
                    if not opt:
                        continue
                    chain.append(OptionsContract(
                        strike      = float(item.get("strikePrice", 0)),
                        expiry      = expiry,
                        option_type = opt_type,
                        last_price  = float(opt.get("ltp", 0)),
                        oi          = int(opt.get("oi", 0)),
                        volume      = int(opt.get("volume", 0)),
                        iv          = float(opt.get("iv", 0)),
                        delta       = float(opt.get("delta", 0)),
                        theta       = float(opt.get("theta", 0)),
                        vega        = float(opt.get("vega", 0)),
                        gamma       = float(opt.get("gamma", 0)),
                    ))
            return chain
        except Exception:
            return []

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, req: OrderRequest) -> OrderResponse:
        product_map = {"CNC": "CNC", "MIS": "INTRADAY", "NRML": "MARGIN"}
        payload = {
            "symbol":          f"NSE:{req.symbol}-EQ",
            "qty":             req.quantity,
            "type":            1 if req.order_type == "MARKET" else 2,
            "side":            1 if req.transaction_type == "BUY" else -1,
            "productType":     product_map.get(req.product, "CNC"),
            "limitPrice":      req.price if req.order_type == "LIMIT" else 0,
            "stopPrice":       req.trigger_price if req.trigger_price else 0,
            "validity":        "DAY",
            "disclosedQty":    0,
            "offlineOrder":    False,
        }
        data = self._post("/orders", payload)
        return OrderResponse(
            order_id = str(data.get("id", "")),
            status   = "OPEN",
            message  = data.get("message", "Order placed"),
            metadata = data,
        )

    def get_orders(self) -> list[Order]:
        data   = self._get("/orders")
        orders = []
        for item in data.get("orderBook", []):
            symbol = item.get("symbol", "")
            ticker = symbol.split(":")[-1].split("-")[0] if ":" in symbol else symbol
            orders.append(Order(
                order_id         = str(item.get("id", "")),
                symbol           = ticker,
                transaction_type = "BUY" if item.get("side", 0) == 1 else "SELL",
                product          = item.get("productType", "CNC"),
                order_type       = "MARKET" if item.get("type") == 1 else "LIMIT",
                quantity         = int(item.get("qty", 0)),
                price            = float(item.get("limitPrice", 0)),
                status           = item.get("status", ""),
                filled_quantity  = int(item.get("filledQty", 0)),
                avg_price        = float(item.get("tradedPrice", 0)),
                timestamp        = datetime.now(),
            ))
        return orders

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = httpx.delete(
                f"{FYERS_BASE}/orders",
                headers=self._headers(),
                json={"id": order_id},
                timeout=15,
            )
            resp.raise_for_status()
            return True
        except Exception:
            return False

    # ── Historical Data ──────────────────────────────────────

    def get_historical_data(
        self,
        symbol:    str,
        exchange:  str = "NSE",
        interval:  str = "day",
        from_date: Optional[datetime] = None,
        to_date:   Optional[datetime] = None,
    ) -> list[dict]:
        resolution_map = {
            "day":      "D",
            "minute":   "1",
            "5minute":  "5",
            "15minute": "15",
            "30minute": "30",
            "60minute": "60",
        }
        resolution = resolution_map.get(interval, "D")
        to_date   = to_date   or datetime.now()
        from_date = from_date or datetime(to_date.year - 1, to_date.month, to_date.day)

        # Fyers symbol format: "NSE:RELIANCE-EQ"
        fyers_symbol = f"{exchange}:{symbol}-EQ"

        try:
            data = self._get("/history", **{
                "symbol":      fyers_symbol,
                "resolution":  resolution,
                "date_format":  "1",
                "range_from":  str(int(from_date.timestamp())),
                "range_to":    str(int(to_date.timestamp())),
                "cont_flag":   "1",
            })

            candles = data.get("candles", [])
            # Each candle: [epoch, open, high, low, close, volume]
            return [
                {
                    "date":   datetime.fromtimestamp(candle[0]),
                    "open":   candle[1],
                    "high":   candle[2],
                    "low":    candle[3],
                    "close":  candle[4],
                    "volume": candle[5],
                }
                for candle in candles
            ]
        except Exception as e:
            raise RuntimeError(f"Fyers historical data error: {e}") from e
