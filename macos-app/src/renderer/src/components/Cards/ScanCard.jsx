function Section({ title, items, color }) {
  if (!items?.length) return null
  return (
    <div>
      <p className={`text-[10px] uppercase tracking-widest font-ui mb-2 ${color}`}>{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => {
          const symbol = typeof item === 'string' ? item : item.symbol ?? item.tradingsymbol ?? JSON.stringify(item)
          const detail = typeof item === 'object'
            ? (item.iv_rank != null ? `IV ${item.iv_rank}%` : item.oi_change != null ? `OI +${item.oi_change}%` : '')
            : ''
          return (
            <div key={i} className={`border rounded-lg px-2.5 py-1.5 ${color.replace('text-', 'border-').replace('500', '400')}/30 bg-current/5`}>
              <span className={`text-[12px] font-mono font-semibold ${color}`}>{symbol}</span>
              {detail && <span className="text-[10px] font-ui text-muted ml-1.5">{detail}</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ScanCard({ data }) {
  const d       = data?.data ?? data ?? {}
  const summary = d.summary ?? d.scan_summary ?? null

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Options Scan</p>

      {summary && (
        <p className="text-muted text-[12px] font-ui">{summary}</p>
      )}

      <Section title="High IV" items={d.high_iv} color="text-red" />
      <Section title="Unusual OI" items={d.unusual_oi} color="text-amber" />
      <Section title="High Put Writing" items={d.high_put_writing} color="text-green" />
      <Section title="Opportunities" items={d.opportunities ?? d.results} color="text-blue" />

      {!d.high_iv?.length && !d.unusual_oi?.length && !d.high_put_writing?.length && !d.results?.length && (
        <p className="text-muted text-sm font-ui">No scan results. Run: <code className="font-mono text-amber">scan</code></p>
      )}
    </div>
  )
}
