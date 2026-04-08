function fmt(n) {
  return Number(n ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function FundsCard({ data }) {
  const d = data?.data ?? data ?? {}
  const demo = d.demo ?? false

  const rows = [
    { label: 'Available Cash',   value: d.available_cash   ?? d.equity?.net ?? 0, color: 'text-green' },
    { label: 'Used Margin',      value: d.used_margin      ?? d.equity?.utilised?.debits ?? 0, color: 'text-red' },
    { label: 'Total Balance',    value: d.total_balance    ?? d.equity?.available?.live_balance ?? 0, color: 'text-text' },
  ]

  const total = rows[2].value
  const used  = rows[1].value
  const usedPct = total > 0 ? Math.min((used / total) * 100, 100) : 0

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-sm w-full space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Account Funds</p>
        {demo && <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>}
      </div>

      {rows.map(({ label, value, color }) => (
        <div key={label} className="flex items-center justify-between">
          <span className="text-muted text-[12px] font-ui">{label}</span>
          <span className={`text-[13px] font-mono font-semibold ${color}`}>₹{fmt(value)}</span>
        </div>
      ))}

      {/* Margin usage bar */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-muted text-[10px] font-ui">Margin used</span>
          <span className="text-muted text-[10px] font-mono">{usedPct.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-panel rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all ${usedPct > 80 ? 'bg-red' : usedPct > 50 ? 'bg-amber' : 'bg-green'}`}
            style={{ width: `${usedPct}%` }}
          />
        </div>
      </div>
    </div>
  )
}
