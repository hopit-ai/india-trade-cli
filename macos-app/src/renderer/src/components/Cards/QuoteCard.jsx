export default function QuoteCard({ data }) {
  if (!data) return <ErrorFallback />
  const change    = data.change ?? data.net_change ?? 0
  const changePct = data.change_pct ?? data.pct_change ?? 0
  const positive  = change >= 0

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui mb-1">Quote</p>
          <p className="text-text text-xl font-semibold font-mono">{data.symbol}</p>
        </div>
        <div className="text-right">
          <p className="text-text text-2xl font-mono">
            ₹{Number(data.ltp ?? data.last_price ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </p>
          <p className={`text-sm font-mono ${positive ? 'text-green' : 'text-red'}`}>
            {positive ? '+' : ''}{Number(change).toFixed(2)}{' '}
            ({positive ? '+' : ''}{Number(changePct).toFixed(2)}%)
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 mt-4 pt-4 border-t border-border">
        {[
          ['Open',   data.open],
          ['High',   data.high],
          ['Low',    data.low],
          ['Volume', data.volume],
        ].map(([label, val]) => (
          <div key={label}>
            <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{label}</p>
            <p className="text-text text-sm font-mono mt-0.5">
              {label === 'Volume'
                ? Number(val ?? 0).toLocaleString('en-IN')
                : `₹${Number(val ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
            </p>
          </div>
        ))}
      </div>
    </Card>
  )
}

function ErrorFallback() {
  return <Card><p className="text-muted text-sm font-ui">No quote data available.</p></Card>
}

function Card({ children }) {
  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-lg">
      {children}
    </div>
  )
}
