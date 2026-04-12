import { useState } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useAPI } from '../../hooks/useAPI'
import BrokerPanel from './BrokerPanel'
import SettingsPanel from './SettingsPanel'

const ROLE_LABELS = { data: 'DATA', execution: 'EXEC', both: '' }

// Quick commands kept for routing — used by InputBar command chips, not displayed in sidebar
export const QUICK_COMMANDS = [
  { label: 'Morning Brief',  command: 'morning-brief' },
  { label: 'Holdings',       command: 'holdings' },
  { label: 'Positions',      command: 'positions' },
  { label: 'Orders',         command: 'orders' },
  { label: 'Funds',          command: 'funds' },
  { label: 'Alerts',         command: 'alerts' },
  { label: 'FII/DII Flows',  command: 'flows' },
  { label: 'Patterns',       command: 'patterns' },
  { label: 'Scan',           command: 'scan' },
  { label: 'GEX',            command: 'gex NIFTY' },
  { label: 'IV Smile',       command: 'iv-smile NIFTY' },
  { label: 'Risk Report',    command: 'risk-report' },
  { label: 'Strategy',       command: 'strategy NIFTY bullish' },
  { label: 'Delta Hedge',    command: 'delta-hedge' },
  { label: 'What-If',        command: 'whatif' },
  { label: 'Drift',          command: 'drift' },
  { label: 'Memory',         command: 'memory' },
]

export default function Sidebar() {
  const { isLoading, brokerStatuses, port } = useChatStore()
  const sessions = useChatStore((s) => s.sessions)
  const activeSessionId = useChatStore((s) => s.activeSessionId)
  const createSession = useChatStore((s) => s.createSession)
  const switchSession = useChatStore((s) => s.switchSession)
  const deleteSession = useChatStore((s) => s.deleteSession)
  const [showBrokerPanel, setShowBrokerPanel] = useState(false)
  const [showSettingsPanel, setShowSettingsPanel] = useState(false)
  const [hoveredSession, setHoveredSession] = useState(null)

  const sessionList = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt)
  const connectedBrokers = Object.entries(brokerStatuses).filter(([, b]) => b.authenticated)

  return (
    <div className="w-60 flex-shrink-0 bg-panel border-r border-border flex flex-col relative">

      {/* Broker panel overlay */}
      {showBrokerPanel && <BrokerPanel onClose={() => setShowBrokerPanel(false)} />}

      {/* Settings panel overlay */}
      {showSettingsPanel && <SettingsPanel onClose={() => setShowSettingsPanel(false)} />}

      {/* New session button */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={createSession}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border
                     text-[12px] font-ui text-muted hover:text-text hover:bg-elevated
                     transition-colors cursor-pointer"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New session
          <span className="ml-auto text-[10px] text-subtle font-ui">⌘N</span>
        </button>
      </div>

      {/* Session list — primary content */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="flex flex-col gap-0.5 py-1">
          {sessionList.map(s => (
            <div
              key={s.id}
              onMouseEnter={() => setHoveredSession(s.id)}
              onMouseLeave={() => setHoveredSession(null)}
              className={`group flex items-center rounded-lg cursor-pointer transition-colors
                ${s.id === activeSessionId
                  ? 'bg-elevated text-text'
                  : 'text-muted hover:bg-elevated/50 hover:text-text'}`}
            >
              <button
                onClick={() => switchSession(s.id)}
                className="flex-1 text-left px-3 py-2 text-[12px] font-ui truncate cursor-pointer"
              >
                {s.title}
              </button>
              {hoveredSession === s.id && sessionList.length > 1 && (
                <button
                  onClick={(e) => { e.stopPropagation(); deleteSession(s.id) }}
                  className="pr-2 text-subtle hover:text-red text-[11px] cursor-pointer transition-colors"
                  title="Delete session"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom bar — broker status + settings gear */}
      <div className="border-t border-border flex items-stretch">
        {/* Settings gear */}
        <button
          onClick={() => setShowSettingsPanel(true)}
          className="px-3 py-3 text-subtle hover:text-text transition-colors cursor-pointer flex-shrink-0"
          title="Settings"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>

      {/* Broker status — compact, at bottom */}
      <div
        className="flex-1 px-3 py-3 cursor-pointer hover:bg-elevated/50 transition-colors"
        onClick={() => setShowBrokerPanel(true)}
      >
        {connectedBrokers.length === 0 ? (
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-subtle flex-shrink-0" />
            <span className="text-[11px] text-muted font-ui">
              {port ? 'No broker connected' : 'Starting...'}
            </span>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {connectedBrokers.map(([key, status]) => {
              const name = { zerodha: 'Zerodha', groww: 'Groww', angel_one: 'Angel One', upstox: 'Upstox', fyers: 'Fyers' }[key] ?? key
              const roleLabel = ROLE_LABELS[status.role] || ''
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green flex-shrink-0" />
                  <span className="text-[11px] text-text font-ui">{name}</span>
                  {roleLabel && (
                    <span className={`text-[8px] font-ui font-bold uppercase tracking-wider px-1 py-0.5 rounded flex-shrink-0 ${
                      status.role === 'data' ? 'bg-blue/10 text-blue' : 'bg-amber/10 text-amber'
                    }`}>{roleLabel}</span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
      </div>
    </div>
  )
}

// Route sidebar quick commands to API endpoints (used by InputBar chips)
export async function routeCommand(call, command) {
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
    case 'gex NIFTY':
      return { cardType: 'gex',         data: unwrap(await call('/skills/gex',         { symbol: 'NIFTY', expiry: null })) }
    case 'iv-smile NIFTY':
      return { cardType: 'iv_smile',    data: unwrap(await call('/skills/iv_smile',    { symbol: 'NIFTY', expiry: null })) }
    case 'risk-report':
      return { cardType: 'risk_report', data: unwrap(await call('/skills/risk_report', {})) }
    case 'strategy NIFTY bullish':
      return { cardType: 'strategy',    data: unwrap(await call('/skills/strategy',    { symbol: 'NIFTY', view: 'BULLISH', dte: 30 })) }
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
