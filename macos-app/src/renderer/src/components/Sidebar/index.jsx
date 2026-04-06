import { useChatStore } from '../../store/chatStore'
import { useAPI } from '../../hooks/useAPI'

const QUICK_COMMANDS = [
  { label: 'Morning Brief',  icon: '☀️',  command: 'morning-brief' },
  { label: 'Holdings',       icon: '📊',  command: 'holdings' },
  { label: 'Positions',      icon: '📈',  command: 'positions' },
  { label: 'Portfolio',      icon: '💼',  command: 'portfolio' },
  { label: 'FII/DII Flows',  icon: '🌊',  command: 'flows' },
]

export default function Sidebar() {
  const { addUserMessage, addResponse, addError, isLoading, brokerStatus, port } = useChatStore()
  const { call, ready } = useAPI()

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
    <div className="w-56 flex-shrink-0 bg-panel border-r border-border flex flex-col">

      {/* Broker status */}
      <div className="px-4 py-3 border-b border-border">
        <p className="text-muted text-[10px] uppercase tracking-widest mb-2 font-ui">Broker</p>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${brokerStatus.connected ? 'bg-green' : 'bg-subtle'}`} />
          <span className="text-text text-[12px] font-ui">
            {brokerStatus.broker || (port ? 'Demo mode' : 'Starting…')}
          </span>
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
        <p className="text-subtle text-[10px] font-ui">India Trade v0.2</p>
      </div>
    </div>
  )
}

// Route sidebar quick commands to API endpoints
async function routeCommand(call, command) {
  switch (command) {
    case 'morning-brief':
      return { cardType: 'morning_brief', data: await call('/skills/morning_brief', {}) }
    case 'holdings':
      return { cardType: 'holdings', data: await call('/skills/holdings', {}) }
    case 'positions':
      return { cardType: 'holdings', data: await call('/skills/positions', {}) }
    case 'portfolio':
      return { cardType: 'markdown', data: { text: 'Portfolio view coming soon.' } }
    case 'flows':
      return { cardType: 'flows', data: await call('/skills/flows', {}) }
    default:
      throw new Error(`Unknown command: ${command}`)
  }
}
