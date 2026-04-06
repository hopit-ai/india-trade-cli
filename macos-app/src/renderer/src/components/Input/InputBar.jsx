import { useState, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useAPI } from '../../hooks/useAPI'

// Maps typed commands → API endpoint + card type
function parseCommand(input) {
  const parts = input.trim().split(/\s+/)
  const cmd   = parts[0].toLowerCase()
  const args  = parts.slice(1)

  switch (cmd) {
    case 'quote': case 'q':
      if (!args[0]) return { error: 'Usage: quote SYMBOL' }
      return { endpoint: '/skills/quote', body: { symbol: args[0].toUpperCase() }, cardType: 'quote' }

    case 'analyze': case 'analyse': case 'a':
      if (!args[0]) return { error: 'Usage: analyze SYMBOL' }
      return { stream: true, symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' }

    case 'morning-brief': case 'brief': case 'mb':
      return { endpoint: '/skills/morning_brief', body: {}, cardType: 'morning_brief' }

    case 'flows': case 'flow':
      return { endpoint: '/skills/flows', body: {}, cardType: 'flows' }

    case 'holdings': case 'h':
      return { endpoint: '/skills/holdings', body: {}, cardType: 'holdings' }

    case 'positions': case 'pos':
      return { endpoint: '/skills/positions', body: {}, cardType: 'holdings' }

    case 'backtest': case 'bt':
      if (args.length < 2) return { error: 'Usage: backtest SYMBOL STRATEGY  (e.g. backtest RELIANCE rsi)' }
      return {
        endpoint: '/skills/backtest',
        body: { symbol: args[0].toUpperCase(), strategy: args[1] },
        cardType: 'backtest',
      }

    case 'macro':
      return { endpoint: '/skills/macro', body: {}, cardType: 'markdown' }

    case 'earnings':
      return { endpoint: '/skills/earnings', body: { symbols: args }, cardType: 'markdown' }

    default:
      // Fall through to AI chat
      return { endpoint: '/skills/chat', body: { message: input }, cardType: 'markdown' }
  }
}

export default function InputBar() {
  const [value, setValue]   = useState('')
  const { call, ready }     = useAPI()
  const port = useChatStore((s) => s.port)
  const {
    addUserMessage, addResponse, addError, isLoading,
    startStreamingMessage, updateStreamingMessage, finalizeStreamingMessage,
    setStreamCancel,
  } = useChatStore()
  const inputRef = useRef(null)

  function runStreaming(symbol, exchange) {
    const msgId = Date.now() + 1
    startStreamingMessage(msgId, symbol, exchange)

    const url = `http://127.0.0.1:${port}/skills/analyze/stream?symbol=${symbol}&exchange=${exchange}`
    const es  = new EventSource(url)

    function applyEvent(event) {
      if (event.type === 'started') {
        updateStreamingMessage(msgId, (d) => ({ ...d, phase: 'started' }))
      } else if (event.type === 'analyst') {
        updateStreamingMessage(msgId, (d) => ({
          ...d,
          analysts: [...d.analysts, {
            name: event.name, verdict: event.verdict,
            confidence: event.confidence, error: event.error,
          }],
        }))
      } else if (event.type === 'phase') {
        updateStreamingMessage(msgId, (d) => ({ ...d, phase: event.phase }))
      } else if (event.type === 'debate_step') {
        updateStreamingMessage(msgId, (d) => ({
          ...d,
          debate_steps: [...(d.debate_steps ?? []), { step: event.step, label: event.label, text: event.text }],
        }))
      } else if (event.type === 'synthesis_text') {
        updateStreamingMessage(msgId, (d) => ({ ...d, synthesis_text: event.text }))
      } else if (event.type === 'done') {
        updateStreamingMessage(msgId, (d) => ({
          ...d, phase: 'done', report: event.report, trade_plans: event.trade_plans,
        }))
        es.close()
        setStreamCancel(null)
        finalizeStreamingMessage(msgId)
      } else if (event.type === 'error') {
        es.close()
        setStreamCancel(null)
        addError(event.message)
        finalizeStreamingMessage(msgId)
      }
    }

    // Register cancel so the card's Stop button can close the stream
    setStreamCancel(() => {
      es.close()
      finalizeStreamingMessage(msgId)
    })

    es.onmessage = (e) => {
      try { applyEvent(JSON.parse(e.data)) } catch (err) { console.error('[SSE]', err) }
    }

    es.onerror = () => {
      es.close()
      addError('Stream connection lost')
      finalizeStreamingMessage(msgId)
    }
  }

  async function submit() {
    const text = value.trim()
    if (!text || isLoading || !ready) return

    setValue('')
    addUserMessage(text)

    const parsed = parseCommand(text)

    if (parsed.error) {
      addError(parsed.error)
      return
    }

    // SSE streaming path for analyze
    if (parsed.stream) {
      runStreaming(parsed.symbol, parsed.exchange)
      return
    }

    try {
      const result = await call(parsed.endpoint, parsed.body)
      addResponse({ cardType: parsed.cardType, data: result.data ?? result })
    } catch (e) {
      addError(e.message)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex-shrink-0 border-t border-border bg-panel px-4 py-3">
      <div className="flex items-center gap-3 bg-elevated border border-border rounded-xl px-4 py-2.5">
        <span className="text-amber text-sm font-mono flex-shrink-0">›</span>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={ready ? 'quote RELIANCE   •   analyze INFY   •   morning-brief' : 'Starting API…'}
          disabled={!ready || isLoading}
          className="flex-1 bg-transparent text-text text-sm font-mono outline-none
                     placeholder:text-subtle disabled:opacity-50"
          autoFocus
        />
        <button
          onClick={submit}
          disabled={!value.trim() || isLoading || !ready}
          className="text-amber text-sm font-mono disabled:opacity-30 hover:opacity-80 transition-opacity"
        >
          ↵
        </button>
      </div>
      <p className="text-subtle text-[10px] font-ui mt-1.5 pl-1">
        Try: quote RELIANCE · analyze INFY · morning-brief · flows · holdings
      </p>
    </div>
  )
}
