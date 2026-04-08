function Metric({ label, value, hint }) {
  const v = Number(value ?? 0)
  const colored = label === 'Delta' ? (v > 0 ? 'text-green' : v < 0 ? 'text-red' : 'text-text')
                : label === 'Theta' ? 'text-red'
                : 'text-text'
  return (
    <div className="bg-panel rounded-lg p-3 border border-border">
      <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
      <p className={`text-[16px] font-mono font-semibold mt-1 ${colored}`}>
        {v >= 0 && label !== 'IV' ? '+' : ''}{v.toFixed(2)}
      </p>
      {hint && <p className="text-subtle text-[10px] font-ui mt-0.5">{hint}</p>}
    </div>
  )
}

export default function GreeksCard({ data }) {
  const d    = data?.data ?? data ?? {}
  const demo = d.demo ?? false

  const net = d.net ?? d.portfolio_greeks ?? {}

  const metrics = [
    { label: 'Delta', value: net.delta ?? net.net_delta ?? 0,  hint: 'Portfolio directional exposure' },
    { label: 'Theta', value: net.theta ?? net.net_theta ?? 0,  hint: 'Daily time decay (₹)' },
    { label: 'Vega',  value: net.vega  ?? net.net_vega  ?? 0,  hint: 'IV sensitivity' },
    { label: 'Gamma', value: net.gamma ?? net.net_gamma ?? 0,  hint: 'Delta change rate' },
  ]

  const warnings = d.warnings ?? d.risk_warnings ?? []
  const positions = d.positions ?? d.by_position ?? []

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Portfolio Greeks</p>
        {demo && <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {metrics.map(m => <Metric key={m.label} {...m} />)}
      </div>

      {warnings.length > 0 && (
        <div className="space-y-1">
          {warnings.map((w, i) => (
            <p key={i} className="text-amber text-[11px] font-ui flex gap-1.5">
              <span>⚠</span><span>{typeof w === 'string' ? w : w.message ?? JSON.stringify(w)}</span>
            </p>
          ))}
        </div>
      )}

      {positions.length > 0 && (
        <div className="border-t border-border pt-3">
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">By Position</p>
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-muted border-b border-border">
                <th className="text-left pb-1.5">Symbol</th>
                <th className="text-right pb-1.5">Δ Delta</th>
                <th className="text-right pb-1.5">Θ Theta</th>
                <th className="text-right pb-1.5">ν Vega</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i} className="border-b border-border/40 last:border-0">
                  <td className="py-1.5 text-text">{p.symbol ?? p.underlying ?? '—'}</td>
                  <td className={`py-1.5 text-right ${Number(p.delta ?? 0) >= 0 ? 'text-green' : 'text-red'}`}>
                    {Number(p.delta ?? 0).toFixed(2)}
                  </td>
                  <td className="py-1.5 text-right text-red">{Number(p.theta ?? 0).toFixed(2)}</td>
                  <td className="py-1.5 text-right text-text">{Number(p.vega ?? 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
