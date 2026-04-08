function deltaColor(v) {
  const n = Number(v ?? 0)
  if (Math.abs(n) < 0.01) return 'text-muted'
  return n > 0 ? 'text-green' : 'text-red'
}

export default function DeltaHedgeCard({ data }) {
  const d = data?.data ?? data ?? {}
  const demo = d.demo ?? false
  const suggestions = d.suggestions ?? []

  const currentDelta = Number(d.current_delta ?? 0)
  const targetDelta = Number(d.target_delta ?? 0)
  const gap = Number(d.gap ?? 0)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Delta Hedge</p>
        {demo && (
          <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>
        )}
      </div>

      {/* Demo warning */}
      {demo && d.message && (
        <div className="border border-amber/30 bg-amber/5 rounded-lg px-3 py-2">
          <p className="text-amber text-[11px] font-ui">⚠ {d.message}</p>
        </div>
      )}

      {/* Delta metrics */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Current Δ', value: currentDelta },
          { label: 'Target Δ', value: targetDelta },
          { label: 'Gap', value: gap },
        ].map(({ label, value }) => (
          <div key={label} className="bg-panel border border-border rounded-lg p-3">
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
            <p className={`text-[15px] font-mono font-semibold mt-1 ${deltaColor(value)}`}>
              {value >= 0 ? '+' : ''}{value.toFixed(2)}
            </p>
          </div>
        ))}
      </div>

      {/* Suggestions table */}
      {suggestions.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Hedge Suggestions</p>
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-muted uppercase tracking-wider border-b border-border">
                <th className="text-left pb-2">Action</th>
                <th className="text-left pb-2">Instrument</th>
                <th className="text-right pb-2">Lots</th>
                <th className="text-right pb-2">Δ Change</th>
              </tr>
            </thead>
            <tbody>
              {suggestions.map((s, i) => {
                const action = (s.action ?? '').toUpperCase()
                const isBuy = action === 'BUY'
                return (
                  <tr key={i} className="border-b border-border/40 last:border-0">
                    <td className={`py-1.5 font-semibold ${isBuy ? 'text-green' : 'text-red'}`}>
                      {action}
                    </td>
                    <td className="py-1.5 text-text">{s.instrument ?? '—'}</td>
                    <td className="py-1.5 text-right text-text">{s.lots ?? '—'}</td>
                    <td className={`py-1.5 text-right ${deltaColor(s.delta_change)}`}>
                      {Number(s.delta_change ?? 0) >= 0 ? '+' : ''}{Number(s.delta_change ?? 0).toFixed(2)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Cost estimate */}
      {d.cost_estimate != null && (
        <div className="border-t border-border pt-2 flex items-center justify-between">
          <p className="text-muted text-[11px] font-ui">Estimated Cost</p>
          <p className="text-text text-[12px] font-mono font-semibold">
            ₹{Number(d.cost_estimate).toLocaleString('en-IN')}
          </p>
        </div>
      )}
    </div>
  )
}
