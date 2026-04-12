# Spec: Multi-Session UI (#110)

## Problem
App has a single chat session. No way to start new conversations, switch
between contexts, or work on multiple stocks without context pollution.

## Goal
Add session management to the frontend — create, switch, delete sessions.
Each session has independent messages and maps to an independent backend
TradingAgent. Works on macOS app and web app.

---

## Architecture

```
┌─────────────────────────────────┐
│ BROKER CONNECTIONS (global)     │
│  Fyers → DATA, Zerodha → EXEC  │
│  Shared across all sessions    │
└─────────────────────────────────┘

┌──────────────────┐ ┌──────────────────┐
│ Session 1        │ │ Session 2        │
│ "INFY Analysis"  │ │ "NIFTY GEX"      │
│                  │ │                  │
│ messages: [...]  │ │ messages: [...]  │
│ TradingAgent #1  │ │ TradingAgent #2  │
└──────────────────┘ └──────────────────┘
```

---

## Frontend Store — `chatStore.js`

### New state shape

```javascript
sessions: {
  'sess-abc123': { id: 'sess-abc123', title: 'INFY Analysis', messages: [...], createdAt: 1712345678 },
  'sess-def456': { id: 'sess-def456', title: 'New Session', messages: [], createdAt: 1712345700 },
},
activeSessionId: 'sess-abc123',
messages: [...]  // === sessions[activeSessionId].messages (kept for backward compat)
```

### Strategy: swap-on-switch

Keep `messages` as a top-level array (all existing components read it).
When switching sessions:
1. Save current `messages` into `sessions[activeSessionId].messages`
2. Set `activeSessionId = targetId`
3. Set `messages = sessions[targetId].messages`

This means zero changes to ChatArea, StreamingAnalysisCard, FollowupChat, etc.

### New actions

```javascript
createSession()
  - Generate ID: `sess-${Date.now().toString(36)}`
  - Save current session's messages
  - Create new session: { id, title: 'New Session', messages: [], createdAt }
  - Add to sessions, set as active, clear messages

switchSession(id)
  - Save current messages to current session
  - Set activeSessionId = id
  - Set messages = sessions[id].messages
  - Reset isLoading, streamCancel, activeStreamId

deleteSession(id)
  - Remove from sessions
  - If active was deleted, switch to most recent remaining
  - If no sessions left, create a new one

renameSession(id, title)
  - Update sessions[id].title
```

### Auto-title

In `addUserMessage()`, if this is the first message in the current session
(messages.length === 0 before adding), derive title from text:

| Input | Title |
|-------|-------|
| `analyze INFY` | "INFY Analysis" |
| `deep-analyze RELIANCE` | "RELIANCE Deep" |
| `gex NIFTY` | "NIFTY GEX" |
| `iv-smile BANKNIFTY` | "BANKNIFTY IV" |
| `morning-brief` | "Morning Brief" |
| `holdings` | "Holdings" |
| `strategy NIFTY bullish` | "NIFTY Strategy" |
| Free text | First 30 chars |

### Initialization

On store creation, create one default session so the app starts with an
empty chat ready.

---

## Sidebar — Session list

### Location
Between broker status and quick commands in `Sidebar/index.jsx`.

### UI
```
SESSIONS                    + New
┌──────────────────────────────┐
│ ▸ INFY Analysis          ← active (highlighted)
│   NIFTY GEX
│   Morning Brief
└──────────────────────────────┘
```

- Click to switch
- Active session highlighted with `bg-elevated`
- Sorted by `createdAt` descending (newest first)
- Max height 200px with overflow scroll
- "+ New" button creates session and switches to it

### Delete (v2, optional)
Right-click context menu or small × icon on hover. Not required for initial release.

---

## InputBar changes

When sending to `/skills/chat`, use `activeSessionId` as the `session_id`
parameter. Currently hardcoded or absent — change to:
```javascript
body: JSON.stringify({
  message: text,
  session_id: activeSessionId,
})
```

---

## Keyboard shortcut

- `Cmd+N` (macOS) / `Ctrl+N` — create new session
- Register in `App.jsx` via `useEffect` with `keydown` listener

---

## Backend

No changes needed. `/skills/chat` already supports `session_id` param
(line 102 in skills.py: `session_id: str = "default"`). Each session_id
gets an independent `TradingAgent` instance in `_chat_sessions` dict.

---

## Persistence

Use `localStorage` to persist sessions across page reloads:
- On every state change, save `{ sessions, activeSessionId }` to localStorage
- On store init, restore from localStorage if available
- Zustand `persist` middleware or manual save/load

---

## Edge Cases

1. **Single session**: Default state — one session, no session list clutter
2. **Delete active session**: Switch to most recent remaining, or create new if empty
3. **Streaming in progress**: Switching sessions while analysis streams — cancel? keep? → Cancel stream on switch (simplest)
4. **Web vs macOS**: Same React code, same behavior
5. **Session limit**: No hard limit, but sidebar scrolls after ~10 sessions
