/**
 * StreamingAnalysisCard
 *
 * Renders live progress as multi-agent analysis SSE events arrive:
 *  – Analyst pills light up one by one as they complete
 *  – Phase labels flip from dim → active → done
 *  – Full AnalysisCard content appears once "done" arrives
 */
import React, { useEffect, useRef, useState } from 'react'
import { useChatStore } from '../../store/chatStore'

// These must match the `name` class attribute on each analyst in multi_agent.py
const ANALYSTS = [
  'Technical',
  'Fundamental',
  'Options',
  'News & Macro',
  'Sentiment',
  'Sector Rotation',
  'Risk Manager',
]

const DISPLAY_NAMES = {
  'Technical':       'Technical',
  'Fundamental':     'Fundamental',
  'Options':         'Options',
  'News & Macro':    'News / Macro',
  'Sentiment':       'Sentiment',
  'Sector Rotation': 'Sector',
  'Risk Manager':    'Risk',
}

const VERDICT_COLOR = {
  BUY:     'text-green border-green/40 bg-green/5',
  SELL:    'text-red border-red/40 bg-red/5',
  HOLD:    'text-amber border-amber/40 bg-amber/5',
  BULLISH: 'text-green border-green/40 bg-green/5',
  BEARISH: 'text-red border-red/40 bg-red/5',
  NEUTRAL: 'text-amber border-amber/40 bg-amber/5',
  UNKNOWN: 'text-muted border-border/40',
}

const STEP_META = {
  bull_r1:     { label: 'Bull Researcher',  color: 'text-green', icon: '▲' },
  bear_r1:     { label: 'Bear Researcher',  color: 'text-red',   icon: '▼' },
  bull_r2:     { label: 'Bull Rebuttal',    color: 'text-green', icon: '▲' },
  bear_r2:     { label: 'Bear Rebuttal',    color: 'text-red',   icon: '▼' },
  facilitator: { label: 'Facilitator',      color: 'text-blue',  icon: '◈' },
}

export default function StreamingAnalysisCard({ data }) {
  const cancelStream      = useChatStore((s) => s.cancelStream)
  const streamCancel      = useChatStore((s) => s.streamCancel)
  const setDraft          = useChatStore((s) => s.setDraft)
  const pendingContext    = useChatStore((s) => s.pendingContext)
  const clearPendingContext = useChatStore((s) => s.clearPendingContext)
  const port              = useChatStore((s) => s.port)
  const bottomRef         = useRef(null)

  // Follow-up chat state (#103)
  const [followupValue,   setFollowupValue]   = useState('')
  const [followupLoading, setFollowupLoading] = useState(false)
  const [followupThread,  setFollowupThread]  = useState([]) // [{q, a}]
  const [followupError,   setFollowupError]   = useState(null)
  const followupRef = useRef(null)

  // Destructure with safe defaults — must happen before any early return
  const {
    symbol, exchange,
    analysts     = [],
    debate_steps = [],
    synthesis_text = null,
    phase        = 'analysts',
    report       = null,
    trade_plans  = null,
  } = data ?? {}

  const done     = phase === 'done'
  const debating = phase === 'debate' || phase === 'synthesis' || done
  const synth    = phase === 'synthesis' || done

  // Auto-scroll to bottom of card whenever new content arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [analysts.length, debate_steps.length, synthesis_text, done])

  const running  = !done && !!streamCancel

  const statusLabel = done        ? 'Analysis'
                    : phase === 'analysts' ? 'Analysis · Connecting…'
                    : phase === 'started'  ? 'Analysis · Initialising…'
                    : phase === 'debate'   ? 'Analysis · Debate…'
                    : phase === 'synthesis'? 'Analysis · Synthesis…'
                    : 'Analysis · Running…'

  return (
    <div className="bg-elevated border border-blue/30 rounded-xl p-4 max-w-2xl w-full space-y-4 overflow-y-auto max-h-[80vh]">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui">
            {statusLabel}
          </p>
          <p className="text-text text-lg font-semibold font-mono mt-0.5">
            {symbol} <span className="text-muted text-sm font-ui">{exchange}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {running && (
            <button
              onClick={cancelStream}
              className="text-red text-xs font-ui border border-red/30 rounded-lg px-2.5 py-1
                         hover:bg-red/10 transition-colors"
            >
              ✕ Stop
            </button>
          )}
          <span className={`text-xl ${done ? '' : 'animate-pulse'}`}>🔬</span>
        </div>
      </div>

      {/* Analyst grid */}
      <div className="border-t border-border pt-3">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">
          Phase 1 — Analyst Team
        </p>
        <div className="flex flex-wrap gap-2 items-start">
          {ANALYSTS.map((name) => {
            const result = analysts.find((a) => a.name === name)
            const idx    = analysts.findIndex((a) => a.name === name)

            if (!result) {
              // Show a subtle pulsing placeholder while this analyst is still running
              const isRunning = !done && (phase === 'started' || phase === 'analysts')
              return (
                <span key={name}
                  className={`border text-[11px] font-ui px-2.5 py-1 rounded-lg
                             text-subtle border-border/30 bg-transparent
                             ${isRunning ? 'animate-pulse opacity-50' : 'opacity-25'}`}>
                  {DISPLAY_NAMES[name]}
                </span>
              )
            }

            const cls = result.error
              ? 'text-red border-red/30 bg-red/5'
              : (VERDICT_COLOR[result.verdict] ?? VERDICT_COLOR.UNKNOWN)

            return (
              <AnalystPill key={name} result={result} name={name} idx={idx} cls={cls} />
            )
          })}
        </div>
      </div>

      {/* Phase 2 + 3 status */}
      <div className="border-t border-border pt-3 grid grid-cols-2 gap-2">
        <PhaseLabel label="Phase 2 — Debate" active={debating} done={synth} />
        <PhaseLabel label="Phase 3 — Synthesis" active={synth} done={done} />
      </div>

      {/* Debate steps — stream in one by one as each LLM call completes */}
      {debate_steps.length > 0 && (
        <div className="border-t border-border pt-3 space-y-3">
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">
            Phase 2 — Bull / Bear Debate
          </p>
          {debate_steps.map((s) => {
            const meta = STEP_META[s.step] ?? { label: s.label, color: 'text-muted', icon: '•' }
            return (
              <DebateStep key={s.step} meta={meta} text={s.text} />
            )
          })}
        </div>
      )}

      {/* Synthesis preview — appears as soon as Fund Manager finishes */}
      {synthesis_text && !done && (
        <div className="border-t border-border pt-3">
          <p className="text-blue text-[10px] uppercase tracking-widest font-ui mb-2">
            Phase 3 — Fund Manager Synthesis
          </p>
          <p className="text-text text-sm font-ui leading-relaxed whitespace-pre-wrap">
            {synthesis_text}
          </p>
        </div>
      )}

      {/* Final report — shown once done (includes trade plans) */}
      {done && report && (
        <div className="border-t border-border pt-3">
          <p className="text-text text-sm font-ui leading-relaxed whitespace-pre-wrap">
            {report}
          </p>
        </div>
      )}

      {/* Trade plans — shown once done */}
      {done && trade_plans && Object.entries(trade_plans).filter(([, v]) => v != null).length > 0 && (
        <TradePlans plans={trade_plans} />
      )}

      {/* ── #104 Action chips — appear once analysis is done ── */}
      {done && (
        <ActionChips
          symbol={symbol}
          analysts={analysts}
          setDraft={setDraft}
          onAsk={(q) => {
            setFollowupValue(q)
            setTimeout(() => followupRef.current?.focus(), 50)
          }}
        />
      )}

      {/* ── #103 Follow-up chat thread ── */}
      {done && (
        <FollowupChat
          symbol={symbol}
          exchange={exchange}
          analysts={analysts}
          synthesisText={synthesis_text}
          report={report}
          port={port}
          value={followupValue}
          setValue={setFollowupValue}
          loading={followupLoading}
          setLoading={setFollowupLoading}
          thread={followupThread}
          setThread={setFollowupThread}
          error={followupError}
          setError={setFollowupError}
          inputRef={followupRef}
          pendingContext={pendingContext}
          clearPendingContext={clearPendingContext}
        />
      )}

      <div ref={bottomRef} />
    </div>
  )
}

function AnalystPill({ result, name, idx, cls }) {
  const [visible, setVisible]   = React.useState(false)
  const [expanded, setExpanded] = React.useState(true)
  const hasPoints = result.key_points && result.key_points.length > 0

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), idx * 80)
    return () => clearTimeout(t)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className={`border rounded-lg transition-all duration-300 ${cls}
                  ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'}
                  ${hasPoints ? 'cursor-pointer' : ''}`}
      onClick={() => hasPoints && setExpanded(v => !v)}
    >
      {/* Pill header row */}
      <div className="flex items-center gap-1.5 px-2.5 py-1">
        <span className="text-[11px] font-ui font-semibold">{DISPLAY_NAMES[name]}</span>
        {!result.error && (
          <span className="opacity-60 text-[10px] font-ui">
            {result.verdict} {result.confidence}%
          </span>
        )}
        {result.error && (
          <span className="opacity-60 text-[10px] font-ui">ERR</span>
        )}
        {hasPoints && (
          <span className="ml-auto opacity-30 text-[9px] font-mono">{expanded ? '▴' : '▾'}</span>
        )}
        {!hasPoints && result.error && (
          <span className="ml-auto opacity-30 text-[9px] font-mono text-red">!</span>
        )}
      </div>

      {/* Expanded key points */}
      {expanded && hasPoints && (
        <ul className="px-2.5 pb-2 space-y-0.5 border-t border-current/10 pt-1.5">
          {result.key_points.map((pt, i) => (
            <li key={i} className="text-[10px] font-ui opacity-80 leading-snug flex gap-1">
              <span className="opacity-50 flex-shrink-0">·</span>
              <span>{pt}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function DebateStep({ meta, text }) {
  const [expanded, setExpanded] = React.useState(false)
  const preview = text.slice(0, 180).replace(/\n/g, ' ')

  return (
    <div className="bg-panel rounded-lg border border-border overflow-hidden">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-elevated transition-colors"
      >
        <span className={`text-xs font-mono ${meta.color}`}>{meta.icon}</span>
        <span className={`text-xs font-ui font-semibold ${meta.color} flex-1`}>{meta.label}</span>
        <span className="text-muted text-[10px] font-mono">{expanded ? '▴' : '▾'}</span>
      </button>
      {!expanded && (
        <p className="px-3 pb-2 text-muted text-[11px] font-ui leading-relaxed line-clamp-2">
          {preview}{text.length > 180 ? '…' : ''}
        </p>
      )}
      {expanded && (
        <p className="px-3 pb-3 text-text text-xs font-ui leading-relaxed whitespace-pre-wrap border-t border-border pt-2">
          {text}
        </p>
      )}
    </div>
  )
}

function PhaseLabel({ label, active, done }) {
  let icon = '○'
  let cls  = 'text-subtle'
  if (done)        { icon = '✓'; cls = 'text-green' }
  else if (active) { icon = '◆'; cls = 'text-amber animate-pulse' }

  return (
    <span className={`text-xs font-ui flex items-center gap-1.5 ${cls}`}>
      <span>{icon}</span>
      <span>{label}</span>
    </span>
  )
}

function TradePlans({ plans }) {
  const entries = Object.entries(plans).filter(([, v]) => v != null)
  if (!entries.length) return null

  return (
    <div className="border-t border-border pt-3 space-y-3">
      <p className="text-amber text-[10px] uppercase tracking-widest font-ui">Trade Plans</p>
      {entries.map(([name, plan]) => (
        <div key={name} className="bg-panel rounded-lg p-3 border border-border">
          <p className="text-amber text-xs font-ui uppercase tracking-wider mb-2">{name}</p>
          <pre className="text-text text-xs font-mono whitespace-pre-wrap leading-relaxed">
            {typeof plan === 'string' ? plan : JSON.stringify(plan, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}

// ── #104 Action chips ─────────────────────────────────────────

function ActionChips({ symbol, analysts, setDraft, onAsk }) {
  // Derive majority verdict from analysts
  const verdictCounts = {}
  for (const a of analysts) {
    const v = (a.verdict ?? '').toUpperCase()
    if (v) verdictCounts[v] = (verdictCounts[v] ?? 0) + 1
  }
  const topVerdict = Object.entries(verdictCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'BULLISH'
  const viewWord   = topVerdict === 'BEARISH' ? 'bearish' : topVerdict === 'NEUTRAL' ? 'neutral' : 'bullish'

  const chips = [
    { label: '🔔 Set alert',       action: () => setDraft(`alert ${symbol} RSI below 35`) },
    { label: '📊 Options strategy', action: () => onAsk(`Suggest a specific options strategy for ${symbol} given the ${viewWord} outlook. Include strikes, expiry, and max risk.`) },
    { label: '💰 Entry & target',   action: () => onAsk(`What is the ideal entry price, stop-loss, and target for ${symbol} given this analysis?`) },
    { label: '⚠️ Key risks',        action: () => onAsk(`What are the biggest risks that could invalidate this ${viewWord} thesis on ${symbol}?`) },
    { label: '🔄 Re-analyze',       action: () => setDraft(`analyze ${symbol}`) },
  ]

  return (
    <div className="border-t border-border pt-3">
      <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Suggested actions</p>
      <div className="flex flex-wrap gap-2">
        {chips.map(({ label, action }) => (
          <button
            key={label}
            onClick={action}
            className="text-[11px] font-ui border border-border/60 rounded-lg px-2.5 py-1
                       text-muted hover:text-text hover:border-border hover:bg-panel
                       transition-colors"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── #103 Follow-up chat ───────────────────────────────────────

function FollowupChat({
  symbol, exchange, analysts, synthesisText, report, port,
  value, setValue, loading, setLoading, thread, setThread,
  error, setError, inputRef, pendingContext, clearPendingContext,
}) {
  // Capture pendingContext at mount time so we don't lose it if store updates
  const mountedPendingRef = useRef(pendingContext)

  // Auto-inject pending context from mid-stream typing (#102) — auto-submit on mount
  useEffect(() => {
    const q = (mountedPendingRef.current || '').trim()
    if (!q || thread.length > 0 || !port) return
    clearPendingContext()
    mountedPendingRef.current = ''

    setValue('')
    setError(null)
    setLoading(true)
    setThread([{ q, a: null }])  // show user question immediately while waiting
    ;(async () => {
      try {
        const res = await fetch(`http://127.0.0.1:${port}/skills/analyze/followup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol, exchange,
            question: q,
            session_id: `${symbol}_${exchange}`,
            context: {
              analysts: analysts.map(a => ({ name: a.name, verdict: a.verdict, confidence: a.confidence, key_points: a.key_points })),
              synthesis_text: synthesisText,
              report,
            },
          }),
        })
        const json = await res.json()
        const answer = json?.data?.response ?? json?.data ?? 'No response'
        setThread([{ q, a: answer }])
      } catch (e) {
        setThread([])
        setError('Follow-up failed: ' + e.message)
      } finally {
        setLoading(false)
        inputRef.current?.focus()
      }
    })()
  }, [pendingContext, port]) // eslint-disable-line react-hooks/exhaustive-deps

  async function ask() {
    const q = value.trim()
    if (!q || loading || !port) return
    setValue('')
    setError(null)
    setLoading(true)

    try {
      const res = await fetch(`http://127.0.0.1:${port}/skills/analyze/followup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          exchange,
          question: q,
          session_id: `${symbol}_${exchange}`,
          context: {
            analysts,
            synthesis_text: synthesisText,
            report,
          },
        }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail?.message ?? json.detail ?? 'Request failed')
      const answer = json.data?.response ?? '(no response)'
      setThread((t) => [...t, { q, a: answer }])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() }
  }

  return (
    <div className="border-t border-border pt-3 space-y-3">
      <p className="text-blue text-[10px] uppercase tracking-widest font-ui">Follow-up</p>

      {/* Thread */}
      {thread.map(({ q, a }, i) => (
        <div key={i} className="space-y-1.5">
          <div className="flex gap-2">
            <span className="text-muted text-[10px] font-mono mt-0.5 flex-shrink-0">you</span>
            <p className="text-text text-[12px] font-ui">{q}</p>
          </div>
          <div className="flex gap-2">
            <span className="text-blue text-[10px] font-mono mt-0.5 flex-shrink-0">ai</span>
            <p className="text-text text-[12px] font-ui leading-relaxed whitespace-pre-wrap">{a}</p>
          </div>
        </div>
      ))}

      {loading && (
        <div className="flex gap-2 items-start bg-blue/5 border border-blue/20 rounded-lg px-3 py-2">
          <span className="text-blue text-[10px] font-mono mt-0.5 flex-shrink-0">ai</span>
          <div className="flex items-center gap-1.5">
            <span className="text-blue text-[11px] font-ui">Thinking</span>
            <span className="flex gap-0.5">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="w-1 h-1 rounded-full bg-blue animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </span>
          </div>
        </div>
      )}

      {error && (
        <p className="text-red text-[11px] font-ui">⚠ {error}</p>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 bg-panel border border-border rounded-lg px-3 py-2">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={`Ask about ${symbol}…`}
          disabled={loading}
          className="flex-1 bg-transparent text-text text-[12px] font-mono outline-none
                     placeholder:text-subtle disabled:opacity-50"
        />
        <button
          onClick={ask}
          disabled={!value.trim() || loading}
          className="text-blue text-[11px] font-mono disabled:opacity-30 hover:opacity-80 transition-opacity"
        >
          ↵
        </button>
      </div>
    </div>
  )
}
