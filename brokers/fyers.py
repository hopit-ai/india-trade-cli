"""
brokers/fyers.py
─────────────────
Fyers API v3 implementation of BrokerAPI using the official fyers-apiv3 SDK.

Fyers offers a free developer API with excellent options chain data
and live market feeds. No monthly subscription fee.

Credentials needed (store via `credentials setup`):
    FYERS_APP_ID      — from myapi.fyers.in (format: XXXX-100 or your App ID)
    FYERS_SECRET_KEY  — client secret from app dashboard
    FYERS_REDIRECT_URL — registered redirect URI
                         (default: http://127.0.0.1:8765/fyers/callback)

Login flow:
  1. `get_login_url()` returns the Fyers auth URL
  2. User logs in via browser → redirected with ?auth_code=...&state=...
  3. `complete_login(auth_code=...)` exchanges code for access token

Session token is saved to ~/.trading_platform/fyers.json and reused.

Install: pip install fyers-apiv3

Docs: https://myapi.fyers.in/docsv3
"""

from __future__ import annotations

import json
import time
from datetime import datetime, date
from pathlib  import Path
from typing   import Optional

from brokers.base import (
    BrokerAPI, UserProfile, Funds, Holding, Position,
    Quote, OptionsContract, OrderRequest, OrderResponse, Order,
)

TOKEN_FILE   = Path.home() / ".trading_platform" / "fyers.json"
TOKEN_EXPIRY = 12 * 3600    # Fyers tokens valid ~12 h

# ── Symbol mapping (instrument format → Fyers format) ────────

_FYERS_INDEX_MAP = {
    "NIFTY 50":          "NSE:NIFTY50-INDEX",
    "NIFTY":             "NSE:NIFTY50-INDEX",
    "NIFTY50":           "NSE:NIFTY50-INDEX",
    "NIFTY BANK":        "NSE:NIFTYBANK-INDEX",
    "BANKNIFTY":         "NSE:NIFTYBANK-INDEX",
    "INDIA VIX":         "NSE:INDIAVIX-INDEX",
    "VIX":               "NSE:INDIAVIX-INDEX",
    "SENSEX":            "BSE:SENSEX-INDEX",
    "NIFTY IT":          "NSE:NIFTYIT-INDEX",
    "NIFTY PHARMA":      "NSE:CNXPHARMA-INDEX",
    "NIFTY AUTO":        "NSE:CNXAUTO-INDEX",
    "NIFTY FMCG":        "NSE:CNXFMCG-INDEX",
    "NIFTY REALTY":      "NSE:CNXREALTY-INDEX",
    "NIFTY METAL":       "NSE:CNXMETAL-INDEX",
    "NIFTY ENERGY":      "NSE:CNXENERGY-INDEX",
    "NIFTY FIN SERVICE": "NSE:CNXFIN-INDEX",
    "NIFTY MIDCAP 100":  "NSE:MIDCAP100-INDEX",
    "FINNIFTY":          "NSE:FINNIFTY-INDEX",
}

_INDEX_KEYWORDS = {"NIFTY", "SENSEX", "VIX", "MIDCAP", "FINNIFTY", "BANKNIFTY",
                   "PHARMA", "AUTO", "FMCG", "REALTY", "METAL", "ENERGY"}


def _to_fyers_symbol(instrument: str) -> str:
    """Convert 'NSE:RELIANCE' or 'NSE:NIFTY 50' to Fyers API format."""
    if ":" in instrument:
        exch, sym = instrument.split(":", 1)
    else:
        exch, sym = "NSE", instrument

    sym_upper = sym.upper().strip()

    # Check index map
    if sym_upper in _FYERS_INDEX_MAP:
        return _FYERS_INDEX_MAP[sym_upper]

    # Already has suffix
    if "-" in sym:
        return instrument

    # Check if it's an index by keywords
    if any(kw in sym_upper for kw in _INDEX_KEYWORDS):
        clean = sym_upper.replace(" ", "")
        return f"{exch}:{clean}-INDEX"

    return f"{exch}:{sym}-EQ"


def _get_sdk():
    """Lazy import fyers SDK."""
    try:
        from fyers_apiv3 import fyersModel
        return fyersModel
    except ImportError:
        raise RuntimeError(
            "fyers-apiv3 not installed. Run:\n"
            "  pip install fyers-apiv3"
        )


class FyersAPI(BrokerAPI):
    """
    Fyers API v3 broker — free, excellent options data.
    Uses the official fyers-apiv3 SDK for all API calls.

    Docs: https://myapi.fyers.in/docsv3
    """

    def __init__(
        self,
        app_id:       str,
        secret_key:   str,
        redirect_uri: str = "http://127.0.0.1:8765/fyers/callback",
    ) -> None:
        self._app_id       = app_id
        self._secret_key   = secret_key
        self._redirect_uri = redirect_uri
        self._access_token = ""
        self._profile: Optional[UserProfile] = None
        self._token_ts: float = 0.0
        self._fyers = None   # FyersModel instance
        self._load_token()

    # ── SDK Instance ─────────────────────────────────────────

    def _get_fyers(self):
        """Get or create the FyersModel SDK instance."""
        if self._fyers is None and self._access_token:
            fyersModel = _get_sdk()
            self._fyers = fyersModel.FyersModel(
                token=self._access_token,
                client_id=self._app_id,
                log_path="",
            )
        return self._fyers

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

    # ── Auth ──────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Returns the Fyers OAuth2 authorization URL using the official SDK."""
        fyersModel = _get_sdk()
        session = fyersModel.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret_key,
            redirect_uri=self._redirect_uri,
            response_type="code",
            grant_type="authorization_code",
            state="india_trade_cli",
        )
        return session.generate_authcode()

    def complete_login(self, auth_code: str = "", **kwargs) -> UserProfile:
        """Exchange the auth code for an access token using the SDK."""
        fyersModel = _get_sdk()
        session = fyersModel.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret_key,
            redirect_uri=self._redirect_uri,
            response_type="code",
            grant_type="authorization_code",
            state="india_trade_cli",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        token = response.get("access_token", "")
        if not token:
            error_msg = response.get("message", "Unknown error")
            if "invalid app id" in error_msg.lower() or "app id hash" in error_msg.lower():
                raise RuntimeError(
                    f"Fyers login failed: {error_msg}\n"
                    "Your App ID and Secret Key don't match. To fix:\n"
                    "  trade\n"
                    "  > credentials delete FYERS_APP_ID\n"
                    "  > credentials delete FYERS_SECRET_KEY\n"
                    "  > login\n"
                    "Then re-enter the correct values from myapi.fyers.in"
                )
            raise RuntimeError(
                f"Fyers login failed: {error_msg}\n"
                "Possible causes: expired auth code, wrong redirect URL, or network issue.\n"
                "Try logging in again. If it persists, verify your app config at myapi.fyers.in\n"
                "and ensure Redirect URL is exactly: http://127.0.0.1:8765/fyers/callback"
            )

        self._access_token = token
        self._token_ts     = time.time()
        self._fyers        = None  # reset so it gets recreated with new token
        self._save_token(token)
        return self.get_profile()

    def is_authenticated(self) -> bool:
        if not self._access_token:
            return False
        if self._token_ts and time.time() - self._token_ts >= TOKEN_EXPIRY:
            self._access_token = ""
            self._fyers = None
            try:
                TOKEN_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            return False
        # Token exists and is < 12 hours old — trust it (no API call)
        return True

    def logout(self) -> None:
        try:
            fyers = self._get_fyers()
            if fyers:
                fyers.logout()
        except Exception:
            pass
        self._access_token = ""
        self._profile      = None
        self._fyers        = None
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # ── Profile & Funds ───────────────────────────────────────

    def get_profile(self) -> UserProfile:
        if self._profile:
            return self._profile
        fyers = self._get_fyers()
        data = fyers.get_profile()
        payload = data.get("data", {})
        self._profile = UserProfile(
            user_id  = payload.get("fy_id", ""),
            name     = payload.get("name", ""),
            email    = payload.get("email_id", ""),
            broker   = "Fyers",
        )
        return self._profile

    def get_funds(self) -> Funds:
        fyers = self._get_fyers()
        data = fyers.funds()
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
        )

    # ── Portfolio ─────────────────────────────────────────────

    def get_holdings(self) -> list[Holding]:
        fyers = self._get_fyers()
        data = fyers.holdings()
        holdings = []
        for item in data.get("holdings", []):
            qty    = int(item.get("quantity", 0))
            avg_px = float(item.get("costPrice", 0))
            ltp    = float(item.get("ltp", avg_px))
            symbol = item.get("symbol", "")
            ticker = symbol.split(":")[-1].split("-")[0] if ":" in symbol else symbol
            pnl    = float(item.get("pl", 0))
            pnl_pct = ((ltp - avg_px) / avg_px * 100) if avg_px else 0.0
            holdings.append(Holding(
                symbol         = ticker,
                exchange       = "NSE",
                quantity       = qty,
                avg_price      = avg_px,
                last_price     = ltp,
                pnl            = pnl,
                pnl_pct        = round(pnl_pct, 2),
                day_change     = 0.0,
                day_change_pct = 0.0,
            ))
        return holdings

    def get_positions(self) -> list[Position]:
        fyers = self._get_fyers()
        data = fyers.positions()
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
                exchange        = item.get("exchange", "NSE"),
                product         = item.get("productType", "CNC"),
                quantity        = qty,
                avg_price       = avg,
                last_price      = ltp,
                pnl             = float(item.get("pl", 0)),
                instrument_type = "EQ",
            ))
        return positions

    # ── Quotes ────────────────────────────────────────────────

    def get_quote(self, instruments: list[str]) -> dict[str, Quote]:
        """
        Get quotes. Instruments: ["NSE:RELIANCE", "NSE:NIFTY 50"]
        Fyers format: "NSE:RELIANCE-EQ", "NSE:NIFTY50-INDEX"
        """
        fyers = self._get_fyers()

        # Convert to Fyers symbol format
        fyers_symbols = []
        key_map = {}   # fyers_symbol → original instrument key
        for inst in instruments:
            fyers_sym = _to_fyers_symbol(inst)
            fyers_symbols.append(fyers_sym)
            key_map[fyers_sym] = inst

        try:
            data = fyers.quotes({"symbols": ",".join(fyers_symbols)})
            result = {}
            for item in data.get("d", []):
                raw    = item.get("n", "")
                v      = item.get("v", {})
                # Find the original key
                orig_key = key_map.get(raw, raw)
                result[orig_key] = Quote(
                    symbol     = orig_key.split(":")[-1] if ":" in orig_key else orig_key,
                    last_price = float(v.get("lp", 0)),
                    open       = float(v.get("open_price", 0)),
                    high       = float(v.get("high_price", 0)),
                    low        = float(v.get("low_price", 0)),
                    close      = float(v.get("prev_close_price", 0)),
                    volume     = int(v.get("volume", 0)),
                    change     = float(v.get("ch", 0)),
                    change_pct = float(v.get("chp", 0)),
                )
            return result
        except Exception:
            return {}

    def get_ltp(self, instrument: str) -> float:
        quotes = self.get_quote([instrument])
        q = quotes.get(instrument)
        return q.last_price if q else 0.0

    def get_options_chain(
        self,
        underlying: str,
        expiry: Optional[str] = None,
    ) -> list[OptionsContract]:
        """Fyers options chain via SDK."""
        fyers = self._get_fyers()
        try:
            # Determine symbol format
            if underlying.upper() in ("NIFTY", "NIFTY50", "NIFTY 50"):
                fyers_sym = "NSE:NIFTY50-INDEX"
            elif underlying.upper() in ("BANKNIFTY", "NIFTY BANK"):
                fyers_sym = "NSE:NIFTYBANK-INDEX"
            else:
                fyers_sym = f"NSE:{underlying}-EQ"

            params = {"symbol": fyers_sym, "strikecount": 20}
            if expiry:
                params["timestamp"] = expiry

            data = fyers.optionchain(params)
            chain = []
            for item in data.get("data", {}).get("optionsChain", []):
                for opt_type in ["CE", "PE"]:
                    opt = item.get(opt_type, item) if opt_type in str(item.get("option_type", "")) else None
                    if not opt and item.get("option_type") == opt_type:
                        opt = item
                    if not opt:
                        continue
                    chain.append(OptionsContract(
                        symbol      = opt.get("symbol", ""),
                        underlying  = underlying,
                        expiry      = opt.get("expiry", expiry or ""),
                        strike      = float(opt.get("strike_price", item.get("strikePrice", 0))),
                        option_type = opt_type,
                        last_price  = float(opt.get("ltp", 0)),
                        oi          = int(opt.get("oi", 0)),
                        oi_change   = int(opt.get("oiChange", 0)),
                        volume      = int(opt.get("volume", 0)),
                        iv          = float(opt.get("iv", 0)) or None,
                        lot_size    = int(opt.get("lotSize", 50)),
                        exchange    = "NFO",
                    ))
            return chain
        except Exception:
            return []

    # ── Orders ────────────────────────────────────────────────

    def place_order(self, req: OrderRequest) -> OrderResponse:
        fyers = self._get_fyers()
        product_map = {"CNC": "CNC", "MIS": "INTRADAY", "NRML": "MARGIN"}
        payload = {
            "symbol":       f"NSE:{req.symbol}-EQ",
            "qty":          req.quantity,
            "type":         1 if req.order_type == "MARKET" else 2,
            "side":         1 if req.transaction_type == "BUY" else -1,
            "productType":  product_map.get(req.product, "CNC"),
            "limitPrice":   req.price if req.order_type == "LIMIT" else 0,
            "stopPrice":    req.trigger_price if req.trigger_price else 0,
            "validity":     "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        data = fyers.place_order(payload)
        return OrderResponse(
            order_id = str(data.get("id", "")),
            status   = "OPEN",
            message  = data.get("message", "Order placed"),
        )

    def get_orders(self) -> list[Order]:
        fyers = self._get_fyers()
        data = fyers.orderbook()
        orders = []
        for item in data.get("orderBook", []):
            symbol = item.get("symbol", "")
            ticker = symbol.split(":")[-1].split("-")[0] if ":" in symbol else symbol
            orders.append(Order(
                order_id         = str(item.get("id", "")),
                symbol           = ticker,
                exchange         = "NSE",
                transaction_type = "BUY" if item.get("side", 0) == 1 else "SELL",
                quantity         = int(item.get("qty", 0)),
                order_type       = "MARKET" if item.get("type") == 1 else "LIMIT",
                product          = item.get("productType", "CNC"),
                status           = str(item.get("status", "")),
                price            = float(item.get("limitPrice", 0)) or None,
                average_price    = float(item.get("tradedPrice", 0)) or None,
                filled_quantity  = int(item.get("filledQty", 0)),
            ))
        return orders

    def cancel_order(self, order_id: str) -> bool:
        fyers = self._get_fyers()
        try:
            data = fyers.cancel_order({"id": order_id})
            return data.get("s") == "ok"
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
        fyers = self._get_fyers()
        resolution_map = {
            "day": "D", "minute": "1", "5minute": "5",
            "15minute": "15", "30minute": "30", "60minute": "60",
        }
        resolution = resolution_map.get(interval, "D")
        to_date   = to_date   or datetime.now()
        from_date = from_date or datetime(to_date.year - 1, to_date.month, to_date.day)

        fyers_symbol = _to_fyers_symbol(f"{exchange}:{symbol}")

        try:
            data = fyers.history({
                "symbol":     fyers_symbol,
                "resolution": resolution,
                "date_format": "1",
                "range_from": str(int(from_date.timestamp())),
                "range_to":   str(int(to_date.timestamp())),
                "cont_flag":  "1",
            })

            candles = data.get("candles", [])
            return [
                {
                    "date":   datetime.fromtimestamp(c[0]),
                    "open":   c[1],
                    "high":   c[2],
                    "low":    c[3],
                    "close":  c[4],
                    "volume": c[5],
                }
                for c in candles
            ]
        except Exception as e:
            raise RuntimeError(
                f"Fyers historical data error: {e}\n"
                "Check that the symbol and date range are valid. If your session expired, try: logout → login"
            ) from e
