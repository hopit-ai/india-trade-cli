function fmt(n) {
  return Number(n ?? 0).toLocaleString('en-IN')
}

function pct(n) {
  return (Number(n ?? 0) * 100).toFixed(2) + '%'
}

function concColor(risk) {
  const r = (risk ?? '').toUpperCase()
  if (r === 'LOW') return 'text-green border-green/30'
  if (r === 'HIGH') return 'text-red border-red/30'
  return 'text-amber border-amber/30'
}

export default function RiskReportCard({ data }) {
  const d = data?.data ?? data ?? {}
  const demo = d.demo ?? false
  const portfolioValue = Number(d.portfolio_value ?? 0)
  const holdings = (d.holding_vars ?? []).slice().sort((a, b) => Math.abs(Number(b.var_95 ?? 0)) - Math.abs(Number(a.var_95 ?? 0)))
  const highCorr = d.high_correlations ?? []
  const concRisk = d.concentration_risk ?? 'MEDIUM'

  const tiles = [
    { label: 'Portfolio Value', value: `₹${fmt(d.portfolio_value)}` },
    { label: '1-day VaR 95%', value: `₹${fmt(d.portfolio_var_95)}`, sub: 'at 95% confidence' },
    { label: 'VaR 99%', value: `₹${fmt(d.portfolio_var_99)}`, sub: 'at 99% confidence' },
    { label: 'Volatility', value: `${Number(d.portfolio_volatility ?? 0).toFixed(1)}%`, sub: 'annualised' },
  ]

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Risk Report</p>
        <div className="flex items-center gap-2">
          {demo && (
            <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>
          )}
          <span className={`text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${concColor(concRisk)}`}>
            {concRisk} CONCENTRATION
          </span>
        </div>
      </div>

      {demo && d.message && (
        <div className="border border-amber/30 bg-amber/5 rounded-lg px-3 py-2">
          <p className="text-amber text-[11px] font-ui">⚠ {d.message}</p>
        </div>
      )}

      {/* Metric tiles */}
      <div className="grid grid-cols-2 gap-2">
        {tiles.map(t => (
          <div key={t.label} className="bg-panel border border-border rounded-lg p-3">
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{t.label}</p>
            <p className="text-text text-[15px] font-mono font-semibold mt-1">{t.value}</p>
            {t.sub && <p className="text-muted text-[10px] font-ui mt-0.5">{t.sub}</p>}
          </div>
        ))}
      </div>

      {/* Holdings VaR */}
      {holdings.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Top Holdings by VaR</p>
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-muted uppercase tracking-wider border-b border-border">
                <th className="text-left pb-2">Symbol</th>
                <th className="text-right pb-2">Weight%</th>
                <th className="text-right pb-2">1-day VaR</th>
              </tr>
            </thead>
            <tbody>
              {holdings.slice(0, 8).map((h, i) => (
                <tr key={i} className="border-b border-border/40 last:border-0">
                  <td className="py-1.5 text-text">{h.symbol ?? '—'}</td>
                  <td className="py-1.5 text-right text-muted">
                    {portfolioValue > 0 ? (Number(h.position_value ?? 0) / portfolioValue * 100).toFixed(1) : '0.0'}%
                  </td>
                  <td className="py-1.5 text-right text-red">₹{fmt(h.var_95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* High correlation warnings */}
      {highCorr.length > 0 && (
        <div className="border-t border-border pt-2 space-y-1">
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-1">Correlation Warnings</p>
          {highCorr.map((c, i) => (
            <p key={i} className="text-amber text-[11px] font-ui flex gap-1.5">
              <span>⚠</span>
              <span>{typeof c === 'string' ? c : JSON.stringify(c)}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
