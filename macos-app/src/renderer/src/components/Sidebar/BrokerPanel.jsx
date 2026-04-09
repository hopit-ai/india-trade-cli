import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'

const BROKERS = [
  {
    key:      'fyers',
    name:     'Fyers',
    color:    'text-[#fed7aa]',
    loginPath: '/fyers/login',
    portalUrl: 'https://myapi.fyers.in',
    portalLabel: 'myapi.fyers.in',
    redirectUrl: 'http://127.0.0.1:8765/fyers/callback',
    keys: [
      { env: 'FYERS_APP_ID', label: 'App ID', placeholder: 'XXXX-100', secret: false },
      { env: 'FYERS_SECRET_KEY', label: 'Secret Key', placeholder: 'Secret key', secret: true },
    ],
  },
  {
    key:      'zerodha',
    name:     'Zerodha',
    color:    'text-[#387ed1]',
    loginPath: '/zerodha/login',
    portalUrl: 'https://developers.kite.trade',
    portalLabel: 'developers.kite.trade',
    redirectUrl: 'http://localhost:8765/zerodha/callback',
    keys: [
      { env: 'KITE_API_KEY', label: 'API Key', placeholder: 'API key', secret: false },
      { env: 'KITE_API_SECRET', label: 'API Secret', placeholder: 'API secret', secret: true },
    ],
  },
  {
    key:      'angel_one',
    name:     'Angel One',
    color:    'text-[#f6882a]',
    loginPath: '/angelone/login',
    keys: [],
  },
  {
    key:      'upstox',
    name:     'Upstox',
    color:    'text-[#c4b5fd]',
    loginPath: '/upstox/login',
    keys: [],
  },
  {
    key:      'groww',
    name:     'Groww',
    color:    'text-[#00c48c]',
    loginPath: '/groww/login',
    keys: [],
  },
]

export default function BrokerPanel({ onClose }) {
  const port              = useChatStore((s) => s.port)
  const brokerStatuses    = useChatStore((s) => s.brokerStatuses)
  const setBrokerStatuses = useChatStore((s) => s.setBrokerStatuses)
  const [disconnecting, setDisconnecting] = useState(null)
  const [expandedBroker, setExpandedBroker] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const base = `http://127.0.0.1:${port}`

  function openLogin(loginPath) {
    window.electronAPI?.openExternal(`${base}${loginPath}`)
  }

  async function disconnect(brokerKey) {
    setDisconnecting(brokerKey)
    setError(null)
    try {
      const r = await fetch(`${base}/api/broker/${brokerKey}`, { method: 'DELETE' })
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${r.status}`)
      }
      const res  = await fetch(`${base}/api/status`)
      const data = await res.json()
      setBrokerStatuses(data)
    } catch (e) {
      setError(e.message)
    }
    setDisconnecting(null)
  }

  async function saveKeysAndLogin(broker) {
    setSaving(true)
    setError(null)
    try {
      const inputs = document.querySelectorAll(`[data-broker-panel="${broker.key}"]`)
      for (const input of inputs) {
        if (!input.value.trim()) {
          setError(`Please fill in all fields for ${broker.name}`)
          setSaving(false)
          return
        }
        await fetch(`${base}/api/onboarding/credential`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: input.dataset.key, value: input.value.trim() }),
        })
      }
      // Refresh status then login
      const res = await fetch(`${base}/api/status`)
      setBrokerStatuses(await res.json())
      openLogin(broker.loginPath)
    } catch (e) {
      setError(e.message)
    }
    setSaving(false)
  }

  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-panel border-r border-border">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <p className="text-text text-[13px] font-semibold font-ui">Brokers</p>
        <button
          onClick={onClose}
          className="text-muted hover:text-text text-lg transition-colors leading-none cursor-pointer"
        >
          &times;
        </button>
      </div>

      {/* Broker list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {BROKERS.map((broker) => {
          const status = brokerStatuses[broker.key] ?? { configured: false, authenticated: false }
          const isExpanded = expandedBroker === broker.key

          return (
            <div key={broker.key} className="bg-elevated rounded-lg border border-border overflow-hidden">
              {/* Broker row */}
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    status.authenticated
                      ? 'bg-green shadow-[0_0_6px_rgba(82,224,122,0.4)]'
                      : status.configured ? 'bg-amber/50' : 'bg-subtle'
                  }`} />
                  <span className={`text-[13px] font-semibold font-ui ${broker.color}`}>{broker.name}</span>
                </div>

                {status.authenticated ? (
                  <button
                    onClick={() => disconnect(broker.key)}
                    disabled={disconnecting === broker.key}
                    className="text-[11px] font-ui px-2.5 py-1 rounded-md border border-red/30
                               text-red hover:bg-red/10 transition-colors disabled:opacity-40 cursor-pointer"
                  >
                    {disconnecting === broker.key ? '...' : 'Disconnect'}
                  </button>
                ) : status.configured ? (
                  <button
                    onClick={() => openLogin(broker.loginPath)}
                    className="text-[11px] font-ui px-2.5 py-1 rounded-md border border-green/30
                               text-green hover:bg-green/10 transition-colors cursor-pointer"
                  >
                    Connect
                  </button>
                ) : broker.keys.length > 0 ? (
                  <button
                    onClick={() => setExpandedBroker(isExpanded ? null : broker.key)}
                    className={`text-[11px] font-ui px-2.5 py-1 rounded-md border transition-colors cursor-pointer
                      ${isExpanded ? 'border-amber/30 text-amber bg-amber/10' : 'border-border text-muted hover:text-text'}`}
                  >
                    {isExpanded ? 'Hide' : 'Set Up'}
                  </button>
                ) : (
                  <span className="text-subtle text-[10px] font-ui">Coming soon</span>
                )}
              </div>

              {/* Expanded setup */}
              {isExpanded && (
                <div className="p-3 border-t border-border space-y-3">
                  {/* Portal link */}
                  <button
                    onClick={() => window.electronAPI?.openExternal(broker.portalUrl)}
                    className="w-full text-left text-amber text-[11px] font-ui hover:underline cursor-pointer"
                  >
                    Create app at {broker.portalLabel} &rarr;
                  </button>

                  {/* Redirect URL */}
                  <div>
                    <p className="text-muted text-[10px] font-ui mb-1">Redirect URL (set this in your broker app):</p>
                    <div className="flex items-center gap-1">
                      <code className="flex-1 bg-panel text-amber text-[10px] font-mono px-2 py-1.5 rounded border border-border truncate">
                        {broker.redirectUrl}
                      </code>
                      <button
                        onClick={() => navigator.clipboard.writeText(broker.redirectUrl)}
                        className="text-muted hover:text-text text-[10px] px-1.5 py-1.5 border border-border rounded cursor-pointer"
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  {/* Key inputs */}
                  {broker.keys.map((key) => (
                    <input
                      key={key.env}
                      data-broker-panel={broker.key}
                      data-key={key.env}
                      type={key.secret ? 'password' : 'text'}
                      placeholder={key.label}
                      className="w-full bg-panel border border-border rounded-lg px-3 py-2
                                 text-text text-xs font-mono placeholder:text-subtle
                                 focus:outline-none focus:border-amber"
                    />
                  ))}

                  {/* Save & Connect */}
                  <button
                    onClick={() => saveKeysAndLogin(broker)}
                    disabled={saving}
                    className="w-full px-3 py-2 bg-green/10 text-green border border-green/30
                               rounded-lg text-xs font-ui font-semibold hover:bg-green/20
                               transition-all disabled:opacity-40 cursor-pointer"
                  >
                    {saving ? 'Saving...' : 'Save & Connect'}
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border flex-shrink-0 space-y-1.5">
        {error && <p className="text-red text-[10px] font-ui">Error: {error}</p>}
        <p className="text-subtle text-[10px] font-ui leading-relaxed">
          Login opens your browser. OAuth completes automatically.
        </p>
      </div>
    </div>
  )
}
