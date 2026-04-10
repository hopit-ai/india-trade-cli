# Spec: Web App — Browser-based UI (#139)

## Problem
Platform requires macOS Electron app or terminal CLI. No access for Windows/Linux/mobile users.

## Solution
Serve the same React UI from FastAPI at `http://localhost:8765/`. Add auth with user accounts. Two deployment modes: self-hosted and hosted SaaS.

## Requirements

### Serving React from FastAPI
- Build React app as static files (reuse `macos-app/out/renderer/`)
- Copy to `web/static/` with electron stubs injected
- Mount as `StaticFiles` in FastAPI AFTER all API routes
- SPA routing: `html=True` serves `index.html` for unmatched paths

### Electron API Stubs
- `web/static/electron-stubs.js` loaded before React bundle
- Provides `window.electronAPI` with web fallbacks:
  - `getPort()` returns null (web uses relative URLs)
  - `openExternal(url)` does `window.open(url, '_blank')`
  - All IPC listeners are no-ops
- Sets `window.__INDIA_TRADE_WEB__ = true` flag

### React Web Compatibility
- `useAPI.js`: if no port, use `window.location.origin` as base URL
- `App.jsx`: if `__INDIA_TRADE_WEB__`, skip Python bootstrap screens, check onboarding via fetch directly
- `useMarketClock.js`: skip tray updates on web
- SSE streaming works unchanged (same-origin requests)

### Auth System
- **User model:** id, email, hashed_password, created_at
- **Storage:** SQLite at `~/.trading_platform/users.db`
- **Password hashing:** bcrypt via `passlib`
- **Sessions:** server-side dict + SQLite persistence, httponly cookie
- **Endpoints:**
  - `POST /auth/signup` — email + password, returns session cookie
  - `POST /auth/login` — email + password, returns session cookie
  - `POST /auth/logout` — clears session
  - `GET /auth/me` — current user info
- **Middleware:** All `/api/*` and `/skills/*` require valid session
- **Exclusions:** `/auth/*`, `/health`, static files are public

### Per-User Credential Isolation
- Self-hosted (single user): backwards compatible, no isolation
- Multi-user: credentials in `user_credentials` SQLite table
- Schema: `(user_id, key, encrypted_value)`
- Encryption: AES-256 with key derived from user's password hash

### Login/Signup Page
- Standalone HTML at `web/static/auth.html`
- Dark theme matching the app
- Email + password form
- Toggle between signup and login
- On success: redirect to `/`

### Deployment Modes

#### Self-hosted
- User runs on own machine/VPS
- All data local
- Docker image provided
- `DEPLOY_MODE=self-hosted` (default)

#### Hosted SaaS
- Multi-user at app.indiatrade.ai
- PostgreSQL for users + encrypted credentials
- Redis for sessions (optional)
- Nginx + HTTPS
- `DEPLOY_MODE=hosted`
- `DATABASE_URL=postgresql://...`

## Acceptance Criteria
1. `http://localhost:8765/` shows login page (no Electron needed)
2. Sign up creates account, login sets session cookie
3. After login, full React UI loads with all features working
4. `analyze SYMBOL` works (SSE streaming)
5. Broker OAuth works (opens in new browser tab)
6. Sidebar commands work
7. Logout clears session, redirects to login
8. Unauthenticated requests to `/api/*` return 401
9. Electron app (`npm run dev`) still works unchanged
10. Docker build produces working image
