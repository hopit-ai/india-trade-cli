import { useState } from 'react'

function fitBadge(score) {
  const s = Number(score ?? 0)
  if (s >= 80) return 'text-green border-green/30'
  if (s >= 60) return 'text-amber border-amber/30'
  return 'text-muted border-border'
}

function StrategyBlock({ strat, isTop }) {
  const [expanded, setExpanded] = useState(false)
  const legs = strat.legs ?? []
  const breakeven = strat.breakeven ?? []
  const fitScore = Number(strat.fit_score ?? 0)

  return (
    <div className={`border rounded-lg p-3 space-y-2 ${isTop ? 'border-amber/40 bg-amber/5' : 'border-border'}`}>
      {/* Name + fit score */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {isTop && <span className="text-amber text-[11px]">⭐ Top Pick</span>}
          <p className="text-text text-[13px] font-semibold font-ui truncate">{strat.name ?? '—'}</p>
        </div>
        <span className={`text-[10px] font-ui border px-1.5 py-0.5 rounded shrink-0 ${fitBadge(fitScore)}`}>
          Fit {fitScore}
        </span>
      </div>

      {/* Description */}
      {strat.description && (
        <p className="text-muted text-[11px] font-ui">{strat.description}</p>
      )}

      {/* Legs */}
      {legs.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {legs.map((leg, i) => {
            const action = (leg.action ?? '').toUpperCase()
            return (
              <span
                key={i}
                className={`text-[10px] font-mono border rounded px-1.5 py-0.5 ${
                  action === 'BUY' ? 'text-green border-green/30 bg-green/5'
                  : action === 'SELL' ? 'text-red border-red/30 bg-red/5'
                  : 'text-muted border-border'
                }`}
              >
                {action} {leg.strike ? Number(leg.strike).toLocaleString('en-IN') : ''} {leg.type ?? ''}
                {leg.lots ? ` ×${leg.lots}` : ''}
              </span>
            )
          })}
        </div>
      )}

      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-1.5 text-[10px] font-mono">
        {[
          { label: 'Capital', value: strat.capital_needed != null ? `₹${Number(strat.capital_needed).toLocaleString('en-IN')}` : '—' },
          { label: 'Max Profit', value: strat.max_profit != null ? (strat.max_profit === Infinity || strat.max_profit === 'unlimited' ? '∞' : `₹${Number(strat.max_profit).toLocaleString('en-IN')}`) : '—', green: true },
          { label: 'Max Loss', value: strat.max_loss != null ? `₹${Number(strat.max_loss).toLocaleString('en-IN')}` : '—', red: true },
          { label: 'R:R', value: strat.rr_ratio != null ? `${Number(strat.rr_ratio).toFixed(1)}x` : '—' },
        ].map(m => (
          <div key={m.label} className="bg-panel border border-border rounded p-1.5">
            <p className="text-muted text-[9px] uppercase tracking-wider">{m.label}</p>
            <p className={`font-semibold mt-0.5 ${m.green ? 'text-green' : m.red ? 'text-red' : 'text-text'}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Breakeven */}
      {breakeven.length > 0 && (
        <p className="text-muted text-[10px] font-mono">
          BE: {breakeven.map(b => `₹${Number(b).toLocaleString('en-IN')}`).join(' / ')}
        </p>
      )}

      {/* Best for / Risks (expand toggle) */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="text-blue text-[10px] font-ui hover:underline"
      >
        {expanded ? '▲ Hide details' : '▼ Best for & risks'}
      </button>
      {expanded && (
        <div className="space-y-1.5 pt-1 border-t border-border">
          {strat.best_for && (
            <p className="text-green text-[11px] font-ui">✓ {strat.best_for}</p>
          )}
          {strat.risks && (
            <p className="text-red text-[11px] font-ui">⚠ {strat.risks}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function StrategyCard({ data }) {
  const d = data?.data ?? data ?? {}
  const symbol = d.symbol ?? '—'
  const view = d.view ?? '—'
  const dte = d.dte ?? '—'
  const topName = d.top?.name ?? null
  const strategies = (d.strategies ?? []).slice(0, 3)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div>
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Strategy Recommendations</p>
        <p className="text-text text-[14px] font-mono font-semibold mt-0.5">
          {symbol}
          <span className="text-muted font-normal text-[12px]"> | {view} | {dte} days</span>
        </p>
      </div>

      {strategies.length === 0 ? (
        <p className="text-muted text-[12px] font-ui text-center py-4">No strategies available</p>
      ) : (
        <div className="space-y-2">
          {strategies.map((strat, i) => (
            <StrategyBlock key={i} strat={strat} isTop={topName != null && strat.name === topName} />
          ))}
        </div>
      )}
    </div>
  )
}
