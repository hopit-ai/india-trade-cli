function fmt(n) { return Number(n ?? 0).toLocaleString('en-IN') }

export default function OICard({ data }) {
  const d      = data?.data ?? data ?? {}
  const symbol = d.symbol ?? '—'
  const spot   = d.spot ?? d.spot_price ?? 0
  const pcr    = d.pcr ?? d.put_call_ratio ?? null
  const maxPain= d.max_pain ?? d.resistance ?? null
  const support= d.support ?? null
  const chain  = d.chain ?? []

  const topStrikes = chain
    .sort((a, b) => (b.ce_oi + b.pe_oi) - (a.ce_oi + a.pe_oi))
    .slice(0, 10)
    .sort((a, b) => a.strike - b.strike)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">OI Profile</p>
          <p className="text-text text-lg font-mono font-semibold mt-0.5">{symbol}</p>
        </div>
        <div className="text-right space-y-1">
          {spot > 0 && <p className="text-text text-sm font-mono">Spot ₹{Number(spot).toLocaleString('en-IN')}</p>}
          {pcr != null && (
            <p className={`text-[12px] font-ui ${pcr > 1.2 ? 'text-green' : pcr < 0.8 ? 'text-red' : 'text-amber'}`}>
              PCR {Number(pcr).toFixed(2)}
            </p>
          )}
        </div>
      </div>

      {/* Key levels */}
      {(maxPain || support) && (
        <div className="grid grid-cols-2 gap-3 border border-border rounded-lg p-3">
          {maxPain && (
            <div>
              <p className="text-muted text-[10px] font-ui uppercase tracking-wider">Max Pain / Resistance</p>
              <p className="text-red text-[13px] font-mono mt-0.5">₹{Number(maxPain).toLocaleString('en-IN')}</p>
            </div>
          )}
          {support && (
            <div>
              <p className="text-muted text-[10px] font-ui uppercase tracking-wider">Support (Max Put OI)</p>
              <p className="text-green text-[13px] font-mono mt-0.5">₹{Number(support).toLocaleString('en-IN')}</p>
            </div>
          )}
        </div>
      )}

      {/* OI table */}
      {topStrikes.length > 0 && (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-muted uppercase tracking-wider border-b border-border">
              <th className="text-right pb-2">CE OI</th>
              <th className="text-center pb-2 text-text">Strike</th>
              <th className="text-left pb-2">PE OI</th>
            </tr>
          </thead>
          <tbody>
            {topStrikes.map((row, i) => {
              const atm = spot > 0 && Math.abs(row.strike - spot) < (topStrikes[1]?.strike - topStrikes[0]?.strike ?? 50) / 2
              return (
                <tr key={i} className={`border-b border-border/40 last:border-0 ${atm ? 'bg-amber/5' : ''}`}>
                  <td className="py-1 text-right text-red">{fmt(row.ce_oi)}</td>
                  <td className={`py-1 text-center font-semibold ${atm ? 'text-amber' : 'text-text'}`}>
                    {Number(row.strike).toLocaleString('en-IN')}
                  </td>
                  <td className="py-1 text-left text-green">{fmt(row.pe_oi)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
