function qualityColor(q) {
  const s = (q ?? '').toUpperCase()
  if (s === 'GOOD') return 'text-green'
  if (s === 'FAIR') return 'text-amber'
  return 'text-red'
}

function outcomeColor(o) {
  const s = (o ?? '').toUpperCase()
  if (s === 'WIN') return 'text-green'
  if (s === 'LOSS') return 'text-red'
  return 'text-muted'
}

export default function AuditCard({ data }) {
  const d = data?.data ?? data ?? {}
  const grades  = d.analyst_grades ?? []
  const lessons = d.lessons ?? []
  const pnl     = d.pnl != null ? Number(d.pnl) : null

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Trade Audit</p>
          <p className="text-text text-lg font-mono font-semibold mt-0.5">{d.symbol ?? '—'}</p>
        </div>
        <div className="text-right space-y-1">
          {d.outcome && (
            <span className={`text-[12px] font-ui font-semibold border rounded px-2 py-0.5 ${
              d.outcome === 'WIN' ? 'text-green border-green/30 bg-green/5'
              : d.outcome === 'LOSS' ? 'text-red border-red/30 bg-red/5'
              : 'text-muted border-border'
            }`}>{d.outcome}</span>
          )}
          {pnl != null && (
            <p className={`text-[12px] font-mono ${pnl >= 0 ? 'text-green' : 'text-red'}`}>
              {pnl >= 0 ? '+' : ''}₹{Math.abs(pnl).toLocaleString('en-IN')}
            </p>
          )}
        </div>
      </div>

      {/* Quality row */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Entry', value: d.entry_quality },
          { label: 'Stop-Loss', value: d.sl_assessment },
          { label: 'Hold', value: d.hold_assessment },
        ].map(({ label, value }) => (
          <div key={label} className="bg-panel border border-border rounded-lg p-2 text-center">
            <p className="text-muted text-[9px] uppercase tracking-wider font-ui">{label}</p>
            <p className={`text-[12px] font-ui font-semibold mt-0.5 ${qualityColor(value)}`}>{value ?? '—'}</p>
          </div>
        ))}
      </div>

      {/* Analyst grades */}
      {grades.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Analyst Grades</p>
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-muted text-[9px] font-ui border-b border-border">
                <th className="pb-1 text-left pr-3">Analyst</th>
                <th className="pb-1 text-left pr-3">Grade</th>
                <th className="pb-1 text-right">Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {grades.map((g, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-1 pr-3 font-ui text-text">{g.analyst ?? '—'}</td>
                  <td className={`py-1 pr-3 font-mono font-semibold ${
                    g.grade === 'A' ? 'text-green' : g.grade === 'B' ? 'text-blue' : g.grade === 'C' ? 'text-amber' : 'text-red'
                  }`}>{g.grade ?? '—'}</td>
                  <td className="py-1 font-mono text-muted text-right">{g.accuracy != null ? `${Number(g.accuracy).toFixed(0)}%` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Most accurate / most wrong */}
      {(d.most_accurate || d.most_wrong) && (
        <div className="flex gap-3 text-[11px]">
          {d.most_accurate && (
            <div className="flex-1 bg-green/5 border border-green/20 rounded-lg px-3 py-2">
              <p className="text-muted text-[9px] uppercase font-ui">Most Accurate</p>
              <p className="text-green font-ui font-semibold mt-0.5">{d.most_accurate}</p>
            </div>
          )}
          {d.most_wrong && (
            <div className="flex-1 bg-red/5 border border-red/20 rounded-lg px-3 py-2">
              <p className="text-muted text-[9px] uppercase font-ui">Most Wrong</p>
              <p className="text-red font-ui font-semibold mt-0.5">{d.most_wrong}</p>
            </div>
          )}
        </div>
      )}

      {/* Lessons */}
      {lessons.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Lessons</p>
          <ul className="space-y-1">
            {lessons.map((l, i) => (
              <li key={i} className="flex gap-2 text-[11px] font-ui text-text">
                <span className="text-blue mt-0.5">›</span>
                <span>{l}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
