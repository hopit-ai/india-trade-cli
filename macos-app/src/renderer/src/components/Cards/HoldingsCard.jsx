export default function HoldingsCard({ data }) {
  const holdings = Array.isArray(data) ? data : data?.holdings ?? []

  if (!holdings.length) {
    return (
      <Card title="Holdings">
        <p className="text-muted text-sm font-ui">No holdings found.</p>
      </Card>
    )
  }

  return (
    <Card title="Holdings">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="text-muted text-[10px] uppercase tracking-wider border-b border-border">
            <th className="text-left pb-2">Symbol</th>
            <th className="text-right pb-2">Qty</th>
            <th className="text-right pb-2">Avg</th>
            <th className="text-right pb-2">LTP</th>
            <th className="text-right pb-2">P&amp;L</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => {
            const pnl = h.pnl ?? h.unrealised_pnl ?? 0
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
                  {pnl >= 0 ? '+' : ''}₹{Number(pnl).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Card>
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
