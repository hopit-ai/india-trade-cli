import { create } from 'zustand'

/** Get the API base URL — works in both Electron and web mode. */
export function getBaseUrl(port) {
  if (window.__INDIA_TRADE_WEB__) return window.location.origin
  return port ? `http://127.0.0.1:${port}` : null
}

/** Generate a UUID-like id for sessions. */
function uuid() {
  return 'sess-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)
}

/**
 * Derive a short title from the first user message in a session.
 */
function deriveTitle(text) {
  const parts = text.trim().split(/\s+/)
  const cmd = parts[0].toLowerCase()
  const arg = parts[1]?.toUpperCase()

  if ((cmd === 'analyze' || cmd === 'analyse' || cmd === 'a') && arg) return `${arg} Analysis`
  if (cmd === 'gex' && arg) return `${arg} GEX`
  if (cmd === 'morning-brief' || cmd === 'brief' || cmd === 'mb') return 'Morning Brief'
  if (cmd === 'iv-smile' || cmd === 'smile') return `${arg || 'NIFTY'} IV Smile`
  if (cmd === 'strategy' || cmd === 'strat') return `${arg || 'NIFTY'} Strategy`
  if (cmd === 'risk-report' || cmd === 'risk') return 'Risk Report'
  if (cmd === 'delta-hedge' || cmd === 'dh') return 'Delta Hedge'
  if (cmd === 'whatif' || cmd === 'what-if') return 'What-If'
  if (cmd === 'drift') return 'Drift'
  if (cmd === 'memory' || cmd === 'mem') return 'Memory'
  if (cmd === 'holdings' || cmd === 'h') return 'Holdings'
  if (cmd === 'positions' || cmd === 'pos') return 'Positions'
  if (cmd === 'orders') return 'Orders'
  if (cmd === 'funds') return 'Funds'
  if (cmd === 'flows') return 'FII/DII Flows'
  if (cmd === 'quote' || cmd === 'q') return `${arg || ''} Quote`
  if (cmd === 'oi') return `${arg || ''} OI`
  if (cmd === 'scan') return 'Scan'
  if (cmd === 'patterns') return 'Patterns'
  if (cmd === 'deep-analyze' || cmd === 'da') return `${arg || ''} Deep Analysis`
  if (cmd === 'backtest' || cmd === 'bt') return `${arg || ''} Backtest`

  // Fallback: first 30 chars
  return text.length > 30 ? text.slice(0, 30) + '...' : text
}

// Create the default initial session
const defaultId = uuid()

export const useChatStore = create((set, get) => ({
  // ── Multi-session state ───────────────────────────────────
  sessions: {
    [defaultId]: { id: defaultId, title: 'New Session', messages: [], createdAt: Date.now() },
  },
  activeSessionId: defaultId,

  // ── Backward-compatible flat messages (swapped on session switch) ──
  messages:      [],
  isLoading:     false,
  port:          null,
  sidecarError:  null,
  brokerStatus:   { connected: false, broker: null },
  brokerStatuses: {},   // full /api/status response
  streamCancel:  null,   // () => void — closes the active EventSource
  activeStreamId: null,  // stream_id from SSE started event (#113)

  setPort:         (port)   => set({ port, sidecarError: null }),
  setSidecarError: (msg)    => set({ sidecarError: msg }),
  setBrokerStatus:   (status)   => set({ brokerStatus: status }),
  setBrokerStatuses: (statuses) => {
    // also derive the simple brokerStatus from the full response
    const connected = Object.values(statuses).some(b => b.authenticated)
    const broker    = Object.entries(statuses).find(([, b]) => b.authenticated)?.[0] ?? null
    const name      = broker ? ({ zerodha: 'Zerodha', groww: 'Groww', angel_one: 'Angel One', upstox: 'Upstox', fyers: 'Fyers' }[broker] ?? broker) : null
    set({ brokerStatuses: statuses, brokerStatus: { connected, broker: name } })
  },

  // ── Session management ────────────────────────────────────

  createSession: () => {
    const { sessions, activeSessionId, messages } = get()
    // Save current session messages
    const updated = { ...sessions }
    if (activeSessionId && updated[activeSessionId]) {
      updated[activeSessionId] = { ...updated[activeSessionId], messages }
    }
    const id = uuid()
    updated[id] = { id, title: 'New Session', messages: [], createdAt: Date.now() }
    set({ sessions: updated, activeSessionId: id, messages: [], isLoading: false })
  },

  switchSession: (id) => {
    const { sessions, activeSessionId, messages } = get()
    if (id === activeSessionId) return
    // Save current session messages
    const updated = { ...sessions }
    if (activeSessionId && updated[activeSessionId]) {
      updated[activeSessionId] = { ...updated[activeSessionId], messages }
    }
    const target = updated[id]
    if (!target) return
    set({ sessions: updated, activeSessionId: id, messages: target.messages, isLoading: false })
  },

  deleteSession: (id) => {
    const { sessions, activeSessionId, messages } = get()
    const updated = { ...sessions }
    delete updated[id]
    const remaining = Object.keys(updated)
    if (remaining.length === 0) {
      // Create a fresh default session
      const newId = uuid()
      updated[newId] = { id: newId, title: 'New Session', messages: [], createdAt: Date.now() }
      set({ sessions: updated, activeSessionId: newId, messages: [] })
      return
    }
    if (id === activeSessionId) {
      const nextId = remaining[0]
      set({ sessions: updated, activeSessionId: nextId, messages: updated[nextId].messages })
    } else {
      // Save current messages before updating sessions
      if (activeSessionId && updated[activeSessionId]) {
        updated[activeSessionId] = { ...updated[activeSessionId], messages }
      }
      set({ sessions: updated })
    }
  },

  renameSession: (id, title) => {
    const { sessions } = get()
    if (!sessions[id]) return
    set({ sessions: { ...sessions, [id]: { ...sessions[id], title } } })
  },

  // ── Message actions (operate on active session) ───────────

  addUserMessage: (text) => set((s) => {
    const newMessages = [...s.messages, {
      id: Date.now(), role: 'user', text,
    }]
    // Auto-title: if this is the first user message in the session
    const session = s.sessions[s.activeSessionId]
    let sessions = s.sessions
    if (session && session.title === 'New Session') {
      sessions = {
        ...s.sessions,
        [s.activeSessionId]: { ...session, title: deriveTitle(text), messages: newMessages },
      }
    } else if (session) {
      sessions = {
        ...s.sessions,
        [s.activeSessionId]: { ...session, messages: newMessages },
      }
    }
    return { messages: newMessages, isLoading: true, sessions }
  }),

  addResponse: (card) => set((s) => {
    const newMessages = [...s.messages, { id: Date.now() + 1, role: 'assistant', ...card }]
    const session = s.sessions[s.activeSessionId]
    let sessions = s.sessions
    if (session) {
      sessions = { ...s.sessions, [s.activeSessionId]: { ...session, messages: newMessages } }
    }
    return { messages: newMessages, isLoading: false, sessions }
  }),

  addError: (text) => set((s) => {
    const newMessages = [...s.messages, { id: Date.now() + 1, role: 'error', text }]
    const session = s.sessions[s.activeSessionId]
    let sessions = s.sessions
    if (session) {
      sessions = { ...s.sessions, [s.activeSessionId]: { ...session, messages: newMessages } }
    }
    return { messages: newMessages, isLoading: false, sessions }
  }),

  setLoading: (v) => set({ isLoading: v }),

  setStreamCancel: (fn) => set({ streamCancel: fn }),
  setActiveStreamId: (id) => set({ activeStreamId: id }),

  cancelStream: () => {
    const { streamCancel } = get()
    if (streamCancel) { streamCancel(); set({ streamCancel: null, isLoading: false }) }
  },

  // Streaming support — used by analyze SSE
  startStreamingMessage: (id, symbol, exchange) => set((s) => {
    const newMessages = [...s.messages, {
      id,
      role: 'assistant',
      cardType: 'streaming_analysis',
      data: { symbol, exchange, analysts: [], debate_steps: [], synthesis_text: null, phase: 'analysts', report: null, trade_plans: null },
    }]
    const session = s.sessions[s.activeSessionId]
    let sessions = s.sessions
    if (session) {
      sessions = { ...s.sessions, [s.activeSessionId]: { ...session, messages: newMessages } }
    }
    return { messages: newMessages, isLoading: true, sessions }
  }),

  updateStreamingMessage: (id, updater) => set((s) => {
    const newMessages = s.messages.map((m) => m.id === id ? { ...m, data: updater(m.data) } : m)
    const session = s.sessions[s.activeSessionId]
    let sessions = s.sessions
    if (session) {
      sessions = { ...s.sessions, [s.activeSessionId]: { ...session, messages: newMessages } }
    }
    return { messages: newMessages, sessions }
  }),

  finalizeStreamingMessage: (_id) => set({ isLoading: false, activeStreamId: null }),

  // Draft message — lets cards pre-fill the input bar
  draft: '',
  setDraft: (text) => set({ draft: text }),

  // Context queued while a streaming analysis is running (#102)
  // Shown as a user bubble and auto-injected into the first follow-up
  pendingContext: '',
  setPendingContext: (text) => set({ pendingContext: text }),
  clearPendingContext: () => set({ pendingContext: '' }),
})
)
