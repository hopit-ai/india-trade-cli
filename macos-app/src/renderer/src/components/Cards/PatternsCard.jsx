const IMPACT_COLOR = {
  high:    'text-red border-red/30 bg-red/5',
  medium:  'text-amber border-amber/30 bg-amber/5',
  low:     'text-muted border-border',
  bullish: 'text-green border-green/30 bg-green/5',
  bearish: 'text-red border-red/30 bg-red/5',
}

export default function PatternsCard({ data }) {
  const d        = data?.data ?? data ?? {}
  const patterns = d.patterns ?? d.active_patterns ?? (Array.isArray(data) ? data : [])

  if (!patterns.length) {
    return (
      <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">Active Patterns</p>
        <p className="text-muted text-sm font-ui">No active patterns detected.</p>
      </div>
    )
  }

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui">
        Active Patterns <span className="text-subtle">({patterns.length})</span>
      </p>
      {patterns.map((p, i) => {
        const impact = (p.impact ?? p.direction ?? 'medium').toLowerCase()
        const cls    = IMPACT_COLOR[impact] ?? IMPACT_COLOR.medium
        return (
          <div key={i} className={`border rounded-lg p-3 ${cls}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[12px] font-ui font-semibold">{p.name ?? p.pattern ?? '—'}</span>
              <div className="flex items-center gap-2">
                {p.confidence != null && (
                  <span className="text-[10px] font-ui opacity-70">{p.confidence}% conf</span>
                )}
                <span className={`text-[10px] font-ui uppercase border rounded px-1.5 py-0.5 ${cls}`}>
                  {impact}
                </span>
              </div>
            </div>
            {(p.description ?? p.action) && (
              <p className="text-[11px] font-ui opacity-80 leading-relaxed">
                {p.description ?? p.action}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
