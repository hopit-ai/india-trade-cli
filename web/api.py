"""
web/api.py
──────────
FastAPI web server — browser-based login for all supported brokers.

Run with:
    uvicorn web.api:app --host 127.0.0.1 --port 8765
    # or from the REPL:
    trade ❯ web

Security note: bind to 127.0.0.1 (default) for local-only access.
Only expose on 0.0.0.0 behind a reverse proxy with authentication.

Supported brokers:
    Zerodha   — Kite Connect OAuth redirect
    Groww     — OAuth2 redirect
    Angel One — TOTP auto-login (free, no redirect needed)
    Upstox    — OAuth2 redirect (API v3, free)
    Fyers     — OAuth2 redirect (API v3, free, great options data)

Endpoints:
    GET  /                       → Login page (all brokers)
    GET  /zerodha/login          → Redirect to Kite OAuth
    GET  /zerodha/callback       → Handle request_token, complete login
    GET  /groww/login            → Redirect to Groww OAuth
    GET  /groww/callback         → Handle auth_code, complete login
    GET  /angelone/login         → Auto-login via TOTP (no redirect)
    GET  /upstox/login           → Redirect to Upstox OAuth
    GET  /upstox/callback        → Handle auth_code, complete login
    GET  /fyers/login            → Redirect to Fyers auth URL
    GET  /fyers/callback         → Handle auth_code, complete login
    GET  /demo                   → Demo / mock mode
    GET  /status                 → HTML: which brokers are authenticated
    GET  /api/status             → JSON: broker auth status
    GET  /api/portfolio          → JSON: combined portfolio from all brokers

Register these redirect URIs in your broker developer consoles:
    Zerodha   → http://localhost:8765/zerodha/callback
    Groww     → http://localhost:8765/groww/callback
    Upstox    → http://localhost:8765/upstox/callback
    Fyers     → http://localhost:8765/fyers/callback
    Angel One → (no redirect needed — TOTP-based)
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request as _Request
from fastapi.responses import HTMLResponse, RedirectResponse

# Load .env + keychain at server startup
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from config.credentials import load_all as _load_keychain

_load_keychain()

app = FastAPI(title="india-trade-cli", docs_url=None, redoc_url=None)

# ── OpenClaw Skills ───────────────────────────────────────────

from web.skills import router as _skills_router
from web.openclaw import MANIFEST as _MANIFEST
from fastapi import Request
from fastapi.exceptions import HTTPException as _HTTPException
import copy


def _require_localhost(request: _Request) -> None:
    """Raise 403 if the request does not come from localhost."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise _HTTPException(
            status_code=403,
            detail="This endpoint is only accessible from localhost.",
        )


app.include_router(_skills_router)


@app.get("/.well-known/openclaw.json", tags=["OpenClaw"])
async def openclaw_manifest(request: Request):
    """OpenClaw skill discovery manifest — lists all available skills and their input schemas."""
    manifest = copy.deepcopy(_MANIFEST)
    manifest["base_url"] = str(request.base_url).rstrip("/")
    return manifest


# ── Shared CSS ────────────────────────────────────────────────

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #0d1117; color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 1rem;
}
.container { max-width: 480px; width: 100%; }
.logo { text-align: center; margin-bottom: 2rem; }
.logo h1 { font-size: 2.4rem; font-weight: 800; color: #58a6ff; font-family: monospace; letter-spacing: 4px; }
.logo p  { color: #8b949e; margin-top: .4rem; font-size: .95rem; }
.card    { background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 2rem; }
h2       { font-size: 1rem; color: #8b949e; margin-bottom: 1.5rem; text-align: center; }
.btn {
    display: flex; align-items: center; justify-content: center; gap: .6rem;
    width: 100%; padding: .85rem 1.5rem; border: none; border-radius: 8px;
    font-size: .95rem; font-weight: 600; cursor: pointer;
    text-decoration: none; transition: all .15s; margin-bottom: .7rem;
}
.btn:last-child { margin-bottom: 0; }
.btn-zerodha  { background: #387ed1; color: #fff; }
.btn-zerodha:hover  { background: #2d6dbf; transform: translateY(-1px); }
.btn-groww    { background: #00c48c; color: #002e21; }
.btn-groww:hover    { background: #00a87a; transform: translateY(-1px); }
.btn-angel    { background: #ff6b35; color: #fff; }
.btn-angel:hover    { background: #e5602e; transform: translateY(-1px); }
.btn-upstox   { background: #7c3aed; color: #fff; }
.btn-upstox:hover   { background: #6d28d9; transform: translateY(-1px); }
.btn-fyers    { background: #c2410c; color: #fff; }
.btn-fyers:hover    { background: #9a3412; transform: translateY(-1px); }
.btn-demo     { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
.btn-demo:hover     { background: #30363d; color: #e6edf3; }
.btn-back     { background: #21262d; color: #8b949e; border: 1px solid #30363d; margin-top: 1.25rem; }
.btn-back:hover     { background: #30363d; color: #e6edf3; }
.btn[disabled]      { opacity: .4; cursor: not-allowed; transform: none !important; }
.divider      { text-align: center; color: #484f58; font-size: .8rem; margin: .3rem 0 .7rem; }
.badge {
    display: inline-block; padding: .2rem .6rem; border-radius: 20px;
    font-size: .75rem; font-weight: 600; margin-right: .4rem;
}
.badge-zerodha { background: #1a3a5c; color: #58a6ff; }
.badge-groww   { background: #00271a; color: #00c48c; }
.badge-angel   { background: #3d1a00; color: #ff6b35; }
.badge-upstox  { background: #2e1065; color: #c4b5fd; }
.badge-fyers   { background: #431407; color: #fed7aa; }
.badge-mock    { background: #2d2016; color: #d29922; }
.success-icon  { font-size: 3rem; text-align: center; margin-bottom: 1rem; }
.account-box {
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 1rem 1.25rem; margin: 1.25rem 0;
}
.account-box .name   { font-size: 1.1rem; font-weight: 700; }
.account-box .uid    { color: #484f58; font-size: .85rem; font-family: monospace; }
.account-box .cash   { color: #3fb950; font-size: 1.1rem; font-weight: 600; margin-top: .5rem; }
.account-box .margin { color: #d29922; font-size: .9rem; }
.warn-box {
    background: #2d1b00; border: 1px solid #d29922; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 1.25rem;
    font-size: .9rem; color: #d29922; line-height: 1.6;
}
.err-box {
    background: #2d0000; border: 1px solid #f85149; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 1.25rem;
    font-size: .9rem; color: #f85149; line-height: 1.6;
}
.info-box {
    background: #0d2137; border: 1px solid #1f6feb; border-radius: 8px;
    padding: 1rem 1.25rem; margin-bottom: 1.25rem;
    font-size: .9rem; color: #8b949e; line-height: 1.6;
}
.list { list-style: none; margin: .75rem 0; }
.list li {
    display: flex; align-items: center; gap: .5rem;
    padding: .45rem 0; border-bottom: 1px solid #21262d; font-size: .9rem;
}
.list li:last-child { border-bottom: none; }
.section-header {
    font-size: .7rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: #484f58; margin: 1rem 0 .5rem; padding-bottom: .35rem;
    border-bottom: 1px solid #21262d;
}
.footer { text-align: center; margin-top: 1.5rem; color: #484f58; font-size: .8rem; line-height: 1.6; }
.footer code { background: #21262d; padding: .15rem .4rem; border-radius: 4px; font-family: monospace; color: #8b949e; }
a { color: inherit; }
"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — india-trade-cli</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="container">
  <div class="logo"><h1>TRADE</h1><p>Indian Stock &amp; Options Platform</p></div>
  {body}
  <div class="footer">
    Credentials stored in OS keychain &nbsp;·&nbsp;
    Configure with <code>credentials setup</code> in the CLI
  </div>
</div>
</body>
</html>"""


# ── Credential / auth helpers ──────────────────────────────────


def _env(key: str) -> str:
    return os.environ.get(key, "")


# Zerodha
def _has_zerodha() -> bool:
    return bool(_env("KITE_API_KEY") and _env("KITE_API_SECRET"))


def _zerodha_auth() -> bool:
    try:
        if not _has_zerodha():
            return False
        from brokers.zerodha import ZerodhaAPI

        return ZerodhaAPI(_env("KITE_API_KEY"), _env("KITE_API_SECRET")).is_authenticated()
    except Exception:
        return False


# Groww
def _has_groww() -> bool:
    return bool(_env("GROWW_CLIENT_ID") and _env("GROWW_CLIENT_SECRET"))


def _groww_auth() -> bool:
    try:
        if not _has_groww():
            return False
        from brokers.groww import GrowwAPI

        return GrowwAPI(_env("GROWW_CLIENT_ID"), _env("GROWW_CLIENT_SECRET")).is_authenticated()
    except Exception:
        return False


# Angel One
def _has_angelone() -> bool:
    return bool(_env("ANGEL_API_KEY") and _env("ANGEL_CLIENT_CODE") and _env("ANGEL_TOTP_SECRET"))


def _angelone_auth() -> bool:
    try:
        if not _has_angelone():
            return False
        from brokers.angelone import AngelOneAPI

        return AngelOneAPI(
            api_key=_env("ANGEL_API_KEY"),
            client_code=_env("ANGEL_CLIENT_CODE"),
            password=_env("ANGEL_PASSWORD"),
            totp_secret=_env("ANGEL_TOTP_SECRET"),
        ).is_authenticated()
    except Exception:
        return False


# Upstox
def _has_upstox() -> bool:
    return bool(_env("UPSTOX_API_KEY") and _env("UPSTOX_API_SECRET"))


def _upstox_auth() -> bool:
    try:
        if not _has_upstox():
            return False
        from brokers.upstox import UpstoxAPI

        return UpstoxAPI(_env("UPSTOX_API_KEY"), _env("UPSTOX_API_SECRET")).is_authenticated()
    except Exception:
        return False


# Fyers
def _has_fyers() -> bool:
    return bool(_env("FYERS_APP_ID") and _env("FYERS_SECRET_KEY"))


def _fyers_auth() -> bool:
    try:
        if not _has_fyers():
            return False
        from brokers.fyers import FyersAPI

        return FyersAPI(_env("FYERS_APP_ID"), _env("FYERS_SECRET_KEY")).is_authenticated()
    except Exception:
        return False


# ── Shared success card ───────────────────────────────────────


def _success_card(broker_name: str, btn_cls: str, profile, funds, note: str) -> str:
    return f"""<div class="card">
      <div class="success-icon">✅</div>
      <h2>{broker_name} connected!</h2>
      <div class="account-box">
        <div class="name">{profile.name}</div>
        <div class="uid">{profile.user_id} &nbsp;·&nbsp; {profile.email}</div>
        <div class="cash">₹{funds.available_cash:,.2f} available</div>
        <div class="margin">₹{funds.used_margin:,.2f} margin used</div>
      </div>
      <p style="color:#8b949e;font-size:.85rem;text-align:center;line-height:1.5">{note}</p>
      <a href="/status" class="{btn_cls} btn" style="margin-top:1.25rem;text-decoration:none;
         display:flex;align-items:center;justify-content:center;padding:.9rem;">
        View all connections →
      </a>
      <a href="/" class="btn btn-back">← Connect another broker</a>
    </div>"""


def _broker_btn(
    label: str, icon: str, cls: str, path: str, configured: bool, authenticated: bool
) -> str:
    tag = f"✓ Connected — {label}" if authenticated else label
    href = f'href="{path}"' if configured else ""
    dis = "" if configured else 'disabled title="API keys not configured — run credentials setup"'
    style = "pointer-events:none;opacity:.4" if not configured else ""
    return f'<a {href} class="btn {cls}" {dis} style="{style}">{icon}&nbsp; {tag}</a>'


# ── Home / Login page ─────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    none_configured = not any(
        [
            _has_zerodha(),
            _has_groww(),
            _has_angelone(),
            _has_upstox(),
            _has_fyers(),
        ]
    )

    warn = (
        """<div class="warn-box">
        ⚠️ No broker API keys configured.<br>
        Run <code>credentials setup</code> in the terminal, or try Demo Mode below.
    </div>"""
        if none_configured
        else ""
    )

    free_brokers = """<div class="section-header">Free APIs — Recommended to start</div>"""

    body = f"""<div class="card">
      <h2>Connect your broker</h2>
      {warn}
      {free_brokers}
      {
        _broker_btn(
            "Login with Angel One (Free)",
            "🟠",
            "btn-angel",
            "/angelone/login",
            _has_angelone(),
            _angelone_auth(),
        )
    }
      {
        _broker_btn(
            "Login with Upstox (Free)",
            "🟣",
            "btn-upstox",
            "/upstox/login",
            _has_upstox(),
            _upstox_auth(),
        )
    }
      {
        _broker_btn(
            "Login with Fyers (Free)",
            "🔴",
            "btn-fyers",
            "/fyers/login",
            _has_fyers(),
            _fyers_auth(),
        )
    }
      <div class="section-header">Premium Brokers</div>
      {
        _broker_btn(
            "Login with Zerodha",
            "🔵",
            "btn-zerodha",
            "/zerodha/login",
            _has_zerodha(),
            _zerodha_auth(),
        )
    }
      {
        _broker_btn(
            "Login with Groww", "🟢", "btn-groww", "/groww/login", _has_groww(), _groww_auth()
        )
    }
      <div class="divider">or</div>
      <a href="/demo" class="btn btn-demo">🎭&nbsp; Demo Mode (no credentials needed)</a>
    </div>
    <div class="footer" style="margin-top:1rem">
      <a href="/status" style="color:#58a6ff">View connection status →</a>
    </div>"""
    return HTMLResponse(_page("Login", body))


# ── Zerodha ───────────────────────────────────────────────────


@app.get("/zerodha/login")
async def zerodha_login():
    if not _has_zerodha():
        body = """<div class="card"><div class="err-box">
          ❌ KITE_API_KEY / KITE_API_SECRET not set.<br>
          Get a free developer app at <a href="https://developers.kite.trade"
          style="color:#58a6ff" target="_blank">developers.kite.trade</a>
          then run <code>credentials setup</code>.
        </div><a href="/" class="btn btn-back">← Back</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=400)
    url = f"https://kite.trade/connect/login?api_key={_env('KITE_API_KEY')}&v=3"
    return RedirectResponse(url)


@app.get("/zerodha/callback", response_class=HTMLResponse)
async def zerodha_callback(request_token: str = "", status: str = ""):
    if status != "success" or not request_token:
        body = """<div class="card"><div class="err-box">❌ Zerodha login cancelled.</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Failed", body), status_code=400)
    try:
        from brokers.zerodha import ZerodhaAPI

        b = ZerodhaAPI(api_key=_env("KITE_API_KEY"), api_secret=_env("KITE_API_SECRET"))
        profile = b.complete_login(request_token=request_token)
        funds = b.get_funds()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">❌ {e}</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return HTMLResponse(
        _page(
            "Connected",
            _success_card(
                "Zerodha",
                "btn-zerodha",
                profile,
                funds,
                "Redirect URL: http://localhost:8765/zerodha/callback",
            ),
        )
    )


# ── Groww ─────────────────────────────────────────────────────


@app.get("/groww/login")
async def groww_login():
    if not _has_groww():
        body = """<div class="card"><div class="err-box">
          ❌ GROWW_CLIENT_ID / GROWW_CLIENT_SECRET not set.<br>
          Get credentials at <a href="https://developer.groww.in" style="color:#00c48c"
          target="_blank">developer.groww.in</a> then run <code>credentials setup</code>.
        </div><a href="/" class="btn btn-back">← Back</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=400)
    redirect = _env("GROWW_REDIRECT_URL") or "http://localhost:8765/groww/callback"
    url = (
        "https://groww.in/v1/api/login/oauth/authorize"
        f"?client_id={_env('GROWW_CLIENT_ID')}"
        f"&redirect_uri={redirect}&response_type=code"
        "&scope=holdings+positions+orders+funds"
    )
    return RedirectResponse(url)


@app.get("/groww/callback", response_class=HTMLResponse)
async def groww_callback(code: str = "", error: str = ""):
    if error or not code:
        body = f"""<div class="card"><div class="err-box">❌ Groww login failed: {error or "no code"}.</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Failed", body), status_code=400)
    try:
        from brokers.groww import GrowwAPI

        redirect = _env("GROWW_REDIRECT_URL") or "http://localhost:8765/groww/callback"
        b = GrowwAPI(
            client_id=_env("GROWW_CLIENT_ID"),
            client_secret=_env("GROWW_CLIENT_SECRET"),
            redirect_uri=redirect,
        )
        profile = b.complete_login(auth_code=code)
        funds = b.get_funds()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">❌ {e}</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return HTMLResponse(
        _page(
            "Connected",
            _success_card(
                "Groww",
                "btn-groww",
                profile,
                funds,
                "Redirect URL: http://localhost:8765/groww/callback",
            ),
        )
    )


# ── Angel One (TOTP — no redirect) ───────────────────────────


@app.get("/angelone/login", response_class=HTMLResponse)
async def angelone_login():
    if not _has_angelone():
        body = """<div class="card">
          <div class="info-box">
            <strong>Angel One SmartAPI</strong> — free, official, no monthly fee.<br><br>
            You need 3 things:<br>
            1. API key from <a href="https://smartapi.angelbroking.com"
               style="color:#ff6b35" target="_blank">smartapi.angelbroking.com</a>
               → <code>ANGEL_API_KEY</code><br>
            2. Your login ID + password → <code>ANGEL_CLIENT_CODE</code> &amp; <code>ANGEL_PASSWORD</code><br>
            3. Enable TOTP in the Angel One app (Settings → Security) →
               copy the base32 seed → <code>ANGEL_TOTP_SECRET</code><br><br>
            Then run: <code>credentials setup</code> in the terminal.
          </div>
          <a href="/" class="btn btn-back">← Back</a>
        </div>"""
        return HTMLResponse(_page("Angel One Setup", body), status_code=400)
    try:
        from brokers.angelone import AngelOneAPI

        b = AngelOneAPI(
            api_key=_env("ANGEL_API_KEY"),
            client_code=_env("ANGEL_CLIENT_CODE"),
            password=_env("ANGEL_PASSWORD"),
            totp_secret=_env("ANGEL_TOTP_SECRET"),
        )
        profile = b.complete_login()
        funds = b.get_funds()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">
          ❌ Angel One login failed: {e}<br><br>
          Check ANGEL_CLIENT_CODE, ANGEL_PASSWORD, and ANGEL_TOTP_SECRET.
        </div><a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return HTMLResponse(
        _page(
            "Connected",
            _success_card(
                "Angel One",
                "btn-angel",
                profile,
                funds,
                "SmartAPI — free, TOTP auto-login, no redirect URI needed.",
            ),
        )
    )


# ── Upstox ────────────────────────────────────────────────────


@app.get("/upstox/login")
async def upstox_login():
    if not _has_upstox():
        body = """<div class="card"><div class="err-box">
          ❌ UPSTOX_API_KEY / UPSTOX_API_SECRET not set.<br>
          Register at <a href="https://developer.upstox.com"
          style="color:#c4b5fd" target="_blank">developer.upstox.com</a>
          then run <code>credentials setup</code>.
        </div><a href="/" class="btn btn-back">← Back</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=400)
    redirect = _env("UPSTOX_REDIRECT_URL") or "http://localhost:8765/upstox/callback"
    url = (
        "https://api.upstox.com/index/dialog/login"
        f"?client_id={_env('UPSTOX_API_KEY')}"
        f"&redirect_uri={redirect}&response_type=code"
    )
    return RedirectResponse(url)


@app.get("/upstox/callback", response_class=HTMLResponse)
async def upstox_callback(code: str = "", error: str = ""):
    if error or not code:
        body = f"""<div class="card"><div class="err-box">❌ Upstox login failed: {error or "no code"}.</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Failed", body), status_code=400)
    try:
        from brokers.upstox import UpstoxAPI

        redirect = _env("UPSTOX_REDIRECT_URL") or "http://localhost:8765/upstox/callback"
        b = UpstoxAPI(
            api_key=_env("UPSTOX_API_KEY"),
            api_secret=_env("UPSTOX_API_SECRET"),
            redirect_uri=redirect,
        )
        profile = b.complete_login(auth_code=code)
        funds = b.get_funds()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">❌ {e}</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return HTMLResponse(
        _page(
            "Connected",
            _success_card(
                "Upstox",
                "btn-upstox",
                profile,
                funds,
                "Redirect URL: http://localhost:8765/upstox/callback",
            ),
        )
    )


# ── Fyers ─────────────────────────────────────────────────────


@app.get("/fyers/login")
async def fyers_login():
    if not _has_fyers():
        body = """<div class="card"><div class="err-box">
          ❌ FYERS_APP_ID / FYERS_SECRET_KEY not set.<br>
          Register at <a href="https://myapi.fyers.in"
          style="color:#fed7aa" target="_blank">myapi.fyers.in</a>
          then run <code>credentials setup</code>.
        </div><a href="/" class="btn btn-back">← Back</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=400)
    try:
        from brokers.fyers import FyersAPI

        redirect = _env("FYERS_REDIRECT_URL") or "http://localhost:8765/fyers/callback"
        b = FyersAPI(
            app_id=_env("FYERS_APP_ID"), secret_key=_env("FYERS_SECRET_KEY"), redirect_uri=redirect
        )
        url = b.get_login_url()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">❌ Could not generate login URL: {e}</div>
        <a href="/" class="btn btn-back">← Back</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return RedirectResponse(url)


@app.get("/fyers/callback", response_class=HTMLResponse)
async def fyers_callback(auth_code: str = "", state: str = "", s: str = ""):
    # Fyers sends ?auth_code= or sometimes ?code=
    code = auth_code
    error = "" if code else "no auth_code received"
    if error:
        body = f"""<div class="card"><div class="err-box">❌ Fyers login failed: {error}.</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Failed", body), status_code=400)
    try:
        from brokers.fyers import FyersAPI

        redirect = _env("FYERS_REDIRECT_URL") or "http://localhost:8765/fyers/callback"
        b = FyersAPI(
            app_id=_env("FYERS_APP_ID"), secret_key=_env("FYERS_SECRET_KEY"), redirect_uri=redirect
        )
        profile = b.complete_login(auth_code=code)
        funds = b.get_funds()
    except Exception as e:
        body = f"""<div class="card"><div class="err-box">❌ {e}</div>
        <a href="/" class="btn btn-back">← Try again</a></div>"""
        return HTMLResponse(_page("Error", body), status_code=500)
    return HTMLResponse(
        _page(
            "Connected",
            _success_card(
                "Fyers",
                "btn-fyers",
                profile,
                funds,
                "Redirect URL: http://localhost:8765/fyers/callback",
            ),
        )
    )


# ── Demo mode ─────────────────────────────────────────────────


@app.get("/demo", response_class=HTMLResponse)
async def demo():
    from brokers.mock import MockBrokerAPI

    b = MockBrokerAPI()
    b.complete_login()
    p = b.get_profile()
    f = b.get_funds()
    h = b.get_holdings()
    pos = b.get_positions()

    body = f"""<div class="card">
      <div class="success-icon">🎭</div>
      <h2>Demo mode — simulated data</h2>
      <div class="account-box">
        <div class="name">{p.name}</div>
        <div class="uid">mock · no real money at risk</div>
        <div class="cash">₹{f.available_cash:,.0f} (simulated)</div>
      </div>
      <ul class="list">
        <li>📊 {len(h)} simulated holdings</li>
        <li>📈 {len(pos)} open positions</li>
        <li>🔒 No real orders will be placed</li>
      </ul>
      <a href="/api/portfolio" class="btn btn-demo" style="margin-top:.75rem">
        View portfolio JSON →
      </a>
      <a href="/" class="btn btn-back">← Back</a>
    </div>"""
    return HTMLResponse(_page("Demo", body))


# ── Status page ───────────────────────────────────────────────


@app.get("/status", response_class=HTMLResponse)
async def status_page():
    _BROKERS = [
        (
            "zerodha",
            "Zerodha",
            "badge-zerodha",
            "/zerodha/login",
            "#58a6ff",
            _has_zerodha,
            _zerodha_auth,
        ),
        ("groww", "Groww", "badge-groww", "/groww/login", "#00c48c", _has_groww, _groww_auth),
        (
            "angelone",
            "Angel One",
            "badge-angel",
            "/angelone/login",
            "#ff6b35",
            _has_angelone,
            _angelone_auth,
        ),
        ("upstox", "Upstox", "badge-upstox", "/upstox/login", "#c4b5fd", _has_upstox, _upstox_auth),
        ("fyers", "Fyers", "badge-fyers", "/fyers/login", "#fed7aa", _has_fyers, _fyers_auth),
    ]
    rows = []
    for bkey, bname, badge_cls, login_path, color, has_fn, auth_fn in _BROKERS:
        badge = f'<span class="badge {badge_cls}">{bname}</span>'
        if has_fn():
            if auth_fn():
                rows.append(f"<li>{badge} ✅ Connected</li>")
            else:
                rows.append(
                    f'<li>{badge} Configured — <a href="{login_path}" style="color:{color}">Login →</a></li>'
                )
        else:
            rows.append(
                f'<li><span class="badge {badge_cls}" style="opacity:.5">{bname}</span> '
                f'<span style="color:#484f58">Not configured — '
                f'<a href="{login_path}" style="color:{color}">Setup →</a></span></li>'
            )

    body = f"""<div class="card">
      <h2>Broker status</h2>
      <ul class="list">{"".join(rows)}</ul>
      <a href="/api/portfolio" class="btn btn-demo" style="margin-top:1rem">Portfolio JSON →</a>
      <a href="/" class="btn btn-back">← Back</a>
    </div>"""
    return HTMLResponse(_page("Status", body))


# ── JSON API ──────────────────────────────────────────────────


@app.get("/api/status")
async def api_status(request: Request):
    _require_localhost(request)
    return {
        "zerodha": {"configured": _has_zerodha(), "authenticated": _zerodha_auth()},
        "groww": {"configured": _has_groww(), "authenticated": _groww_auth()},
        "angel_one": {"configured": _has_angelone(), "authenticated": _angelone_auth()},
        "upstox": {"configured": _has_upstox(), "authenticated": _upstox_auth()},
        "fyers": {"configured": _has_fyers(), "authenticated": _fyers_auth()},
    }


@app.get("/api/portfolio")
async def api_portfolio(request: Request):
    _require_localhost(request)
    holdings: list[dict] = []
    positions: list[dict] = []
    total_cash = total_margin = total_balance = 0.0
    active_brokers: list[str] = []

    def _try(name: str, factory):
        nonlocal total_cash, total_margin, total_balance
        try:
            b = factory()
            if not b.is_authenticated():
                return
            active_brokers.append(name)
            f = b.get_funds()
            total_cash += f.available_cash
            total_margin += f.used_margin
            total_balance += f.total_balance
            for h in b.get_holdings():
                holdings.append(
                    {
                        "broker": name,
                        "symbol": h.symbol,
                        "qty": h.quantity,
                        "avg_price": h.avg_price,
                        "ltp": h.last_price,
                        "pnl": h.pnl,
                        "current_value": h.current_value,
                    }
                )
            for p in b.get_positions():
                positions.append(
                    {
                        "broker": name,
                        "symbol": p.symbol,
                        "product": p.product,
                        "qty": p.quantity,
                        "avg_price": p.avg_price,
                        "ltp": p.last_price,
                        "pnl": p.pnl,
                    }
                )
        except Exception:
            pass

    if _has_zerodha():
        from brokers.zerodha import ZerodhaAPI

        _try("zerodha", lambda: ZerodhaAPI(_env("KITE_API_KEY"), _env("KITE_API_SECRET")))

    if _has_groww():
        from brokers.groww import GrowwAPI

        _try("groww", lambda: GrowwAPI(_env("GROWW_CLIENT_ID"), _env("GROWW_CLIENT_SECRET")))

    if _has_angelone():
        from brokers.angelone import AngelOneAPI

        _try(
            "angel_one",
            lambda: AngelOneAPI(
                _env("ANGEL_API_KEY"),
                _env("ANGEL_CLIENT_CODE"),
                _env("ANGEL_PASSWORD"),
                _env("ANGEL_TOTP_SECRET"),
            ),
        )

    if _has_upstox():
        from brokers.upstox import UpstoxAPI

        _try("upstox", lambda: UpstoxAPI(_env("UPSTOX_API_KEY"), _env("UPSTOX_API_SECRET")))

    if _has_fyers():
        from brokers.fyers import FyersAPI

        _try("fyers", lambda: FyersAPI(_env("FYERS_APP_ID"), _env("FYERS_SECRET_KEY")))

    # Fallback: demo data if no broker authenticated
    if not active_brokers:
        from brokers.mock import MockBrokerAPI

        m = MockBrokerAPI()
        m.complete_login()
        active_brokers.append("mock (demo)")
        f = m.get_funds()
        total_cash, total_margin, total_balance = f.available_cash, f.used_margin, f.total_balance
        for h in m.get_holdings():
            holdings.append(
                {
                    "broker": "mock",
                    "symbol": h.symbol,
                    "qty": h.quantity,
                    "avg_price": h.avg_price,
                    "ltp": h.last_price,
                    "pnl": h.pnl,
                    "current_value": h.current_value,
                }
            )
        for p in m.get_positions():
            positions.append(
                {
                    "broker": "mock",
                    "symbol": p.symbol,
                    "qty": p.quantity,
                    "avg_price": p.avg_price,
                    "ltp": p.last_price,
                    "pnl": p.pnl,
                }
            )

    total_pnl = sum(h["pnl"] for h in holdings) + sum(p["pnl"] for p in positions)
    return {
        "brokers": active_brokers,
        "funds": {
            "available_cash": round(total_cash, 2),
            "used_margin": round(total_margin, 2),
            "total_balance": round(total_balance, 2),
            "currency": "INR",
        },
        "holdings": holdings,
        "positions": positions,
        "total_pnl": round(total_pnl, 2),
        "holding_count": len(holdings),
        "position_count": len(positions),
    }
