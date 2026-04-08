export default function HoldingsCard({ data }) {
  const holdings = Array.isArray(data) ? data : data?.holdings ?? []

  if (!holdings.length) {
    return (
      <Card title="Holdings">
        <p className="text-muted text-sm font-ui">No holdings found.</p>
      </Card>
    )
  }

  // Totals
  const totalInvested = holdings.reduce((s, h) => s + (h.avg_price ?? 0) * (h.quantity ?? 0), 0)
  const totalCurrent  = holdings.reduce((s, h) => s + (h.last_price ?? h.ltp ?? 0) * (h.quantity ?? 0), 0)
  const totalPnl      = holdings.reduce((s, h) => s + Number(h.pnl ?? h.unrealised_pnl ?? 0), 0)
  const totalDayChg   = holdings.reduce((s, h) => s + Number(h.day_change ?? 0) * (h.quantity ?? 1), 0)
  const overallPct    = totalInvested > 0 ? (totalPnl / totalInvested * 100) : 0
  const dayPct        = totalCurrent > 0 ? (totalDayChg / (totalCurrent - totalDayChg) * 100) : 0

  return (
    <Card title="Holdings">
      {/* Summary row */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <SummaryBox
          label="Invested"
          value={`₹${totalInvested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
        />
        <SummaryBox
          label="Overall P&L"
          value={`${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          sub={`${overallPct >= 0 ? '+' : ''}${overallPct.toFixed(2)}%`}
          positive={totalPnl >= 0}
        />
        <SummaryBox
          label="Today's P&L"
          value={`${totalDayChg >= 0 ? '+' : ''}₹${totalDayChg.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          sub={`${dayPct >= 0 ? '+' : ''}${dayPct.toFixed(2)}%`}
          positive={totalDayChg >= 0}
        />
      </div>

      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="text-muted text-[10px] uppercase tracking-wider border-b border-border">
            <th className="text-left pb-2">Symbol</th>
            <th className="text-right pb-2">Qty</th>
            <th className="text-right pb-2">Avg</th>
            <th className="text-right pb-2">LTP</th>
            <th className="text-right pb-2">P&amp;L</th>
            <th className="text-right pb-2">Today</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => {
            const pnl = Number(h.pnl ?? h.unrealised_pnl ?? 0)
            const pnlPct = Number(h.pnl_pct ?? 0)
            const dayChg = Number(h.day_change ?? 0)
            const dayChgPct = Number(h.day_change_pct ?? 0)
            return (
              <tr key={i} className="border-b border-border/50 last:border-0">
                <td className="py-2 text-text font-semibold">{h.symbol ?? h.tradingsymbol}</td>
                <td className="py-2 text-right text-text">{h.quantity ?? h.qty}</td>
                <td className="py-2 text-right text-muted">
                  ₹{Number(h.avg_price ?? h.average_price ?? 0).toFixed(2)}
                </td>
                <td className="py-2 text-right text-text">
                  ₹{Number(h.ltp ?? h.last_price ?? 0).toFixed(2)}
                </td>
                <td className={`py-2 text-right ${pnl >= 0 ? 'text-green' : 'text-red'}`}>
                  <div>{pnl >= 0 ? '+' : ''}₹{Number(pnl).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px]">{pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%</div>
                </td>
                <td className={`py-2 text-right ${dayChg >= 0 ? 'text-green' : 'text-red'}`}>
                  <div>{dayChg >= 0 ? '+' : ''}₹{Number(dayChg).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                  <div className="text-[10px]">{dayChgPct >= 0 ? '+' : ''}{dayChgPct.toFixed(2)}%</div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Card>
  )
}

function SummaryBox({ label, value, sub, positive }) {
  return (
    <div className="bg-panel rounded-lg p-2.5 border border-border">
      <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
      <p className={`text-sm font-mono font-semibold mt-0.5 ${positive != null ? (positive ? 'text-green' : 'text-red') : 'text-text'}`}>
        {value}
      </p>
      {sub && (
        <p className={`text-[10px] font-mono mt-0.5 ${positive != null ? (positive ? 'text-green' : 'text-red') : 'text-muted'}`}>
          {sub}
        </p>
      )}
    </div>
  )
}

function Card({ title, children }) {
  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
      <p className="text-muted text-[11px] uppercase tracking-widest font-ui mb-3">{title}</p>
      {children}
    </div>
  )
}
