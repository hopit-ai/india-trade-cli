# Spec: In-App Settings Panel (#135)

## Problem
All configuration (AI provider, trading mode, capital, broker keys) lives in `.env` or the CLI.
The macOS app has no settings UI — non-technical users must edit files.

## Backend Endpoints

### GET /skills/settings
Returns current configuration (non-secret fields shown, secret fields masked).

Response:
```json
{
  "status": "ok",
  "data": {
    "ai_provider": "anthropic",
    "ai_model": "claude-sonnet-4-5",
    "ai_fast_provider": "",
    "ai_fast_model": "",
    "trading_mode": "paper",
    "trading_capital": "100000",
    "default_risk_pct": "1.0",
    "newsapi_key": "****",
    "telegram_bot_token": "****",
    "anthropic_api_key_set": true,
    "openai_api_key_set": false,
    "gemini_api_key_set": false
  }
}
```

### POST /skills/settings
Updates one or more settings. Writes to `os.environ` (in-memory) and to the keychain via `config.credentials.set_credential`.

Input:
```json
{
  "settings": {
    "AI_PROVIDER": "gemini",
    "GEMINI_API_KEY": "AIza...",
    "TRADING_MODE": "paper",
    "TRADING_CAPITAL": "200000"
  }
}
```

Response:
```json
{"status": "ok", "data": {"updated": ["AI_PROVIDER", "GEMINI_API_KEY", "TRADING_MODE", "TRADING_CAPITAL"]}}
```

## Frontend

### SettingsPanel.jsx
- Modal overlay component (similar to BrokerPanel)
- Sections: AI Provider, Trading, Notifications, Data
- Each setting is an editable field (text input, select, or toggle)
- Changes call `POST /skills/settings`
- Opens from gear icon in Sidebar footer

### Sidebar update
- Add gear icon button in the bottom bar (next to broker status)
- Clicking it shows `<SettingsPanel onClose={...} />`

## Files
- `web/skills.py` — GET/POST `/skills/settings`
- `macos-app/.../Sidebar/SettingsPanel.jsx` — settings modal
- `macos-app/.../Sidebar/index.jsx` — add gear icon + SettingsPanel integration

## Acceptance Criteria
- GET /skills/settings returns current config with secrets masked
- POST /skills/settings updates env vars and persists to keychain
- Unknown/disallowed keys are rejected (400)
- Frontend gear icon opens settings modal
- Saving settings in modal calls POST /skills/settings
