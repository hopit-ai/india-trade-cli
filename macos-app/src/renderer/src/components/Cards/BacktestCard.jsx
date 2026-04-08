export default function BacktestCard({ data }) {
  if (!data) return null

  const r = data

  const metrics = [
    ['Total Return',   pct(r.total_return)],
    ['CAGR',          pct(r.cagr)],
    ['Sharpe',        num(r.sharpe_ratio ?? r.sharpe)],
    ['Max Drawdown',  pct(r.max_drawdown)],
    ['Win Rate',      pct(r.win_rate)],
    ['Total Trades',  r.total_trades ?? '—'],
    ['Profit Factor', num(r.profit_factor)],
    ['Avg Hold',      r.avg_hold_days ? `${r.avg_hold_days}d` : '—'],
  ]

  const returnVal = Number(r.total_return ?? 0)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-lg w-full">

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui mb-1">Backtest</p>
          <p className="text-text text-lg font-semibold font-mono">
            {r.symbol} <span className="text-muted text-sm">·</span>{' '}
            <span className="text-amber text-sm">{r.strategy}</span>
          </p>
          {r.period && <p className="text-muted text-xs font-ui mt-0.5">{r.period}</p>}
        </div>
        <p className={`text-2xl font-mono font-bold ${returnVal >= 0 ? 'text-green' : 'text-red'}`}>
          {returnVal >= 0 ? '+' : ''}{pct(returnVal)}
        </p>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-4 gap-3 border-t border-border pt-3">
        {metrics.map(([label, val]) => (
          <div key={label}>
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
            <p className="text-text text-sm font-mono mt-0.5">{val}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

const pct = (n) => `${Number(n ?? 0).toFixed(2)}%`
const num = (n) => Number(n ?? 0).toFixed(2)
