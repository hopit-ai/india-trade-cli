function pnlColor(v) {
  const n = Number(v ?? 0)
  return n > 0 ? 'text-green' : n < 0 ? 'text-red' : 'text-muted'
}

function fmt(n) {
  return Number(n ?? 0).toLocaleString('en-IN')
}

function ScenarioMini({ sc }) {
  const pnl = Number(sc.projected_pnl ?? 0)
  const pct = Number(sc.projected_pnl_pct ?? 0)
  return (
    <div className="bg-panel border border-border rounded-lg p-3 flex-1 min-w-0">
      <p className="text-muted text-[10px] font-ui uppercase tracking-wider truncate">{sc.scenario_name ?? 'Scenario'}</p>
      <p className={`text-[15px] font-mono font-semibold mt-1 ${pnlColor(pnl)}`}>
        {pnl >= 0 ? '+' : ''}₹{fmt(pnl)}
      </p>
      <p className={`text-[11px] font-mono ${pnlColor(pct)}`}>
        {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
      </p>
    </div>
  )
}

export default function WhatIfCard({ data }) {
  const d = data?.data ?? data ?? {}
  const demo = d.demo ?? false

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">What-If Analysis</p>
        {demo && (
          <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>
        )}
      </div>

      {demo && d.message && (
        <div className="border border-amber/30 bg-amber/5 rounded-lg px-3 py-2">
          <p className="text-amber text-[11px] font-ui">⚠ {d.message}</p>
        </div>
      )}

      {/* Multi-scenario mode */}
      {d.multi && d.scenarios?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {d.scenarios.map((sc, i) => (
            <ScenarioMini key={i} sc={sc} />
          ))}
        </div>
      )}

      {/* Single-scenario mode */}
      {!d.multi && (
        <>
          {d.scenario_name && (
            <div>
              <p className="text-text text-[13px] font-semibold font-ui">{d.scenario_name}</p>
              {d.description && (
                <p className="text-muted text-[11px] font-ui mt-0.5">{d.description}</p>
              )}
            </div>
          )}

          {/* Portfolio summary */}
          {(d.current_value != null || d.projected_value != null) && (
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-panel border border-border rounded-lg p-3">
                <p className="text-muted text-[10px] uppercase tracking-wider font-ui">Current</p>
                <p className="text-text text-[14px] font-mono font-semibold mt-1">₹{fmt(d.current_value)}</p>
              </div>
              <div className="bg-panel border border-border rounded-lg p-3">
                <p className="text-muted text-[10px] uppercase tracking-wider font-ui">Projected</p>
                <p className="text-text text-[14px] font-mono font-semibold mt-1">₹{fmt(d.projected_value)}</p>
              </div>
              <div className="bg-panel border border-border rounded-lg p-3">
                <p className="text-muted text-[10px] uppercase tracking-wider font-ui">P&amp;L</p>
                <p className={`text-[14px] font-mono font-semibold mt-1 ${pnlColor(d.projected_pnl)}`}>
                  {Number(d.projected_pnl ?? 0) >= 0 ? '+' : ''}₹{fmt(d.projected_pnl)}
                </p>
                {d.projected_pnl_pct != null && (
                  <p className={`text-[10px] font-mono ${pnlColor(d.projected_pnl_pct)}`}>
                    {Number(d.projected_pnl_pct ?? 0) >= 0 ? '+' : ''}{Number(d.projected_pnl_pct ?? 0).toFixed(2)}%
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Impacts table */}
          {d.impacts?.length > 0 && (
            <div>
              <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Position Impacts</p>
              <table className="w-full text-[11px] font-mono">
                <thead>
                  <tr className="text-muted uppercase tracking-wider border-b border-border">
                    <th className="text-left pb-2">Symbol</th>
                    <th className="text-right pb-2">Current</th>
                    <th className="text-right pb-2">Projected</th>
                    <th className="text-right pb-2">Δ%</th>
                  </tr>
                </thead>
                <tbody>
                  {d.impacts.map((imp, i) => {
                    const chg = Number(imp.change_pct ?? 0)
                    return (
                      <tr key={i} className="border-b border-border/40 last:border-0">
                        <td className="py-1.5 text-text">{imp.symbol ?? '—'}</td>
                        <td className="py-1.5 text-right text-muted">₹{fmt(imp.current_value)}</td>
                        <td className="py-1.5 text-right text-text">₹{fmt(imp.projected_value)}</td>
                        <td className={`py-1.5 text-right font-semibold ${pnlColor(chg)}`}>
                          {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
