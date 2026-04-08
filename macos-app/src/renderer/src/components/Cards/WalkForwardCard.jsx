function retColor(v) {
  const n = Number(v ?? 0)
  return n > 0 ? 'text-green' : n < 0 ? 'text-red' : 'text-muted'
}

export default function WalkForwardCard({ data }) {
  const d = data?.data ?? data ?? {}
  const symbol = d.symbol ?? '—'
  const strategy = d.strategy ?? d.strategy_name ?? '—'
  const windows = d.windows ?? []

  const avgReturn = Number(d.avg_return ?? d.average_return ?? 0)
  const avgSharpe = Number(d.avg_sharpe ?? d.average_sharpe ?? 0)
  const avgWinRate = Number(d.avg_win_rate ?? d.average_win_rate ?? 0)
  const consistency = d.consistency ?? null

  const summaryStats = [
    { label: 'Avg Return', value: `${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(2)}%`, color: retColor(avgReturn) },
    { label: 'Avg Sharpe', value: avgSharpe.toFixed(2), color: avgSharpe >= 1 ? 'text-green' : avgSharpe >= 0 ? 'text-amber' : 'text-red' },
    { label: 'Avg Win Rate', value: `${(avgWinRate * 100).toFixed(1)}%`, color: avgWinRate >= 0.55 ? 'text-green' : avgWinRate >= 0.45 ? 'text-amber' : 'text-red' },
    { label: 'Windows', value: String(windows.length), color: 'text-text' },
  ]

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div>
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Walk-Forward Backtest</p>
        <p className="text-text text-[14px] font-mono font-semibold mt-0.5">
          {symbol} <span className="text-muted font-normal">({strategy})</span>
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-2">
        {summaryStats.map(s => (
          <div key={s.label} className="bg-panel border border-border rounded-lg p-2.5">
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{s.label}</p>
            <p className={`text-[14px] font-mono font-semibold mt-1 ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Windows table */}
      {windows.length > 0 && (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-muted uppercase tracking-wider border-b border-border">
              <th className="text-left pb-2">Period</th>
              <th className="text-right pb-2">Return%</th>
              <th className="text-right pb-2">Sharpe</th>
              <th className="text-right pb-2">Win Rate</th>
              <th className="text-right pb-2">Trades</th>
            </tr>
          </thead>
          <tbody>
            {windows.map((w, i) => {
              const ret = Number(w.return_pct ?? w.return ?? 0)
              const sharpe = Number(w.sharpe ?? w.sharpe_ratio ?? 0)
              const winRate = Number(w.win_rate ?? 0)
              return (
                <tr key={i} className="border-b border-border/40 last:border-0">
                  <td className="py-1.5 text-text">{w.period ?? w.window ?? `W${i + 1}`}</td>
                  <td className={`py-1.5 text-right ${retColor(ret)}`}>
                    {ret >= 0 ? '+' : ''}{ret.toFixed(2)}%
                  </td>
                  <td className={`py-1.5 text-right ${sharpe >= 1 ? 'text-green' : sharpe >= 0 ? 'text-amber' : 'text-red'}`}>
                    {sharpe.toFixed(2)}
                  </td>
                  <td className="py-1.5 text-right text-text">
                    {(winRate * 100).toFixed(1)}%
                  </td>
                  <td className="py-1.5 text-right text-muted">{w.trades ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {/* Consistency note */}
      {consistency != null && (
        <div className="border-t border-border pt-2">
          <p className="text-muted text-[11px] font-ui">
            <span className="text-muted">Consistency: </span>
            <span className="text-text font-mono">{typeof consistency === 'number' ? `${(consistency * 100).toFixed(1)}%` : String(consistency)}</span>
          </p>
        </div>
      )}
    </div>
  )
}
