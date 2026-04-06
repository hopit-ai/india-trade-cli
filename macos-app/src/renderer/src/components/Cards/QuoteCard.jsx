export default function QuoteCard({ data }) {
  if (!data) return <Card><p className="text-muted text-sm">No quote data.</p></Card>

  const ltp       = data.last_price ?? data.ltp ?? 0
  const change    = data.change ?? data.net_change ?? 0
  const changePct = data.change_pct ?? data.pct_change ?? 0
  const symbol    = data.symbol ?? data.tradingsymbol ?? '—'
  const positive  = change >= 0

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui mb-1">Quote</p>
          <p className="text-text text-xl font-semibold font-mono">{symbol}</p>
          <p className="text-muted text-xs font-ui mt-0.5">{data.exchange ?? 'NSE'}</p>
        </div>
        <div className="text-right">
          <p className="text-text text-2xl font-mono font-semibold">
            ₹{fmt(ltp)}
          </p>
          <p className={`text-sm font-mono mt-1 ${positive ? 'text-green' : 'text-red'}`}>
            {positive ? '+' : ''}{Number(change).toFixed(2)}
            {' '}({positive ? '+' : ''}{Number(changePct).toFixed(2)}%)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-border">
        {[
          ['Open',   `₹${fmt(data.open)}`],
          ['High',   `₹${fmt(data.high)}`],
          ['Low',    `₹${fmt(data.low)}`],
          ['Volume', vol(data.volume)],
        ].map(([label, val]) => (
          <div key={label}>
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
            <p className="text-text text-sm font-mono mt-0.5">{val}</p>
          </div>
        ))}
      </div>
    </Card>
  )
}

const fmt = (n) => Number(n ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const vol = (n) => {
  const v = Number(n ?? 0)
  if (v >= 1e7) return `${(v / 1e7).toFixed(2)}Cr`
  if (v >= 1e5) return `${(v / 1e5).toFixed(2)}L`
  return v.toLocaleString('en-IN')
}

function Card({ children }) {
  return <div className="bg-elevated border border-border rounded-xl p-4 max-w-md w-full">{children}</div>
}
