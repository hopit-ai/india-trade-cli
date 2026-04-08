function verdictColor(v) {
  const s = (v ?? '').toUpperCase()
  if (s === 'BULLISH') return 'text-green'
  if (s === 'BEARISH') return 'text-red'
  return 'text-amber'
}

function outcomeColor(o) {
  const s = (o ?? '').toUpperCase()
  if (s === 'WIN') return 'text-green'
  if (s === 'LOSS') return 'text-red'
  if (s === 'BREAKEVEN') return 'text-muted'
  return 'text-subtle'
}

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

export default function MemoryCard({ data }) {
  const d       = data?.data ?? data ?? {}
  const stats   = d.stats   ?? {}
  const records = d.records ?? []

  const winRate  = Number(stats.win_rate  ?? 0)
  const totalPnl = Number(stats.total_pnl ?? 0)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Trade Memory</p>

      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'Analyses', value: stats.total_analyses ?? 0 },
          { label: 'Win Rate', value: `${winRate.toFixed(1)}%`, color: winRate >= 55 ? 'text-green' : winRate < 40 ? 'text-red' : 'text-amber' },
          { label: 'Total P&L', value: `${totalPnl >= 0 ? '+' : ''}₹${Math.abs(totalPnl).toLocaleString('en-IN')}`, color: totalPnl >= 0 ? 'text-green' : 'text-red' },
          { label: 'Avg Conf', value: `${Number(stats.avg_confidence ?? 0).toFixed(0)}%` },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-panel border border-border rounded-lg p-2 text-center">
            <p className="text-muted text-[9px] uppercase tracking-wider font-ui">{label}</p>
            <p className={`text-[13px] font-mono font-semibold mt-0.5 ${color ?? 'text-text'}`}>{value}</p>
          </div>
        ))}
      </div>

      {records.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-muted text-[9px] uppercase tracking-wider font-ui border-b border-border">
                <th className="pb-1 text-left pr-3">Date</th>
                <th className="pb-1 text-left pr-3">Symbol</th>
                <th className="pb-1 text-left pr-3">Verdict</th>
                <th className="pb-1 text-right pr-3">Conf</th>
                <th className="pb-1 text-left pr-3">Outcome</th>
                <th className="pb-1 text-right">P&L</th>
              </tr>
            </thead>
            <tbody>
              {records.slice(0, 12).map((r, i) => {
                const pnl = r.pnl != null ? Number(r.pnl) : null
                return (
                  <tr key={i} className="border-b border-border/50 hover:bg-panel/50">
                    <td className="py-1 pr-3 font-mono text-muted">{fmtDate(r.created_at ?? r.date)}</td>
                    <td className="py-1 pr-3 font-mono text-text font-semibold">{r.symbol ?? '—'}</td>
                    <td className={`py-1 pr-3 font-ui ${verdictColor(r.verdict)}`}>{r.verdict ?? '—'}</td>
                    <td className="py-1 pr-3 font-mono text-muted text-right">{r.confidence ? `${r.confidence}%` : '—'}</td>
                    <td className={`py-1 pr-3 font-ui ${outcomeColor(r.outcome)}`}>{r.outcome ?? '—'}</td>
                    <td className={`py-1 font-mono text-right ${pnl == null ? 'text-subtle' : pnl >= 0 ? 'text-green' : 'text-red'}`}>
                      {pnl == null ? '—' : `${pnl >= 0 ? '+' : ''}₹${Math.abs(pnl).toLocaleString('en-IN')}`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {records.length > 12 && (
            <p className="text-subtle text-[10px] font-ui mt-1">{records.length - 12} more — use memory query to filter</p>
          )}
        </div>
      ) : (
        <p className="text-muted text-[12px] font-ui text-center py-4">No trade records yet. Run analyze SYMBOL to start building memory.</p>
      )}
    </div>
  )
}
