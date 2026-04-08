import { useChatStore } from '../../store/chatStore'

export default function MorningBriefCard({ data }) {
  if (!data) return null
  const { market_snapshot, institutional_flows, top_news, market_breadth } = data
  const setDraft = useChatStore((s) => s.setDraft)

  // Build contextual chips from actual brief data
  const posture    = market_snapshot?.posture ?? null
  const niftyLtp   = market_snapshot?.nifty?.ltp ?? null
  const niftyChg   = market_snapshot?.nifty?.change_pct ?? null
  const vix        = market_snapshot?.vix?.ltp ?? null
  const fiiNet     = institutional_flows?.fii_net_today ?? null
  const fiiStreak  = institutional_flows?.fii_streak ?? null
  const advances   = market_breadth?.advances ?? null
  const declines   = market_breadth?.declines ?? null

  const ctx = [
    posture   && `Market posture: ${posture}`,
    niftyLtp  && `NIFTY at ${Number(niftyLtp).toLocaleString('en-IN')} (${niftyChg != null ? (niftyChg >= 0 ? '+' : '') + Number(niftyChg).toFixed(2) + '%' : ''})`,
    vix       && `VIX at ${Number(vix).toFixed(1)}`,
    fiiNet    && `FII net ${Number(fiiNet) >= 0 ? '+' : ''}₹${Number(fiiNet).toFixed(0)} Cr${fiiStreak != null ? ` (${Math.abs(fiiStreak)}d ${Number(fiiStreak) >= 0 ? 'buying' : 'selling'})` : ''}`,
    advances  && declines && `Breadth: ${advances} advances, ${declines} declines`,
  ].filter(Boolean).join('; ')

  const chips = [
    posture && {
      label: `${posture === 'BULLISH' ? '📈' : posture === 'BEARISH' ? '📉' : '⚡'} ${posture} market — how to trade today?`,
      q: `${ctx}. Given this ${posture.toLowerCase()} market setup, what should I focus on today — key levels to watch, sectors to favour, and positions to avoid?`,
    },
    fiiNet != null && {
      label: `FII ${Number(fiiNet) >= 0 ? 'buying' : 'selling'} ₹${Math.abs(Number(fiiNet)).toFixed(0)} Cr — what does this mean?`,
      q: `${ctx}. What does this FII flow pattern mean for NIFTY tomorrow and which sectors are most impacted?`,
    },
    advances != null && declines != null && {
      label: `${advances} up vs ${declines} down — oversold or more downside?`,
      q: `${ctx}. Is this breadth reading a sign of exhaustion and potential reversal, or does it suggest more downside ahead?`,
    },
    top_news?.length > 0 && {
      label: '📰 What\'s the biggest market risk today?',
      q: `${ctx}. Top news: ${top_news.slice(0, 3).map(n => n.headline ?? n.title ?? '').filter(Boolean).join(' | ')}. What is the single biggest risk to watch today?`,
    },
  ].filter(Boolean)

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

      {/* Contextual action chips */}
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1 border-t border-border">
          {chips.map((chip) => (
            <button
              key={chip.label}
              onClick={() => setDraft(chip.q)}
              className="text-[11px] font-ui px-3 py-1.5 rounded-full border border-border
                         text-muted hover:text-text hover:border-amber/50 hover:bg-amber/5
                         transition-colors cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
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
