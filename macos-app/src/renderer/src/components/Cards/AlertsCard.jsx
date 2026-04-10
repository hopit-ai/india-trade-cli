import { useState } from 'react'
import { useChatStore, getBaseUrl } from '../../store/chatStore'

export default function AlertsCard({ data }) {
  const port    = useChatStore((s) => s.port)
  const d       = data?.data ?? data ?? {}
  const [alerts, setAlerts] = useState(d.alerts ?? d.active_alerts ?? (Array.isArray(data) ? data : []))
  const [removing, setRemoving] = useState(null)

  async function remove(alertId) {
    setRemoving(alertId)
    try {
      await fetch(`${getBaseUrl(port)}/skills/alerts/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alertId }),
      })
      setAlerts(prev => prev.filter(a => (a.id ?? a.alert_id) !== alertId))
    } catch (_) {}
    setRemoving(null)
  }

  if (!alerts.length) {
    return (
      <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-3">Alerts</p>
        <p className="text-muted text-sm font-ui">No active alerts. Use <code className="font-mono text-amber">alert SYMBOL above/below PRICE</code> to add one.</p>
      </div>
    )
  }

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui mb-3">
        Alerts <span className="text-subtle">({alerts.length})</span>
      </p>
      <div className="space-y-2">
        {alerts.map((a) => {
          const id        = a.id ?? a.alert_id ?? String(Math.random())
          const symbol    = a.symbol ?? '—'
          const condition = a.condition ?? a.description ?? '—'
          const threshold = a.threshold != null ? `₹${Number(a.threshold).toLocaleString('en-IN')}` : ''
          const triggered = a.triggered ?? false

          return (
            <div key={id} className={`flex items-center justify-between rounded-lg border px-3 py-2
              ${triggered ? 'border-green/40 bg-green/5' : 'border-border bg-panel'}`}>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-text text-[12px] font-mono font-semibold">{symbol}</span>
                  <span className={`text-[10px] font-ui ${triggered ? 'text-green' : 'text-muted'}`}>
                    {triggered ? '✓ triggered' : '● active'}
                  </span>
                </div>
                <p className="text-muted text-[11px] font-ui mt-0.5 truncate">
                  {condition} {threshold}
                </p>
              </div>
              <button
                onClick={() => remove(id)}
                disabled={removing === id}
                className="ml-3 text-subtle hover:text-red text-[11px] font-ui transition-colors
                           disabled:opacity-40 flex-shrink-0"
              >
                {removing === id ? '…' : '✕'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
