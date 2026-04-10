"""
web/auth.py
───────────
User authentication for web mode (login/signup with email + password).

Uses SQLite for user storage and in-memory sessions.
"""

from __future__ import annotations

import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
import hashlib

# ── Database ─────────────────────────────────────────────────────

DB_PATH = Path(os.environ.get("AUTH_DB_PATH", Path.home() / ".trading_platform" / "users.db"))


def init_db() -> None:
    """Create the users table if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def user_count() -> int:
    """Return the total number of registered users."""
    if not DB_PATH.exists():
        return 0
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ── User CRUD ────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_user(email: str, password: str) -> dict:
    """
    Create a new user account.

    Validates email format and password length (>= 8 chars).
    Hashes password with bcrypt. Raises ValueError on validation failure,
    and sqlite3.IntegrityError if email already exists.
    """
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("Invalid email format")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    salt = secrets.token_hex(16)
    password_hash = salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, password_hash, now),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "email": email, "created_at": now}
    except sqlite3.IntegrityError:
        raise ValueError("An account with this email already exists")
    finally:
        conn.close()


def verify_user(email: str, password: str) -> dict | None:
    """
    Verify credentials. Returns user dict {id, email, created_at} or None.
    """
    email = email.strip().lower()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return None
        stored = row["password_hash"]
        salt, hashed = stored.split(":", 1)
        if hashlib.sha256((salt + password).encode()).hexdigest() != hashed:
            return None
        return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
    finally:
        conn.close()


# ── Session store (in-memory) ────────────────────────────────────

_sessions: dict[str, dict] = {}


def create_session(user_id: int, email: str) -> str:
    """Generate a random session ID and store it."""
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "user_id": user_id,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    """Return session dict or None if not found."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    """Remove a session."""
    _sessions.pop(session_id, None)


# ── FastAPI router ───────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


class AuthBody(BaseModel):
    email: str
    password: str


@auth_router.post("/signup")
async def signup(body: AuthBody, response: Response):
    """Create a new account, start a session, set cookie."""
    if "@" not in body.email:
        raise HTTPException(400, "Invalid email — must contain @")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    try:
        user = create_user(body.email, body.password)
    except ValueError as e:
        raise HTTPException(400, str(e))

    session_id = create_session(user["id"], user["email"])
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return {"ok": True, "email": user["email"]}


@auth_router.post("/login")
async def login(body: AuthBody, response: Response):
    """Verify credentials, start a session, set cookie."""
    user = verify_user(body.email, body.password)
    if not user:
        raise HTTPException(401, "Invalid email or password")

    session_id = create_session(user["id"], user["email"])
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return {"ok": True, "email": user["email"]}


@auth_router.post("/logout")
async def logout(request: Request, response: Response):
    """Delete session and clear cookie."""
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)
    response.delete_cookie("session_id")
    return {"ok": True}


@auth_router.get("/me")
async def me(request: Request):
    """Return current user info from session cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "Session expired")
    return {"email": session["email"], "user_id": session["user_id"]}


# ── Auth dependency ──────────────────────────────────────────────


async def require_auth(request: Request) -> dict:
    """Dependency that checks for valid session cookie."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "Session expired")
    return session
