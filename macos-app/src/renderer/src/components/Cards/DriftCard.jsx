function trendBadge(trend) {
  const t = (trend ?? '').toUpperCase()
  if (t === 'IMPROVING') return { text: 'IMPROVING', cls: 'text-green border-green/30' }
  if (t === 'DECLINING') return { text: 'DECLINING', cls: 'text-red border-red/30' }
  return { text: 'STABLE', cls: 'text-amber border-amber/30' }
}

function pct(v, decimals = 1) {
  return (Number(v ?? 0) * 100).toFixed(decimals) + '%'
}

export default function DriftCard({ data }) {
  const d = data?.data ?? data ?? {}
  const trend = trendBadge(d.win_rate_trend)
  const analystAcc = d.analyst_accuracy ?? {}
  const alerts = d.alerts ?? []
  const recentWr = Number(d.recent_win_rate ?? 0)
  const olderWr = Number(d.older_win_rate ?? 0)
  const delta = Number(d.win_rate_delta ?? (recentWr - olderWr))

  const dirTiles = [
    { label: 'BUY', value: d.buy_accuracy != null ? pct(d.buy_accuracy) : '—', color: 'text-green' },
    { label: 'SELL', value: d.sell_accuracy != null ? pct(d.sell_accuracy) : '—', color: 'text-red' },
    { label: 'HOLD', value: d.hold_accuracy != null ? pct(d.hold_accuracy) : '—', color: 'text-muted' },
  ]

  const analystRows = Object.entries(analystAcc).map(([name, acc]) => ({ name, acc: Number(acc) }))
    .sort((a, b) => b.acc - a.acc)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Model Accuracy Drift</p>
        <span className={`text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${trend.cls}`}>
          {trend.text}
        </span>
      </div>

      {/* Win rate comparison */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-panel border border-border rounded-lg p-3">
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui">Recent Win Rate</p>
          <p className="text-text text-[15px] font-mono font-semibold mt-1">{pct(recentWr)}</p>
        </div>
        <div className="bg-panel border border-border rounded-lg p-3">
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui">Older Win Rate</p>
          <p className="text-text text-[15px] font-mono font-semibold mt-1">{pct(olderWr)}</p>
        </div>
        <div className="bg-panel border border-border rounded-lg p-3">
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui">Δ Change</p>
          <p className={`text-[15px] font-mono font-semibold mt-1 ${delta > 0 ? 'text-green' : delta < 0 ? 'text-red' : 'text-muted'}`}>
            {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}pp
          </p>
        </div>
      </div>

      {/* Direction accuracy tiles */}
      <div>
        <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Direction Accuracy</p>
        <div className="flex gap-2">
          {dirTiles.map(t => (
            <div key={t.label} className="bg-panel border border-border rounded-lg p-2.5 flex-1 text-center">
              <p className="text-muted text-[10px] font-ui uppercase">{t.label}</p>
              <p className={`text-[15px] font-mono font-semibold mt-1 ${t.color}`}>{t.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Analyst accuracy table */}
      {analystRows.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Analyst Accuracy</p>
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-muted uppercase tracking-wider border-b border-border">
                <th className="text-left pb-2">Analyst</th>
                <th className="text-right pb-2">Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {analystRows.map((row, i) => (
                <tr key={i} className="border-b border-border/40 last:border-0">
                  <td className="py-1.5 text-text">{row.name}</td>
                  <td className={`py-1.5 text-right font-semibold ${row.acc >= 0.6 ? 'text-green' : row.acc >= 0.45 ? 'text-amber' : 'text-red'}`}>
                    {(row.acc * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="border-t border-border pt-2 space-y-1">
          {alerts.map((a, i) => (
            <p key={i} className="text-amber text-[11px] font-ui flex gap-1.5">
              <span>⚠</span><span>{typeof a === 'string' ? a : JSON.stringify(a)}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
