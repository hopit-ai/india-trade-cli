export default function FlowsCard({ data }) {
  if (!data) return null

  const fii = Number(data.fii_net_today ?? 0)
  const dii = Number(data.dii_net_today ?? 0)
  const fii5 = Number(data.fii_5d_net ?? 0)
  const dii5 = Number(data.dii_5d_net ?? 0)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-md w-full">

      <div className="flex items-center gap-2 mb-4">
        <span>🌊</span>
        <p className="text-muted text-[11px] uppercase tracking-widest font-ui">FII / DII Flows</p>
      </div>

      {/* Signal badge */}
      {data.signal && <Signal value={data.signal} reason={data.signal_reason} />}

      {/* Flow grid */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        <FlowBox label="FII Today" value={fii} streak={data.fii_streak} />
        <FlowBox label="DII Today" value={dii} streak={data.dii_streak} />
        <FlowBox label="FII 5-Day" value={fii5} />
        <FlowBox label="DII 5-Day" value={dii5} />
      </div>

      {/* Divergence */}
      {data.divergence && (
        <div className="mt-3 pt-3 border-t border-border text-xs font-ui text-muted">
          <span className="text-amber font-semibold">Divergence: </span>
          {data.divergence}
        </div>
      )}
    </div>
  )
}

function FlowBox({ label, value, streak }) {
  const pos = value >= 0
  return (
    <div className="bg-panel rounded-lg p-3 border border-border">
      <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-1">{label}</p>
      <p className={`font-mono text-base font-semibold ${pos ? 'text-green' : 'text-red'}`}>
        {pos ? '+' : ''}₹{Math.abs(value).toFixed(0)} Cr
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
              : 'text-muted border-border'
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-ui ${color}`}>
      <span className="font-semibold">{value}</span>
      {reason && <span className="text-muted text-xs">— {reason}</span>}
    </div>
  )
}
