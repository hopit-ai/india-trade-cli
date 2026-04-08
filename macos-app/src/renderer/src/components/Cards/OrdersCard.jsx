const STATUS_COLOR = {
  COMPLETE:  'text-green',
  REJECTED:  'text-red',
  CANCELLED: 'text-muted',
  PENDING:   'text-amber',
  OPEN:      'text-blue',
  TRIGGER_PENDING: 'text-amber',
}

export default function OrdersCard({ data }) {
  const d      = data?.data ?? data ?? {}
  const orders = d.orders ?? (Array.isArray(data) ? data : [])
  const demo   = d.demo ?? false

  if (!orders.length) {
    return (
      <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-3">Today's Orders</p>
        <p className="text-muted text-sm font-ui">{demo ? 'No orders (demo mode — connect a broker)' : 'No orders today.'}</p>
      </div>
    )
  }

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
      <div className="flex items-center justify-between mb-3">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Today's Orders</p>
        {demo && <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>}
      </div>
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="text-muted text-[10px] uppercase tracking-wider border-b border-border">
            <th className="text-left pb-2">Symbol</th>
            <th className="text-left pb-2">Type</th>
            <th className="text-right pb-2">Qty</th>
            <th className="text-right pb-2">Price</th>
            <th className="text-right pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o, i) => {
            const status = (o.status ?? o.order_status ?? 'UNKNOWN').toUpperCase()
            const isBuy  = (o.transaction_type ?? o.side ?? '').toUpperCase() === 'BUY'
            return (
              <tr key={i} className="border-b border-border/50 last:border-0">
                <td className="py-2 text-text font-semibold">{o.symbol ?? o.tradingsymbol ?? '—'}</td>
                <td className={`py-2 text-[11px] ${isBuy ? 'text-green' : 'text-red'}`}>
                  {(o.transaction_type ?? o.side ?? '—').toUpperCase()}
                  {' '}
                  <span className="text-muted">{o.order_type ?? o.type ?? ''}</span>
                </td>
                <td className="py-2 text-right text-text">{o.quantity ?? o.qty ?? '—'}</td>
                <td className="py-2 text-right text-text">
                  ₹{Number(o.price ?? o.average_price ?? 0).toFixed(2)}
                </td>
                <td className={`py-2 text-right text-[11px] ${STATUS_COLOR[status] ?? 'text-muted'}`}>
                  {status}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
