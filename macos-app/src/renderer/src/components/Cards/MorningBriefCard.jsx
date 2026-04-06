export default function MorningBriefCard({ data }) {
  if (!data) return null
  const { market_snapshot, institutional_flows, top_news, market_breadth } = data

  return (
    <div className="bg-elevated border border-amber/30 rounded-xl p-4 max-w-2xl w-full space-y-4">

      <div className="flex items-center gap-2">
        <span className="text-lg">☀️</span>
        <p className="text-amber text-[11px] uppercase tracking-widest font-ui">Morning Brief</p>
      </div>

      {/* Market snapshot — IndexSnapshot objects */}
      {market_snapshot && (
        <Section title="Markets">
          {/* Posture badge */}
          {market_snapshot.posture && (
            <div className="mb-3">
              <Signal value={market_snapshot.posture} />
              {market_snapshot.posture_reason && (
                <p className="text-muted text-xs font-ui mt-1">{market_snapshot.posture_reason}</p>
              )}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {['nifty', 'banknifty', 'sensex', 'vix'].map(key => {
              const idx = market_snapshot[key]
              if (!idx || typeof idx !== 'object') return null
              const pos = (idx.change_pct ?? 0) >= 0
              return (
                <div key={key} className="bg-panel rounded-lg p-2.5 border border-border">
                  <p className="text-muted text-[10px] uppercase tracking-wider font-ui">{key}</p>
                  <p className="text-text text-sm font-mono font-semibold mt-0.5">
                    {Number(idx.ltp ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </p>
                  <p className={`text-xs font-mono ${pos ? 'text-green' : 'text-red'}`}>
                    {pos ? '+' : ''}{Number(idx.change_pct ?? 0).toFixed(2)}%
                  </p>
                </div>
              )
            })}
          </div>
        </Section>
      )}

      {/* FII / DII flows */}
      {institutional_flows && (
        <Section title="FII / DII">
          <div className="grid grid-cols-2 gap-3">
            <FlowStat label="FII Today" value={institutional_flows.fii_net_today} streak={institutional_flows.fii_streak} />
            <FlowStat label="DII Today" value={institutional_flows.dii_net_today} streak={institutional_flows.dii_streak} />
          </div>
          {institutional_flows.signal && (
            <div className="mt-2">
              <Signal value={institutional_flows.signal} reason={institutional_flows.signal_reason} />
            </div>
          )}
        </Section>
      )}

      {/* Top news */}
      {top_news?.length > 0 && (
        <Section title="Top News">
          <ul className="space-y-2">
            {top_news.slice(0, 5).map((n, i) => (
              <li key={i} className="flex gap-2 text-xs font-ui text-text leading-snug">
                <span className="text-muted flex-shrink-0">•</span>
                <span>{n.headline ?? n.title ?? String(n)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Market breadth */}
      {market_breadth && (
        <Section title="Breadth">
          <div className="flex gap-4 text-xs font-mono">
            <span className="text-green">▲ {market_breadth.advances ?? '—'}</span>
            <span className="text-red">▼ {market_breadth.declines ?? '—'}</span>
            <span className="text-muted">— {market_breadth.unchanged ?? '—'}</span>
          </div>
        </Section>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="border-t border-border pt-3">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">{title}</p>
      {children}
    </div>
  )
}

function FlowStat({ label, value, streak }) {
  const v = Number(value ?? 0)
  const pos = v >= 0
  return (
    <div className="bg-panel rounded-lg p-2.5 border border-border">
      <p className="text-muted text-[10px] font-ui">{label}</p>
      <p className={`font-mono text-sm font-semibold mt-0.5 ${pos ? 'text-green' : 'text-red'}`}>
        {pos ? '+' : ''}₹{Math.abs(v).toFixed(0)} Cr
      </p>
      {streak !== undefined && (
        <p className="text-muted text-[10px] font-ui mt-0.5">
          {Math.abs(streak)}d {streak >= 0 ? 'buying' : 'selling'}
        </p>
      )}
    </div>
  )
}

function Signal({ value, reason }) {
  const color = value === 'BULLISH' ? 'text-green border-green/30 bg-green/5'
              : value === 'BEARISH' ? 'text-red border-red/30 bg-red/5'
              : value === 'VOLATILE' ? 'text-amber border-amber/30 bg-amber/5'
              : 'text-muted border-border'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-ui ${color}`}>
      <span className="font-semibold">{value}</span>
      {reason && <span className="text-muted">— {reason}</span>}
    </span>
  )
}
