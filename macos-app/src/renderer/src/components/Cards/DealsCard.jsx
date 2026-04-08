const ENTITY_COLOR = {
  FII:      'text-blue',
  MF:       'text-amber',
  DII:      'text-purple-400',
  PROMOTER: 'text-green',
  OTHER:    'text-muted',
}

function fmt(n) {
  return Number(n ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

export default function DealsCard({ data }) {
  const raw   = data?.data ?? data ?? []
  const deals = Array.isArray(raw) ? raw : raw.deals ?? []

  if (!deals.length) {
    return (
      <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">Bulk / Block Deals</p>
        <p className="text-muted text-sm font-ui">No deals found.</p>
      </div>
    )
  }

  // Group by date
  const byDate = deals.reduce((acc, d) => {
    const key = d.date ?? 'Today'
    ;(acc[key] = acc[key] ?? []).push(d)
    return acc
  }, {})

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui">
        Bulk / Block Deals <span className="text-subtle">({deals.length})</span>
      </p>

      {Object.entries(byDate).map(([date, group]) => (
        <div key={date}>
          <p className="text-subtle text-[10px] font-ui mb-2">{date}</p>
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-muted text-[10px] uppercase tracking-wider border-b border-border">
                <th className="text-left pb-2">Symbol</th>
                <th className="text-left pb-2">Client</th>
                <th className="text-left pb-2">Entity</th>
                <th className="text-center pb-2">Type</th>
                <th className="text-right pb-2">Qty</th>
                <th className="text-right pb-2">Price</th>
                <th className="text-right pb-2">Class</th>
              </tr>
            </thead>
            <tbody>
              {group.map((d, i) => {
                const isBuy = d.deal_type?.toUpperCase() === 'BUY'
                const entityCls = ENTITY_COLOR[d.entity_type] ?? ENTITY_COLOR.OTHER
                return (
                  <tr key={i} className="border-b border-border/40 last:border-0">
                    <td className="py-1.5 text-text font-semibold">{d.symbol ?? '—'}</td>
                    <td className="py-1.5 text-muted max-w-[120px] truncate" title={d.client}>
                      {d.client ?? '—'}
                    </td>
                    <td className={`py-1.5 ${entityCls} text-[10px]`}>
                      {d.entity_type ?? '—'}
                    </td>
                    <td className={`py-1.5 text-center font-semibold text-[10px] ${isBuy ? 'text-green' : 'text-red'}`}>
                      {d.deal_type ?? '—'}
                    </td>
                    <td className="py-1.5 text-right text-text">{fmt(d.quantity)}</td>
                    <td className="py-1.5 text-right text-text">₹{fmt(d.price)}</td>
                    <td className="py-1.5 text-right text-subtle text-[10px]">
                      {d.deal_class ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
