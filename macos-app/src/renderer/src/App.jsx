import { useEffect } from 'react'
import { useChatStore } from './store/chatStore'
import Sidebar from './components/Sidebar'
import ChatArea from './components/Chat/ChatArea'
import InputBar from './components/Input/InputBar'

export default function App() {
  const { setPort, setSidecarError } = useChatStore()

  useEffect(() => {
    // Listen for future sidecar-ready events (first launch)
    window.electronAPI?.onSidecarReady(({ port }) => setPort(port))
    window.electronAPI?.onSidecarError(({ message }) => setSidecarError(message))

    // After HMR or renderer reload, sidecar-ready already fired — ask main for the port
    window.electronAPI?.getPort().then(port => { if (port) setPort(port) })
  }, [])

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

        {/* Status dot right */}
        <StatusDot />
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

function StatusDot() {
  const { port, sidecarError } = useChatStore()
  const connected = !!port && !sidecarError

  return (
    <div className="no-drag flex items-center gap-2 pr-4">
      <span className={`w-2 h-2 rounded-full transition-all ${
        connected ? 'bg-green shadow-[0_0_6px_rgba(82,224,122,0.5)]' : 'bg-subtle'
      }`} />
      <span className="text-muted text-[11px] font-ui">
        {sidecarError ? 'error' : connected ? 'connected' : 'starting…'}
      </span>
    </div>
  )
}
