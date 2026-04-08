function signalBadge(signal) {
  const s = (signal ?? '').toUpperCase()
  if (s.includes('BUY')) return { text: s, cls: 'text-green border-green/30' }
  if (s.includes('SELL')) return { text: s, cls: 'text-red border-red/30' }
  return { text: s || 'NEUTRAL', cls: 'text-muted border-border' }
}

function corrColor(v) {
  const n = Math.abs(Number(v ?? 0))
  if (n >= 0.8) return 'text-green'
  if (n >= 0.5) return 'text-amber'
  return 'text-red'
}

export default function PairsCard({ data }) {
  const d = data?.data ?? data ?? {}
  const stockA = d.stock_a ?? d.symbol_a ?? '—'
  const stockB = d.stock_b ?? d.symbol_b ?? '—'
  const correlation = Number(d.correlation ?? 0)
  const zScore = Number(d.z_score ?? 0)
  const spreadMean = Number(d.spread_mean ?? 0)
  const spreadStd = Number(d.spread_std ?? 0)
  const cointegrated = d.cointegrated ?? null
  const sig = signalBadge(d.signal)

  const metrics = [
    { label: 'Correlation', value: correlation.toFixed(3), color: corrColor(correlation) },
    { label: 'Z-Score', value: zScore.toFixed(2), color: Math.abs(zScore) > 2 ? 'text-amber' : Math.abs(zScore) > 3 ? 'text-red' : 'text-text' },
    { label: 'Spread Mean', value: spreadMean.toFixed(4), color: 'text-text' },
    { label: 'Spread Std', value: spreadStd.toFixed(4), color: 'text-text' },
  ]

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Pairs Analysis</p>
          <p className="text-text text-lg font-mono font-semibold mt-0.5">
            {stockA} <span className="text-muted">vs</span> {stockB}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {cointegrated != null && (
            <span className={`text-[10px] font-ui border px-1.5 py-0.5 rounded ${cointegrated ? 'text-green border-green/30' : 'text-muted border-border'}`}>
              {cointegrated ? 'Cointegrated' : 'Not Cointegrated'}
            </span>
          )}
          <span className={`text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${sig.cls}`}>
            {sig.text}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-2">
        {metrics.map(m => (
          <div key={m.label} className="bg-panel border border-border rounded-lg p-2.5">
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{m.label}</p>
            <p className={`text-[14px] font-mono font-semibold mt-1 ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Description */}
      {d.description && (
        <div className="border border-border rounded-lg px-3 py-2">
          <p className="text-muted text-[11px] font-ui leading-relaxed">{d.description}</p>
        </div>
      )}
    </div>
  )
}
