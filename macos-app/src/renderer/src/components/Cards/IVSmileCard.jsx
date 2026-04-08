import { useChatStore } from '../../store/chatStore'

// IV values below this threshold are illiquid/unsolvable — shown as —
const IV_FLOOR = 0.5

export default function IVSmileCard({ data }) {
  const d = data?.data ?? data ?? {}
  const symbol = d.symbol ?? '—'
  const expiry = d.expiry ?? ''
  const rows = (d.rows ?? []).slice().sort((a, b) => a.strike - b.strike)
  const setDraft = useChatStore((s) => s.setDraft)

  function ivValid(v) { return Number(v ?? 0) >= IV_FLOOR }

  function ivColor(iv) {
    const v = Number(iv ?? 0)
    if (v > 50) return 'text-red'
    if (v > 30) return 'text-amber'
    return 'text-text'
  }

  function fmtIV(v) {
    if (!ivValid(v)) return '—'
    return Number(v).toFixed(1) + '%'
  }

  // Find ATM: row with moneyness closest to 0
  let atmIdx = -1
  if (rows.length > 0) {
    let minAbs = Infinity
    rows.forEach((r, i) => {
      const m = Math.abs(Number(r.moneyness ?? 0))
      if (m < minAbs) { minAbs = m; atmIdx = i }
    })
  }

  // Build contextual chips from actual data
  const atmRow   = atmIdx >= 0 ? rows[atmIdx] : null
  const atmPeIv  = atmRow ? Number(atmRow.pe_iv ?? 0) : 0
  const atmStrike = atmRow ? Number(atmRow.strike) : 0

  // Max PE skew: lowest valid strike below ATM
  const belowAtm = rows.filter((_, i) => i < atmIdx && ivValid(Number(_.pe_iv ?? 0)))
  const maxSkewRow = belowAtm.length > 0
    ? belowAtm.reduce((m, r) => Number(r.pe_iv) > Number(m.pe_iv) ? r : m)
    : null

  // Max CE IV: highest valid strike above ATM
  const aboveAtm = rows.filter((_, i) => i > atmIdx && ivValid(Number(_.ce_iv ?? 0)))
  const maxCeRow = aboveAtm.length > 0
    ? aboveAtm.reduce((m, r) => Number(r.ce_iv) > Number(m.ce_iv) ? r : m)
    : null

  const ctx = [
    `${symbol} IV Smile`,
    atmStrike ? `ATM ${atmStrike.toLocaleString('en-IN')} PE IV=${atmPeIv.toFixed(1)}%` : '',
    maxSkewRow ? `max put skew at ${Number(maxSkewRow.strike).toLocaleString('en-IN')} = ${Number(maxSkewRow.pe_iv).toFixed(1)}%` : '',
    maxCeRow   ? `max CE IV at ${Number(maxCeRow.strike).toLocaleString('en-IN')} = ${Number(maxCeRow.ce_iv).toFixed(1)}%` : '',
  ].filter(Boolean).join(', ')

  const chips = [
    maxSkewRow && {
      label: `Put skew +${Number(maxSkewRow.pe_iv).toFixed(0)}% at ${Number(maxSkewRow.strike).toLocaleString('en-IN')} — why?`,
      q: `${ctx}. Why is put IV so elevated vs call IV, and what does this skew structure tell me about market positioning for ${symbol}?`,
    },
    atmPeIv > 0 && {
      label: `ATM IV ${atmPeIv.toFixed(1)}% — buy or sell options?`,
      q: `${ctx}. ATM IV is ${atmPeIv.toFixed(1)}%. Is this a good time to buy or sell ${symbol} options, and what strategies suit this IV level?`,
    },
    {
      label: 'How to trade this skew?',
      q: `${ctx}. What options strategies make the most sense given this skew structure — spreads, straddles, or directional plays?`,
    },
  ].filter(Boolean)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">IV Smile</p>
          <p className="text-text text-lg font-mono font-semibold mt-0.5">{symbol}</p>
        </div>
        {expiry && (
          <span className="text-muted text-[11px] font-ui border border-border px-2 py-0.5 rounded">
            {expiry}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="text-muted text-[12px] font-ui text-center py-4">No data available</p>
      ) : (
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="text-muted uppercase tracking-wider border-b border-border">
              <th className="text-right pb-2 pr-3">Strike</th>
              <th className="text-right pb-2 pr-3">CE IV%</th>
              <th className="text-right pb-2 pr-3">PE IV%</th>
              <th className="text-right pb-2">Skew (PE−CE)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const ceIv = Number(row.ce_iv ?? 0)
              const peIv = Number(row.pe_iv ?? 0)
              const ceOk = ivValid(ceIv)
              const peOk = ivValid(peIv)
              const skew = ceOk && peOk ? peIv - ceIv : null
              const isAtm = i === atmIdx
              return (
                <tr
                  key={i}
                  className={`border-b border-border/40 last:border-0 ${isAtm ? 'bg-amber/5' : ''}`}
                >
                  <td className={`py-1.5 text-right pr-3 font-semibold ${isAtm ? 'text-amber' : 'text-text'}`}>
                    {Number(row.strike).toLocaleString('en-IN')}
                    {isAtm && <span className="text-amber text-[9px] ml-1">ATM</span>}
                  </td>
                  <td className={`py-1.5 text-right pr-3 ${ceOk ? ivColor(ceIv) : 'text-muted'}`}>
                    {fmtIV(ceIv)}
                  </td>
                  <td className={`py-1.5 text-right pr-3 ${peOk ? ivColor(peIv) : 'text-muted'}`}>
                    {fmtIV(peIv)}
                  </td>
                  <td className={`py-1.5 text-right ${skew == null ? 'text-muted' : skew > 0 ? 'text-green' : skew < 0 ? 'text-red' : 'text-muted'}`}>
                    {skew == null ? '—' : `${skew >= 0 ? '+' : ''}${skew.toFixed(1)}%`}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {/* Action chips */}
      <div className="flex flex-wrap gap-2 pt-1">
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
    </div>
  )
}
