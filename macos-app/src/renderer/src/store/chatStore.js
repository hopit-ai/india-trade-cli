import { create } from 'zustand'

/** Get the API base URL — works in both Electron and web mode. */
export function getBaseUrl(port) {
  if (window.__INDIA_TRADE_WEB__) return window.location.origin
  return port ? `http://127.0.0.1:${port}` : null
}

export const useChatStore = create((set, get) => ({
  messages:      [],
  isLoading:     false,
  port:          null,
  sidecarError:  null,
  brokerStatus:   { connected: false, broker: null },
  brokerStatuses: {},   // full /api/status response
  streamCancel:  null,   // () => void — closes the active EventSource

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

  addUserMessage: (text) => set((s) => ({
    messages: [...s.messages, {
      id: Date.now(), role: 'user', text,
    }],
    isLoading: true,
  })),

  addResponse: (card) => set((s) => ({
    messages: [...s.messages, { id: Date.now() + 1, role: 'assistant', ...card }],
    isLoading: false,
  })),

  addError: (text) => set((s) => ({
    messages: [...s.messages, { id: Date.now() + 1, role: 'error', text }],
    isLoading: false,
  })),

  setLoading: (v) => set({ isLoading: v }),

  setStreamCancel: (fn) => set({ streamCancel: fn }),

  cancelStream: () => {
    const { streamCancel } = get()
    if (streamCancel) { streamCancel(); set({ streamCancel: null, isLoading: false }) }
  },

  // Streaming support — used by analyze SSE
  startStreamingMessage: (id, symbol, exchange) => set((s) => ({
    messages: [...s.messages, {
      id,
      role: 'assistant',
      cardType: 'streaming_analysis',
      data: { symbol, exchange, analysts: [], debate_steps: [], synthesis_text: null, phase: 'analysts', report: null, trade_plans: null },
    }],
    isLoading: true,
  })),

  updateStreamingMessage: (id, updater) => set((s) => ({
    messages: s.messages.map((m) => m.id === id ? { ...m, data: updater(m.data) } : m),
  })),

  finalizeStreamingMessage: (_id) => set({ isLoading: false }),

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
