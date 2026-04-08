import { useState, useRef, useEffect } from 'react'
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

    // ── High-value additions ──────────────────────────────────

    case 'deep-analyze': case 'deep-analyse': case 'da':
      if (!args[0]) return { error: 'Usage: deep-analyze SYMBOL [EXCHANGE]' }
      return {
        endpoint: '/skills/deep_analyze',
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' },
        cardType: 'markdown',
      }

    case 'funds': case 'fund':
      return { endpoint: '/skills/funds', body: {}, cardType: 'funds', method: 'GET' }

    case 'profile':
      return { endpoint: '/skills/profile', body: {}, cardType: 'profile', method: 'GET' }

    case 'orders': case 'order':
      return { endpoint: '/skills/orders', body: {}, cardType: 'orders', method: 'GET' }

    case 'alerts': case 'al':
      return { endpoint: '/skills/alerts/list', body: {}, cardType: 'alerts' }

    case 'alert':
      // alert SYMBOL above/below PRICE
      // alert remove ID
      if (args[0] === 'remove' || args[0] === 'rm') {
        if (!args[1]) return { error: 'Usage: alert remove ALERT_ID' }
        return { endpoint: '/skills/alerts/remove', body: { alert_id: args[1] }, cardType: 'markdown' }
      }
      if (args.length < 3) return { error: 'Usage: alert SYMBOL above|below PRICE' }
      return {
        endpoint: '/skills/alerts/add',
        body: {
          symbol:    args[0].toUpperCase(),
          condition: args[1].toLowerCase(),   // above / below / crosses
          threshold: Number(args[2]),
        },
        cardType: 'markdown',
      }

    case 'oi':
      if (!args[0]) return { error: 'Usage: oi SYMBOL [EXCHANGE]' }
      return {
        endpoint: '/skills/oi_profile',
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' },
        cardType: 'oi',
      }

    case 'patterns': case 'pat':
      return { endpoint: '/skills/patterns', body: {}, cardType: 'patterns' }

    case 'greeks': case 'greek':
      return { endpoint: '/skills/greeks', body: {}, cardType: 'greeks' }

    case 'scan':
      return {
        endpoint: '/skills/scan',
        body: { scan_type: args[0] ?? 'options', filters: {} },
        cardType: 'scan',
      }

    case 'deals': case 'bulk-deals':
      return {
        endpoint: '/skills/deals',
        body: { symbol: args[0]?.toUpperCase() ?? null, days: 5 },
        cardType: 'deals',
      }

    case 'iv-smile': case 'smile': case 'ivsmile': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      return { endpoint: '/skills/iv_smile', body: { symbol: sym, expiry: args[1] ?? null }, cardType: 'iv_smile' }
    }
    case 'gex': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      return { endpoint: '/skills/gex', body: { symbol: sym, expiry: args[1] ?? null }, cardType: 'gex' }
    }
    case 'delta-hedge': case 'dh': case 'deltahedge':
      return { endpoint: '/skills/delta_hedge', body: null, cardType: 'delta_hedge', method: 'GET' }
    case 'risk-report': case 'risk': case 'var':
      return { endpoint: '/skills/risk_report', body: null, cardType: 'risk_report', method: 'GET' }
    case 'walkforward': case 'wf': case 'walk-forward': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      const strat = args[1] ?? 'rsi'
      return { endpoint: '/skills/walkforward', body: { symbol: sym, strategy: strat, window_months: 6 }, cardType: 'walkforward' }
    }
    case 'whatif': case 'what-if': case 'scenario': {
      // whatif nifty -5   → market move
      // whatif RELIANCE +10 → stock move
      // whatif             → 3-scenario sweep
      const sym = args[0]?.toUpperCase()
      const chg = parseFloat(args[1])
      if (sym && (sym === 'NIFTY' || sym === 'MARKET') && !isNaN(chg)) {
        return { endpoint: '/skills/whatif', body: { scenario: 'market', nifty_change: chg }, cardType: 'whatif' }
      } else if (sym && !isNaN(chg)) {
        return { endpoint: '/skills/whatif', body: { scenario: 'stock', symbol: sym, stock_change: chg }, cardType: 'whatif' }
      }
      return { endpoint: '/skills/whatif', body: { scenario: 'market' }, cardType: 'whatif' }
    }
    case 'strategy': case 'strat': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      const view = (args[1] ?? 'bullish').toUpperCase()
      const dte = parseInt(args[2]) || 30
      return { endpoint: '/skills/strategy', body: { symbol: sym, view, dte }, cardType: 'strategy' }
    }
    case 'drift':
      return { endpoint: '/skills/drift', body: null, cardType: 'drift', method: 'GET' }
    case 'memory': case 'mem':
      return { endpoint: '/skills/memory', body: null, cardType: 'memory', method: 'GET' }
    case 'audit': {
      const trade_id = args[0]
      if (!trade_id) return { endpoint: '/skills/memory', body: null, cardType: 'memory', method: 'GET' }
      return { endpoint: '/skills/audit', body: { trade_id }, cardType: 'audit' }
    }
    case 'telegram': case 'tg':
      return { endpoint: '/skills/telegram/status', body: null, cardType: 'telegram', method: 'GET' }
    case 'provider': {
      if (args[0]) {
        return { endpoint: '/skills/provider', body: { provider: args[0], model: args[1] ?? null }, cardType: 'provider' }
      }
      return { endpoint: '/skills/provider', body: null, cardType: 'provider', method: 'GET' }
    }
    case 'pairs': {
      const symA = args[0]?.toUpperCase() ?? 'RELIANCE'
      const symB = args[1]?.toUpperCase() ?? 'TCS'
      return { endpoint: '/skills/pairs', body: { stock_a: symA, stock_b: symB }, cardType: 'pairs' }
    }

    default:
      // Fall through to AI chat
      return { endpoint: '/skills/chat', body: { message: input }, cardType: 'markdown' }
  }
}

export default function InputBar() {
  const [value, setValue]   = useState('')
  const { call, get, ready } = useAPI()
  const port     = useChatStore((s) => s.port)
  const draft             = useChatStore((s) => s.draft)
  const setDraft          = useChatStore((s) => s.setDraft)
  const streamCancel      = useChatStore((s) => s.streamCancel)
  const setPendingContext = useChatStore((s) => s.setPendingContext)
  const {
    addUserMessage, addResponse, addError, isLoading,
    startStreamingMessage, updateStreamingMessage, finalizeStreamingMessage,
    setStreamCancel,
  } = useChatStore()

  // True when an analysis is actively streaming — input stays active in "context mode"
  const isStreaming = isLoading && !!streamCancel
  const inputRef = useRef(null)

  // When a card pre-fills the draft, populate the input and focus it
  useEffect(() => {
    if (draft) {
      setValue(draft)
      setDraft('')
      inputRef.current?.focus()
    }
  }, [draft])

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
            key_points: event.key_points ?? [],
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
    if (!text || !ready) return

    // #102 — context injection: if analysis is streaming, queue as pending context
    if (isStreaming) {
      setValue('')
      setPendingContext(text)
      // Show as a user bubble so the user can see it was received
      addUserMessage(text)
      return
    }

    if (isLoading) return

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
      const result = parsed.method === 'GET'
        ? await get(parsed.endpoint)
        : await call(parsed.endpoint, parsed.body)
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

  const placeholder = !ready
    ? 'Starting API…'
    : isStreaming
    ? 'Analysis in progress — type to add context…'
    : 'analyze INFY · gex NIFTY · strategy NIFTY bullish · whatif nifty -5 · …'

  return (
    <div className="flex-shrink-0 border-t border-border bg-panel px-4 py-3">
      {/* #102 banner — visible while streaming */}
      {isStreaming && (
        <div className="mb-2 px-1 flex items-center gap-2">
          <span className="text-[10px] animate-pulse text-amber font-ui">◆</span>
          <span className="text-[10px] text-muted font-ui">
            Analysis running — add context to inject into the follow-up
          </span>
        </div>
      )}
      <div className={`flex items-center gap-3 bg-elevated border rounded-xl px-4 py-2.5 ${isStreaming ? 'border-amber/30' : 'border-border'}`}>
        <span className={`text-sm font-mono flex-shrink-0 ${isStreaming ? 'text-amber animate-pulse' : 'text-amber'}`}>›</span>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={!ready || (isLoading && !isStreaming)}
          className="flex-1 bg-transparent text-text text-sm font-mono outline-none
                     placeholder:text-subtle disabled:opacity-50"
          autoFocus
        />
        <button
          onClick={submit}
          disabled={!value.trim() || (isLoading && !isStreaming) || !ready}
          className="text-amber text-sm font-mono disabled:opacity-30 hover:opacity-80 transition-opacity"
        >
          ↵
        </button>
      </div>
      <p className="text-subtle text-[10px] font-ui mt-1.5 pl-1">
        analyze INFY · oi NIFTY · greeks · scan · funds · orders · alerts · patterns · da RELIANCE · iv-smile NIFTY · gex NIFTY · delta-hedge · risk-report · walkforward NIFTY rsi · whatif nifty -5 · strategy NIFTY bullish · drift · memory · audit &lt;id&gt; · telegram · provider · pairs RELIANCE TCS
      </p>
    </div>
  )
}
