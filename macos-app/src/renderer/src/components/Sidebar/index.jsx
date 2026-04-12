import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useAPI } from '../../hooks/useAPI'
import BrokerPanel from './BrokerPanel'

const QUICK_COMMANDS = [
  { label: 'Morning Brief',  icon: '☀️',  command: 'morning-brief' },
  { label: 'Holdings',       icon: '📊',  command: 'holdings' },
  { label: 'Positions',      icon: '📈',  command: 'positions' },
  { label: 'Orders',         icon: '📋',  command: 'orders' },
  { label: 'Funds',          icon: '💰',  command: 'funds' },
  { label: 'Alerts',         icon: '🔔',  command: 'alerts' },
  { label: 'FII/DII Flows',  icon: '🌊',  command: 'flows' },
  { label: 'Patterns',       icon: '🔍',  command: 'patterns' },
  { label: 'Scan',           icon: '📡',  command: 'scan' },
  // ── Analysis ──────────────────────────────────────────────
  { label: 'GEX',            icon: '⚡',  command: 'gex NIFTY' },
  { label: 'IV Smile',       icon: '📉',  command: 'iv-smile NIFTY' },
  { label: 'Risk Report',    icon: '🛡',  command: 'risk-report' },
  { label: 'Strategy',       icon: '🎯',  command: 'strategy NIFTY bullish' },
  // ── Portfolio ─────────────────────────────────────────────
  { label: 'Delta Hedge',    icon: '⚖️',  command: 'delta-hedge' },
  { label: 'What-If',        icon: '🔮',  command: 'whatif' },
  { label: 'Drift',          icon: '📐',  command: 'drift' },
  { label: 'Memory',         icon: '🧠',  command: 'memory' },
]

const ROLE_LABELS = { data: 'DATA', execution: 'EXEC', both: '' }

export default function Sidebar() {
  const { addUserMessage, addResponse, addError, isLoading, brokerStatus, brokerStatuses, port } = useChatStore()
  const sessions = useChatStore((s) => s.sessions)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const { call, ready } = useAPI()
  const [showBrokerPanel, setShowBrokerPanel] = useState(false)

  const sessionList = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt)

  async function runCommand(command) {
    if (!ready || isLoading) return
    addUserMessage(command)
    try {
      const data = await routeCommand(call, command)
      addResponse(data)
    } catch (e) {
      addError(e.message)
    }
  }

  return (
    <div className="w-56 flex-shrink-0 bg-panel border-r border-border flex flex-col relative">

      {/* Broker panel overlay */}
      {showBrokerPanel && <BrokerPanel onClose={() => setShowBrokerPanel(false)} />}

      {/* Broker status — click to open broker panel */}
      <div
        className="px-4 py-3 border-b border-border cursor-pointer hover:bg-elevated transition-colors group"
        onClick={() => setShowBrokerPanel(true)}
      >
        <p className="text-muted text-[10px] uppercase tracking-widest mb-2 font-ui">Broker</p>
        {(() => {
          const connectedBrokers = Object.entries(brokerStatuses).filter(([, b]) => b.authenticated)
          if (connectedBrokers.length === 0) {
            return (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full flex-shrink-0 bg-subtle" />
                  <span className="text-text text-[12px] font-ui truncate">
                    {port ? 'Not connected' : 'Starting...'}
                  </span>
                </div>
                <span className="text-subtle text-[10px] font-ui opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-1">
                  connect
                </span>
              </div>
            )
          }
          return (
            <div className="flex flex-col gap-1">
              {connectedBrokers.map(([key, status]) => {
                const name = { zerodha: 'Zerodha', groww: 'Groww', angel_one: 'Angel One', upstox: 'Upstox', fyers: 'Fyers' }[key] ?? key
                const roleLabel = ROLE_LABELS[status.role] || ''
                return (
                  <div key={key} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2 h-2 rounded-full flex-shrink-0 bg-green shadow-[0_0_6px_rgba(82,224,122,0.4)]" />
                      <span className="text-text text-[12px] font-ui truncate">{name}</span>
                    </div>
                    {roleLabel && (
                      <span className={`text-[9px] font-ui font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                        status.role === 'data' ? 'bg-blue/15 text-blue' : 'bg-amber/15 text-amber'
                      }`}>{roleLabel}</span>
                    )}
                  </div>
                )
              })}
              <span className="text-subtle text-[10px] font-ui opacity-0 group-hover:opacity-100 transition-opacity">
                manage
              </span>
            </div>
          )
        })()}
      </div>

      {/* Sessions */}
      <div className="px-3 py-2 border-b border-border">
        <div className="flex items-center justify-between mb-2 px-1">
          <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Sessions</p>
          <button onClick={createSession} className="text-blue text-[11px] font-ui hover:underline cursor-pointer">+ New</button>
        </div>
        <div className="flex flex-col gap-0.5 max-h-[200px] overflow-y-auto">
          {sessionList.map(s => (
            <button
              key={s.id}
              onClick={() => switchSession(s.id)}
              className={`text-left px-2 py-1.5 rounded text-[12px] font-ui truncate cursor-pointer
                ${s.id === activeSessionId ? 'bg-elevated text-text' : 'text-muted hover:bg-elevated/50'}`}
            >
              {s.title}
            </button>
          ))}
        </div>
      </div>

      {/* Quick commands */}
      <div className="px-3 py-3 flex-1">
        <p className="text-muted text-[10px] uppercase tracking-widest mb-2 px-1 font-ui">Quick</p>
        <div className="flex flex-col gap-1">
          {QUICK_COMMANDS.map((q) => (
            <button
              key={q.command}
              onClick={() => runCommand(q.command)}
              disabled={!ready || isLoading}
              className="flex items-center gap-2 px-2 py-1.5 rounded text-[12px] text-text
                         hover:bg-elevated transition-colors disabled:opacity-40
                         text-left font-ui"
            >
              <span>{q.icon}</span>
              <span>{q.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Version */}
      <div className="px-4 py-3 border-t border-border">
        <p className="text-subtle text-[10px] font-ui">Vibe Trading v0.2</p>
      </div>
    </div>
  )
}

// Route sidebar quick commands to API endpoints
async function routeCommand(call, command) {
  const unwrap = (res) => res.data ?? res
  switch (command) {
    case 'morning-brief':
      return { cardType: 'morning_brief', data: unwrap(await call('/skills/morning_brief', {})) }
    case 'holdings':
      return { cardType: 'holdings', data: unwrap(await call('/skills/holdings', {})) }
    case 'positions':
      return { cardType: 'holdings', data: unwrap(await call('/skills/positions', {})) }
    case 'flows': {
      const fd = unwrap(await call('/skills/flows', {}))
      return { cardType: 'flows', data: fd?.flow_analysis ?? fd }
    }
    case 'orders':
      return { cardType: 'orders', data: unwrap(await call('/skills/orders', {})) }
    case 'funds':
      return { cardType: 'funds',    data: unwrap(await call('/skills/funds',    {})) }
    case 'alerts':
      return { cardType: 'alerts',   data: unwrap(await call('/skills/alerts/list', {})) }
    case 'patterns':
      return { cardType: 'patterns', data: unwrap(await call('/skills/patterns', {})) }
    case 'scan':
      return { cardType: 'scan',     data: unwrap(await call('/skills/scan',     { scan_type: 'options', filters: {} })) }
    // ── Analysis ──────────────────────────────────────────────
    case 'gex NIFTY':
      return { cardType: 'gex',         data: unwrap(await call('/skills/gex',         { symbol: 'NIFTY', expiry: null })) }
    case 'iv-smile NIFTY':
      return { cardType: 'iv_smile',    data: unwrap(await call('/skills/iv_smile',    { symbol: 'NIFTY', expiry: null })) }
    case 'risk-report':
      return { cardType: 'risk_report', data: unwrap(await call('/skills/risk_report', {})) }
    case 'strategy NIFTY bullish':
      return { cardType: 'strategy',    data: unwrap(await call('/skills/strategy',    { symbol: 'NIFTY', view: 'BULLISH', dte: 30 })) }
    // ── Portfolio ─────────────────────────────────────────────
    case 'delta-hedge':
      return { cardType: 'delta_hedge', data: unwrap(await call('/skills/delta_hedge', {})) }
    case 'whatif':
      return { cardType: 'whatif',      data: unwrap(await call('/skills/whatif',      { scenario: 'market' })) }
    case 'drift':
      return { cardType: 'drift',       data: unwrap(await call('/skills/drift',       {})) }
    case 'memory':
      return { cardType: 'memory',      data: unwrap(await call('/skills/memory',      {})) }
    default:
      throw new Error(`Unknown command: ${command}`)
  }
}
