/**
 * StreamingAnalysisCard
 *
 * Renders live progress as multi-agent analysis SSE events arrive:
 *  – Analyst pills light up one by one as they complete
 *  – Phase labels flip from dim → active → done
 *  – Full AnalysisCard content appears once "done" arrives
 */
import React, { useEffect, useRef } from 'react'
import { useChatStore } from '../../store/chatStore'

const ANALYSTS = [
  'TechnicalAnalyst',
  'FundamentalAnalyst',
  'OptionsAnalyst',
  'NewsMacroAnalyst',
  'SentimentAnalyst',
  'SectorRotationAnalyst',
  'RiskAnalyst',
]

const DISPLAY_NAMES = {
  TechnicalAnalyst:     'Technical',
  FundamentalAnalyst:   'Fundamental',
  OptionsAnalyst:       'Options',
  NewsMacroAnalyst:     'News / Macro',
  SentimentAnalyst:     'Sentiment',
  SectorRotationAnalyst:'Sector',
  RiskAnalyst:          'Risk',
}

const VERDICT_COLOR = {
  BUY:     'text-green border-green/40 bg-green/5',
  SELL:    'text-red border-red/40 bg-red/5',
  HOLD:    'text-amber border-amber/40 bg-amber/5',
  UNKNOWN: 'text-muted border-border',
}

const STEP_META = {
  bull_r1:     { label: 'Bull Researcher',  color: 'text-green', icon: '▲' },
  bear_r1:     { label: 'Bear Researcher',  color: 'text-red',   icon: '▼' },
  bull_r2:     { label: 'Bull Rebuttal',    color: 'text-green', icon: '▲' },
  bear_r2:     { label: 'Bear Rebuttal',    color: 'text-red',   icon: '▼' },
  facilitator: { label: 'Facilitator',      color: 'text-blue',  icon: '◈' },
}

export default function StreamingAnalysisCard({ data }) {
  const cancelStream = useChatStore((s) => s.cancelStream)
  const streamCancel = useChatStore((s) => s.streamCancel)
  const bottomRef    = useRef(null)

  if (!data) return null
  const { symbol, exchange, analysts, debate_steps = [], synthesis_text, phase, report, trade_plans } = data

  // Auto-scroll card bottom into view whenever new content arrives
  // eslint-disable-next-line react-hooks/rules-of-hooks
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [analysts.length, debate_steps.length, synthesis_text, done])

  const done     = phase === 'done'
  const started  = phase !== 'analysts'   // received 'started' event
  const debating = phase === 'debate' || phase === 'synthesis' || done
  const synth    = phase === 'synthesis' || done
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
        <div className="flex flex-wrap gap-2">
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
              <span
                key={name}
                className={`border text-[11px] font-ui px-2.5 py-1 rounded-lg
                            animate-fade-slide ${cls}`}
                style={{ animationDelay: `${idx * 300}ms`, animationFillMode: 'both',
                         opacity: 0 /* hidden until animation starts */ }}
              >
                {DISPLAY_NAMES[name]}
                {!result.error && (
                  <span className="ml-1 opacity-60 text-[10px]">
                    {result.verdict} {result.confidence}%
                  </span>
                )}
              </span>
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

      <div ref={bottomRef} />
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
