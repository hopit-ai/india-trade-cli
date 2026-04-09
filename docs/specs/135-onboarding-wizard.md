# Spec: First-Launch Onboarding Wizard (#135)

## Problem
After Python bootstrap, a fresh install goes straight to the chat UI with nothing configured. No AI provider, no broker, no API keys. Users must edit `.env` manually — unacceptable for DMG distribution.

## Solution
5-step guided onboarding wizard shown on first launch (after sidecar is ready). Credentials stored in OS keychain + backup `.env` at `~/.trading_platform/.env`.

## Requirements

### First-Launch Detection
- `GET /api/onboarding/status` checks if `AI_PROVIDER` is set in keychain or env
- Returns: `{ onboarding_complete, ai_provider, newsapi_key_set, broker_connected, capital, risk_pct, trading_mode }`
- If `onboarding_complete` is false AND no `ai_provider`: show wizard

### Step 1: Welcome
- App logo, title, tagline
- "Get Started" button → next step

### Step 2: AI Provider (mandatory)
- 5 provider cards: Gemini (free), Claude API, Claude Pro/Max (free*), OpenAI, Ollama (free)
- Providers with `needsKey=true`: show API key input + "Test Key" button
- Providers without key (Ollama, Claude subscription): show SetupRunner
  - Ollama: auto-detect → brew install → start server → pull llama3.1
  - Claude sub: auto-detect → npm install CLI → prompt `claude login`
- `POST /api/onboarding/test-provider` validates key via lightweight API call
- `POST /api/onboarding/credential` saves key to keychain + env
- `POST /api/onboarding/setup-provider` runs shell commands for Ollama/Claude
- Cannot proceed without a valid provider configured

### Step 3: Market Data (NewsAPI mandatory, broker skippable)
- **NewsAPI** (mandatory):
  - Key input + "Get free key" link (opens newsapi.org)
  - `POST /api/onboarding/test-newsapi` validates key
  - Saves via `/api/onboarding/credential`
  - Cannot proceed without valid NewsAPI key
- **Broker** (skippable):
  - Info banner: "Connect a broker for live data. Without one, 15-min delayed."
  - Fyers card: opens `/fyers/login` via `electronAPI.openExternal`
  - Zerodha card: opens `/zerodha/login` via `electronAPI.openExternal`
  - Polls `/api/status` every 2s to detect auth completion
  - "Skip for now" button

### Step 4: Trading Settings
- Capital (INR): number input, default 200000
- Risk per trade (%): number input, default 2, range 0.5-10
- Trading mode: Paper (default) / Live toggle
  - Live shows warning: "Real trades through your broker"

### Step 5: Completion
- Summary of all configured settings with check/skip icons
- "Start Trading" button
- `POST /api/onboarding/complete` saves settings + writes `~/.trading_platform/.env`

### Credential Storage
- Primary: OS keychain via `keyring` (set_credential in config/credentials.py)
- Backup: `~/.trading_platform/.env` for packaged mode
- Sidecar loads: `load_dotenv(~/.trading_platform/.env, override=False)` as fallback
- No restart needed: `set_credential` writes to `os.environ` immediately

### Backend Endpoints
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/onboarding/status` | GET | Check configuration state | None |
| `/api/onboarding/credential` | POST | Save key/value to keychain + env | None |
| `/api/onboarding/test-provider` | POST | Test AI provider key | None |
| `/api/onboarding/test-newsapi` | POST | Test NewsAPI key | None |
| `/api/onboarding/setup-provider` | POST | Run Ollama/Claude setup commands | None |
| `/api/onboarding/complete` | POST | Save settings, mark done | None |

### Setup Provider Steps
**Ollama:** check → install (brew) → start (ollama serve) → pull_model (llama3.1)
**Claude subscription:** check → install (npm) → prompt login

## Acceptance Criteria
1. Fresh app (no AI_PROVIDER in keychain/env) shows onboarding wizard after sidecar ready
2. Cannot proceed past Step 2 without a valid AI provider
3. Cannot proceed past Step 3 without a valid NewsAPI key
4. Broker connection is skippable
5. "Test Key" validates against the actual API (Gemini, Anthropic, OpenAI, Ollama)
6. Ollama setup runs brew install + ollama pull from within the app
7. Claude subscription setup runs npm install from within the app
8. After completion, main chat UI loads immediately (no restart)
9. Subsequent launches skip wizard (onboarding_complete = true)
10. Credentials persist across app restarts (stored in keychain)
11. `~/.trading_platform/.env` is written as backup for packaged mode
