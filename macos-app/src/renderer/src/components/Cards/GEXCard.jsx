import { useChatStore } from '../../store/chatStore'

export default function GEXCard({ data }) {
  const setDraft = useChatStore((s) => s.setDraft)
  const d = data?.data ?? data ?? {}

  if (d.error) {
    return (
      <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-2">Gamma Exposure</p>
        <p className="text-red text-[12px] font-ui">{d.error}</p>
      </div>
    )
  }

  const regime = (d.regime ?? 'NEUTRAL').toUpperCase()
  const totalGex = Number(d.total_net_gex ?? 0)
  const flipPoint = d.flip_point ?? null

  const regimeColor = regime === 'POSITIVE' ? 'text-green border-green/30'
    : regime === 'NEGATIVE' ? 'text-red border-red/30'
    : 'text-amber border-amber/30'

  const regimeMsg = regime === 'POSITIVE'
    ? 'Dealers long gamma — market may pin/revert'
    : regime === 'NEGATIVE'
    ? 'Dealers short gamma — expect breakout/amplified moves'
    : 'Balanced gamma exposure'

  const strikes = (d.strikes ?? [])
    .slice()
    .sort((a, b) => Math.abs(Number(b.net_gex ?? 0)) - Math.abs(Number(a.net_gex ?? 0)))
    .slice(0, 10)
    .sort((a, b) => Number(a.strike) - Number(b.strike))

  function fmtCr(v) {
    const n = Number(v ?? 0)
    return (n / 1e7).toFixed(2) + 'cr'
  }

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Gamma Exposure</p>
        <div className="flex items-center gap-2">
          <span className={`text-[11px] font-ui border px-2 py-0.5 rounded font-semibold ${regimeColor}`}>
            {regime}
          </span>
          <span className="text-text text-[12px] font-mono">
            GEX: {fmtCr(totalGex)}
          </span>
        </div>
      </div>

      {/* Flip point */}
      {flipPoint != null && (
        <div className="border border-border rounded-lg px-3 py-2">
          <span className="text-muted text-[10px] font-ui uppercase tracking-wider">GEX Flip Point: </span>
          <span className="text-blue text-[13px] font-mono font-semibold">
            ₹{Number(flipPoint).toLocaleString('en-IN')}
          </span>
        </div>
      )}

      {/* Regime explanation */}
      <p className="text-muted text-[11px] font-ui italic">{regimeMsg}</p>

      {/* Action chips — contextual based on regime and flip point */}
      {(() => {
        const flipFmt = flipPoint != null ? `₹${Number(flipPoint).toLocaleString('en-IN')}` : null
        const gexFmt  = `${(Math.abs(totalGex) / 1e7).toFixed(0)} Cr ${totalGex < 0 ? 'short' : 'long'} gamma`
        const ctx     = `NIFTY GEX: ${regime} regime, flip point ${flipFmt ?? 'unknown'}, total ${gexFmt}`

        const chips = [
          flipFmt && {
            label: `Flip at ${flipFmt} — what happens there?`,
            q: `${ctx}. What happens when NIFTY approaches the GEX flip point at ${flipFmt}, and should I position for a breakout or reversal?`,
          },
          {
            label: regime === 'NEGATIVE'
              ? 'Moves amplified — how to trade it?'
              : regime === 'POSITIVE'
              ? 'Market pinning — how to trade it?'
              : 'Balanced GEX — what does this mean?',
            q: `${ctx}. How should I trade a ${regime.toLowerCase()} gamma regime — which strategies benefit and which to avoid?`,
          },
          {
            label: `${gexFmt} — how bearish/bullish is this?`,
            q: `${ctx}. How significant is ${gexFmt} and what does it imply for near-term ${regime === 'NEGATIVE' ? 'downside risk' : 'market stability'}?`,
          },
        ].filter(Boolean)

        return (
          <div className="flex flex-wrap gap-2">
            {chips.map((chip) => (
              <button
                key={chip.label}
                onClick={() => setDraft(chip.q)}
                className="text-[11px] font-ui px-3 py-1.5 rounded-full border border-border
                           text-muted hover:text-text hover:border-blue/50 hover:bg-blue/5
                           transition-colors cursor-pointer"
              >
                {chip.label}
              </button>
            ))}
          </div>
        )
      })()}

      {/* Strikes table */}
      {strikes.length > 0 && (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-muted uppercase tracking-wider border-b border-border">
              <th className="text-right pb-2 pr-3">Strike</th>
              <th className="text-right pb-2 pr-3">CE GEX</th>
              <th className="text-right pb-2 pr-3">PE GEX</th>
              <th className="text-right pb-2">Net</th>
            </tr>
          </thead>
          <tbody>
            {strikes.map((row, i) => {
              const net = Number(row.net_gex ?? 0)
              return (
                <tr key={i} className="border-b border-border/40 last:border-0">
                  <td className="py-1.5 text-right pr-3 text-text font-semibold">
                    {Number(row.strike).toLocaleString('en-IN')}
                  </td>
                  <td className="py-1.5 text-right pr-3 text-muted">{fmtCr(row.ce_gex)}</td>
                  <td className="py-1.5 text-right pr-3 text-muted">{fmtCr(row.pe_gex)}</td>
                  <td className={`py-1.5 text-right font-semibold ${net > 0 ? 'text-green' : net < 0 ? 'text-red' : 'text-muted'}`}>
                    {net >= 0 ? '+' : ''}{fmtCr(net)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
