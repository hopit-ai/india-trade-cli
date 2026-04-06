/**
 * StreamingAnalysisCard
 *
 * Renders live progress as multi-agent analysis SSE events arrive:
 *  – Analyst pills light up one by one as they complete
 *  – Phase labels flip from dim → active → done
 *  – Full AnalysisCard content appears once "done" arrives
 */

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

export default function StreamingAnalysisCard({ data }) {
  if (!data) return null
  const { symbol, exchange, analysts, phase, report, trade_plans } = data

  const done     = phase === 'done'
  const debating = phase === 'debate' || phase === 'synthesis' || done
  const synth    = phase === 'synthesis' || done

  return (
    <div className="bg-elevated border border-blue/30 rounded-xl p-4 max-w-2xl w-full space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui">
            {done ? 'Analysis' : 'Analysis · Running…'}
          </p>
          <p className="text-text text-lg font-semibold font-mono mt-0.5">
            {symbol} <span className="text-muted text-sm font-ui">{exchange}</span>
          </p>
        </div>
        <span className={`text-xl ${done ? '' : 'animate-pulse'}`}>🔬</span>
      </div>

      {/* Analyst grid */}
      <div className="border-t border-border pt-3">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">
          Phase 1 — Analyst Team
        </p>
        <div className="flex flex-wrap gap-2">
          {ANALYSTS.map((name) => {
            const result = analysts.find((a) => a.name === name)
            const idle   = !result

            let cls = 'border text-[11px] font-ui px-2.5 py-1 rounded-lg transition-all '
            if (idle) {
              cls += 'text-subtle border-border/40 bg-panel/40'
            } else if (result.error) {
              cls += 'text-red border-red/30 bg-red/5'
            } else {
              cls += VERDICT_COLOR[result.verdict] ?? VERDICT_COLOR.UNKNOWN
            }

            return (
              <span key={name} className={cls}>
                {idle ? <span className="opacity-40">{DISPLAY_NAMES[name]}</span> : (
                  <>
                    {DISPLAY_NAMES[name]}
                    {!result.error && (
                      <span className="ml-1 opacity-60 text-[10px]">
                        {result.verdict} {result.confidence}%
                      </span>
                    )}
                  </>
                )}
              </span>
            )
          })}
        </div>
      </div>

      {/* Phase 2 + 3 status */}
      <div className="border-t border-border pt-3 flex gap-4">
        <PhaseLabel label="Phase 2 — Debate" active={debating} done={synth} />
        <PhaseLabel label="Phase 3 — Synthesis" active={synth} done={done} />
      </div>

      {/* Final report — shown once done */}
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
