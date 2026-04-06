import { useState } from 'react'

export default function AnalysisCard({ data }) {
  const [showPlans, setShowPlans] = useState(false)
  if (!data) return null

  const { symbol, exchange, report, trade_plans } = data
  // Filter out null/empty plans
  const plans = trade_plans
    ? Object.entries(trade_plans).filter(([, v]) => v != null)
    : []

  return (
    <div className="bg-elevated border border-blue/30 rounded-xl p-4 max-w-2xl w-full space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-muted text-[11px] uppercase tracking-widest font-ui">Analysis</p>
          <p className="text-text text-lg font-semibold font-mono mt-0.5">
            {symbol} <span className="text-muted text-sm font-ui">{exchange}</span>
          </p>
        </div>
        <span className="text-blue text-xl">🔬</span>
      </div>

      {/* Report */}
      {report && (
        <div className="border-t border-border pt-3">
          <p className="text-text text-sm font-ui leading-relaxed whitespace-pre-wrap">
            {report}
          </p>
        </div>
      )}

      {/* Trade plans toggle */}
      {plans.length > 0 && (
        <div className="border-t border-border pt-3">
          <button
            onClick={() => setShowPlans(v => !v)}
            className="text-amber text-xs font-ui hover:opacity-80 transition-opacity"
          >
            {showPlans ? '▾ Hide' : '▸ Show'} trade plans ({plans.length})
          </button>
          {showPlans && (
            <div className="mt-3 space-y-3">
              {plans.map(([name, plan]) => (
                <div key={name} className="bg-panel rounded-lg p-3 border border-border">
                  <p className="text-amber text-xs font-ui uppercase tracking-wider mb-2">{name}</p>
                  <pre className="text-text text-xs font-mono whitespace-pre-wrap leading-relaxed">
                    {typeof plan === 'string' ? plan : JSON.stringify(plan, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
