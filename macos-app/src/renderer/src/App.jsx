import { useEffect } from 'react'
import { useChatStore } from './store/chatStore'
import { useMarketClock } from './hooks/useMarketClock'
import Sidebar from './components/Sidebar'
import ChatArea from './components/Chat/ChatArea'
import InputBar from './components/Input/InputBar'

export default function App() {
  const { setPort, setSidecarError, setBrokerStatuses } = useChatStore()
  const port = useChatStore((s) => s.port)

  useEffect(() => {
    window.electronAPI?.onSidecarReady(({ port }) => setPort(port))
    window.electronAPI?.onSidecarError(({ message }) => setSidecarError(message))
    window.electronAPI?.getPort().then(port => { if (port) setPort(port) })
  }, [])

  // Poll /api/status every 8s once sidecar is up
  useEffect(() => {
    if (!port) return
    const fetchStatus = () =>
      fetch(`http://127.0.0.1:${port}/api/status`)
        .then(r => r.json())
        .then(setBrokerStatuses)
        .catch(() => {})
    fetchStatus()
    const t = setInterval(fetchStatus, 8000)
    return () => clearInterval(t)
  }, [port])

  return (
    <div className="flex flex-col h-full bg-surface">

      {/* ── Title bar — 52px, draggable ── */}
      <div className="drag flex items-center h-[52px] bg-panel border-b border-border flex-shrink-0">
        {/* Traffic light spacer */}
        <div className="w-[76px] flex-shrink-0" />

        {/* App name — centred */}
        <div className="flex-1 flex items-center justify-center gap-2 pointer-events-none">
          <span className="text-amber text-[15px]">◆</span>
          <span className="text-text text-[13px] font-semibold tracking-wide font-ui">
            India Trade
          </span>
        </div>

        {/* Market status + API dot */}
        <div className="no-drag flex items-center gap-3 pr-4">
          <MarketBadge />
          <StatusDot />
        </div>
      </div>

      {/* ── Main layout ── */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex flex-col flex-1 overflow-hidden">
          <ChatArea />
          <InputBar />
        </div>
      </div>
    </div>
  )
}

function MarketBadge() {
  const { status, nifty } = useMarketClock()

  const cfg = {
    'open':       { dot: 'bg-green animate-pulse', label: 'Open',      text: 'text-green' },
    'pre-open':   { dot: 'bg-amber animate-pulse', label: 'Pre-open',  text: 'text-amber' },
    'post-close': { dot: 'bg-amber',               label: 'Post-close',text: 'text-amber' },
    'closed':     { dot: 'bg-subtle',              label: 'Closed',    text: 'text-subtle' },
  }[status] ?? { dot: 'bg-subtle', label: '', text: 'text-subtle' }

  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      <span className={`text-[11px] font-ui ${cfg.text}`}>
        {nifty ? `N ${nifty}` : cfg.label}
      </span>
    </div>
  )
}

function StatusDot() {
  const { port, sidecarError } = useChatStore()
  const connected = !!port && !sidecarError

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full transition-all ${
        connected ? 'bg-green shadow-[0_0_6px_rgba(82,224,122,0.5)]' : 'bg-subtle'
      }`} />
      <span className="text-muted text-[11px] font-ui">
        {sidecarError ? 'error' : connected ? 'connected' : 'starting…'}
      </span>
    </div>
  )
}
