import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act } from '@testing-library/react'
import { useChatStore } from '../renderer/src/store/chatStore'

// Reset the store to a clean slate before each test so tests are isolated.
beforeEach(() => {
  useChatStore.setState({
    messages:       [],
    isLoading:      false,
    draft:          '',
    pendingContext: '',
    streamCancel:   null,
    port:           null,
    sidecarError:   null,
    brokerStatus:   { connected: false, broker: null },
    brokerStatuses: {},
  })
})

describe('chatStore', () => {
  // ── messages ───────────────────────────────────────────────────────────────
  it('addUserMessage adds a user message and sets loading', () => {
    act(() => {
      useChatStore.getState().addUserMessage('hello world')
    })
    const { messages, isLoading } = useChatStore.getState()
    expect(messages).toHaveLength(1)
    expect(messages[0].role).toBe('user')
    expect(messages[0].text).toBe('hello world')
    expect(isLoading).toBe(true)
  })

  it('addResponse adds assistant message and clears loading', () => {
    act(() => {
      useChatStore.getState().addUserMessage('test')
    })
    act(() => {
      useChatStore.getState().addResponse({ cardType: 'quote', data: { symbol: 'INFY' } })
    })
    const { messages, isLoading } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[1].role).toBe('assistant')
    expect(messages[1].cardType).toBe('quote')
    expect(messages[1].data).toEqual({ symbol: 'INFY' })
    expect(isLoading).toBe(false)
  })

  it('addError adds error message and clears loading', () => {
    act(() => {
      useChatStore.getState().addUserMessage('test')
    })
    act(() => {
      useChatStore.getState().addError('Something went wrong')
    })
    const { messages, isLoading } = useChatStore.getState()
    expect(messages).toHaveLength(2)
    expect(messages[1].role).toBe('error')
    expect(messages[1].text).toBe('Something went wrong')
    expect(isLoading).toBe(false)
  })

  // ── streaming ──────────────────────────────────────────────────────────────
  it('startStreamingMessage creates streaming_analysis card', () => {
    const msgId = 12345
    act(() => {
      useChatStore.getState().startStreamingMessage(msgId, 'NIFTY', 'NSE')
    })
    const { messages, isLoading } = useChatStore.getState()
    expect(messages).toHaveLength(1)
    const msg = messages[0]
    expect(msg.id).toBe(msgId)
    expect(msg.role).toBe('assistant')
    expect(msg.cardType).toBe('streaming_analysis')
    expect(msg.data.symbol).toBe('NIFTY')
    expect(msg.data.exchange).toBe('NSE')
    expect(msg.data.analysts).toEqual([])
    expect(msg.data.phase).toBe('analysts')
    expect(isLoading).toBe(true)
  })

  it('updateStreamingMessage updates specific message by id', () => {
    const msgId = 99
    act(() => {
      useChatStore.getState().startStreamingMessage(msgId, 'RELIANCE', 'NSE')
    })
    act(() => {
      useChatStore.getState().updateStreamingMessage(msgId, (data) => ({
        ...data,
        analysts: [{ name: 'Technical', content: 'Bullish' }],
        phase: 'debate',
      }))
    })
    const { messages } = useChatStore.getState()
    const msg = messages.find((m) => m.id === msgId)
    expect(msg.data.analysts).toHaveLength(1)
    expect(msg.data.analysts[0].name).toBe('Technical')
    expect(msg.data.phase).toBe('debate')
  })

  it('updateStreamingMessage does not affect other messages', () => {
    act(() => {
      useChatStore.getState().startStreamingMessage(1, 'NIFTY', 'NSE')
      useChatStore.getState().startStreamingMessage(2, 'TCS', 'NSE')
    })
    act(() => {
      useChatStore.getState().updateStreamingMessage(1, (data) => ({
        ...data,
        phase: 'synthesis',
      }))
    })
    const { messages } = useChatStore.getState()
    const msg1 = messages.find((m) => m.id === 1)
    const msg2 = messages.find((m) => m.id === 2)
    expect(msg1.data.phase).toBe('synthesis')
    expect(msg2.data.phase).toBe('analysts') // unchanged
  })

  it('finalizeStreamingMessage clears isLoading', () => {
    act(() => {
      useChatStore.getState().startStreamingMessage(55, 'BANKNIFTY', 'NSE')
    })
    expect(useChatStore.getState().isLoading).toBe(true)
    act(() => {
      useChatStore.getState().finalizeStreamingMessage(55)
    })
    expect(useChatStore.getState().isLoading).toBe(false)
    // Message itself should still be there
    expect(useChatStore.getState().messages).toHaveLength(1)
  })

  // ── draft ──────────────────────────────────────────────────────────────────
  it('setDraft and draft state', () => {
    expect(useChatStore.getState().draft).toBe('')
    act(() => {
      useChatStore.getState().setDraft('analyze NIFTY')
    })
    expect(useChatStore.getState().draft).toBe('analyze NIFTY')
    act(() => {
      useChatStore.getState().setDraft('')
    })
    expect(useChatStore.getState().draft).toBe('')
  })

  // ── pendingContext ─────────────────────────────────────────────────────────
  it('setPendingContext stores context', () => {
    act(() => {
      useChatStore.getState().setPendingContext('Focus on support levels')
    })
    expect(useChatStore.getState().pendingContext).toBe('Focus on support levels')
  })

  it('clearPendingContext resets to empty string', () => {
    act(() => {
      useChatStore.getState().setPendingContext('Some context')
    })
    act(() => {
      useChatStore.getState().clearPendingContext()
    })
    expect(useChatStore.getState().pendingContext).toBe('')
  })

  // ── cancelStream ──────────────────────────────────────────────────────────
  it('cancelStream calls the cancel function and resets state', () => {
    const cancelFn = vi.fn()
    act(() => {
      useChatStore.getState().setStreamCancel(cancelFn)
      useChatStore.getState().setLoading(true)
    })
    expect(useChatStore.getState().streamCancel).toBe(cancelFn)
    act(() => {
      useChatStore.getState().cancelStream()
    })
    expect(cancelFn).toHaveBeenCalledOnce()
    expect(useChatStore.getState().streamCancel).toBeNull()
    expect(useChatStore.getState().isLoading).toBe(false)
  })

  it('cancelStream is noop when no streamCancel', () => {
    // Should not throw when streamCancel is null
    expect(() => {
      act(() => {
        useChatStore.getState().cancelStream()
      })
    }).not.toThrow()
    expect(useChatStore.getState().isLoading).toBe(false)
  })

  // ── setBrokerStatuses ──────────────────────────────────────────────────────
  it('setBrokerStatuses derives brokerStatus from authenticated brokers', () => {
    act(() => {
      useChatStore.getState().setBrokerStatuses({
        zerodha:   { authenticated: false },
        groww:     { authenticated: true },
        angel_one: { authenticated: false },
      })
    })
    const { brokerStatus, brokerStatuses } = useChatStore.getState()
    expect(brokerStatus.connected).toBe(true)
    expect(brokerStatus.broker).toBe('Groww')
    expect(brokerStatuses.groww.authenticated).toBe(true)
  })

  it('setBrokerStatuses maps known broker keys to display names', () => {
    const knownBrokers = [
      { key: 'zerodha',   expected: 'Zerodha' },
      { key: 'groww',     expected: 'Groww' },
      { key: 'angel_one', expected: 'Angel One' },
      { key: 'upstox',    expected: 'Upstox' },
      { key: 'fyers',     expected: 'Fyers' },
    ]
    for (const { key, expected } of knownBrokers) {
      const statuses = { [key]: { authenticated: true } }
      act(() => {
        useChatStore.getState().setBrokerStatuses(statuses)
      })
      expect(useChatStore.getState().brokerStatus.broker).toBe(expected)
    }
  })

  it('setBrokerStatuses sets connected=false when none authenticated', () => {
    act(() => {
      useChatStore.getState().setBrokerStatuses({
        zerodha: { authenticated: false },
        groww:   { authenticated: false },
      })
    })
    const { brokerStatus } = useChatStore.getState()
    expect(brokerStatus.connected).toBe(false)
    expect(brokerStatus.broker).toBeNull()
  })

  it('setBrokerStatuses uses raw key as broker name for unknown brokers', () => {
    act(() => {
      useChatStore.getState().setBrokerStatuses({
        newbroker: { authenticated: true },
      })
    })
    const { brokerStatus } = useChatStore.getState()
    expect(brokerStatus.connected).toBe(true)
    // Falls through to `broker ?? broker` which returns the raw key
    expect(brokerStatus.broker).toBe('newbroker')
  })
})
