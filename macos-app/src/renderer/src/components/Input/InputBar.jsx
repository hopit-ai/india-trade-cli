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

    case 'analyze': case 'analyse':
      if (!args[0]) return { error: 'Usage: analyze SYMBOL' }
      return { endpoint: '/skills/analyze', body: { symbol: args[0].toUpperCase() }, cardType: 'markdown' }

    case 'morning-brief': case 'brief':
      return { endpoint: '/skills/morning_brief', body: {}, cardType: 'morning_brief' }

    case 'flows':
      return { endpoint: '/skills/flows', body: {}, cardType: 'markdown' }

    case 'holdings':
      return { endpoint: '/skills/holdings', body: {}, cardType: 'holdings' }

    case 'positions':
      return { endpoint: '/skills/positions', body: {}, cardType: 'holdings' }

    case 'backtest':
      if (args.length < 2) return { error: 'Usage: backtest SYMBOL STRATEGY' }
      return {
        endpoint: '/skills/backtest',
        body: { symbol: args[0].toUpperCase(), strategy: args[1] },
        cardType: 'markdown',
      }

    default:
      // Fall through to AI chat
      return { endpoint: '/skills/chat', body: { message: input }, cardType: 'markdown' }
  }
}

export default function InputBar() {
  const [value, setValue]   = useState('')
  const { call, ready }     = useAPI()
  const { addUserMessage, addResponse, addError, isLoading } = useChatStore()
  const inputRef            = useRef(null)

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
