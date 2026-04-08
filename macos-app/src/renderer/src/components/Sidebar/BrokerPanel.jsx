import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'

const BROKERS = [
  {
    key:      'zerodha',
    name:     'Zerodha',
    color:    'text-[#387ed1]',
    loginPath: '/zerodha/login',
  },
  {
    key:      'groww',
    name:     'Groww',
    color:    'text-[#00c48c]',
    loginPath: '/groww/login',
  },
  {
    key:      'angel_one',
    name:     'Angel One',
    color:    'text-[#f6882a]',
    loginPath: '/angelone/login',
  },
  {
    key:      'upstox',
    name:     'Upstox',
    color:    'text-[#c4b5fd]',
    loginPath: '/upstox/login',
  },
  {
    key:      'fyers',
    name:     'Fyers',
    color:    'text-[#fed7aa]',
    loginPath: '/fyers/login',
  },
]

export default function BrokerPanel({ onClose }) {
  const port              = useChatStore((s) => s.port)
  const brokerStatuses    = useChatStore((s) => s.brokerStatuses)
  const setBrokerStatuses = useChatStore((s) => s.setBrokerStatuses)
  const [disconnecting, setDisconnecting] = useState(null)
  const [error, setError] = useState(null)

  function openLogin(loginPath) {
    const url = `http://127.0.0.1:${port}${loginPath}`
    window.electronAPI?.openExternal(url)
  }

  async function disconnect(brokerKey) {
    setDisconnecting(brokerKey)
    setError(null)
    try {
      const r = await fetch(`http://127.0.0.1:${port}/api/broker/${brokerKey}`, { method: 'DELETE' })
      if (!r.ok) {
        const body = await r.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${r.status}`)
      }
      // Refresh status immediately
      const res  = await fetch(`http://127.0.0.1:${port}/api/status`)
      const data = await res.json()
      setBrokerStatuses(data)
    } catch (e) {
      setError(e.message)
    }
    setDisconnecting(null)
  }

  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-panel border-r border-border">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <p className="text-text text-[13px] font-semibold font-ui">Connect Broker</p>
        <button
          onClick={onClose}
          className="text-muted hover:text-text text-lg transition-colors leading-none"
        >
          ✕
        </button>
      </div>

      {/* Broker list */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {BROKERS.map(({ key, name, color, loginPath }) => {
          const status = brokerStatuses[key] ?? { configured: false, authenticated: false }

          return (
            <div
              key={key}
              className="bg-elevated rounded-lg border border-border p-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    status.authenticated
                      ? 'bg-green shadow-[0_0_6px_rgba(82,224,122,0.4)]'
                      : status.configured ? 'bg-amber/50' : 'bg-subtle'
                  }`} />
                  <span className={`text-[13px] font-semibold font-ui ${color}`}>{name}</span>
                </div>

                {/* Action */}
                {status.authenticated ? (
                  <button
                    onClick={() => disconnect(key)}
                    disabled={disconnecting === key}
                    className="text-[11px] font-ui px-2.5 py-1 rounded-md border border-red/30
                               text-red hover:bg-red/10 transition-colors disabled:opacity-40"
                  >
                    {disconnecting === key ? '…' : 'Disconnect'}
                  </button>
                ) : status.configured ? (
                  <button
                    onClick={() => openLogin(loginPath)}
                    className="text-[11px] font-ui px-2.5 py-1 rounded-md border border-blue/40
                               text-blue hover:bg-blue/10 transition-colors"
                  >
                    Login →
                  </button>
                ) : (
                  <span className="text-subtle text-[10px] font-ui">Not configured</span>
                )}
              </div>

              {/* Sub-status */}
              {!status.authenticated && status.configured && (
                <p className="text-muted text-[10px] font-ui mt-1">
                  Credentials found — click Login to authenticate
                </p>
              )}
              {!status.configured && (
                <p className="text-subtle text-[10px] font-ui mt-1">
                  Add API keys to <span className="font-mono">.env</span> to enable
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border flex-shrink-0 space-y-1.5">
        {error && (
          <p className="text-red text-[10px] font-ui">⚠ {error}</p>
        )}
        <p className="text-subtle text-[10px] font-ui leading-relaxed">
          Login opens your browser. OAuth completes there; the app reconnects automatically.
        </p>
      </div>
    </div>
  )
}
