import { create } from 'zustand'

export const useChatStore = create((set, get) => ({
  messages:     [],
  isLoading:    false,
  port:         null,
  sidecarError: null,
  brokerStatus: { connected: false, broker: null },

  setPort:         (port)   => set({ port, sidecarError: null }),
  setSidecarError: (msg)    => set({ sidecarError: msg }),
  setBrokerStatus: (status) => set({ brokerStatus: status }),

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

  // Streaming support — used by analyze SSE
  startStreamingMessage: (id, symbol, exchange) => set((s) => ({
    messages: [...s.messages, {
      id,
      role: 'assistant',
      cardType: 'streaming_analysis',
      data: { symbol, exchange, analysts: [], phase: 'analysts', report: null, trade_plans: null },
    }],
    isLoading: true,
  })),

  updateStreamingMessage: (id, updater) => set((s) => ({
    messages: s.messages.map((m) => m.id === id ? { ...m, data: updater(m.data) } : m),
  })),

  finalizeStreamingMessage: (_id) => set({ isLoading: false }),
}))
