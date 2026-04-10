import { useEffect, useState } from 'react'
import { useChatStore } from './store/chatStore'
import { useMarketClock } from './hooks/useMarketClock'
import Sidebar from './components/Sidebar'
import ChatArea from './components/Chat/ChatArea'
import InputBar from './components/Input/InputBar'
import SetupScreen from './components/SetupScreen'
import OnboardingWizard from './components/Onboarding/OnboardingWizard'

export default function App() {
  const { setPort, setSidecarError, setBrokerStatuses } = useChatStore()
  const port = useChatStore((s) => s.port)

  // Setup phase state machine
  const [setupPhase, setSetupPhase] = useState('initializing')
  // 'initializing' | 'progress' | 'python_missing' | 'error' | 'onboarding' | 'ready'
  const [setupData, setSetupData] = useState(null)

  useEffect(() => {
    // Web mode — no Electron IPC, just check if server is ready
    if (window.__INDIA_TRADE_WEB__) {
      const checkReady = async () => {
        try {
          const res = await fetch('/api/onboarding/status')
          if (res.status === 401) {
            // Not authenticated — auth.html should have redirected, but just in case
            window.location.href = '/'
            return
          }
          const data = await res.json()
          setPort(0) // Signal that API is available (web uses relative URLs)
          if (data.onboarding_complete) {
            setSetupPhase('ready')
          } else {
            setSetupPhase('onboarding')
          }
        } catch {
          setSetupPhase('error')
          setSetupData({ message: 'Cannot connect to server' })
        }
      }
      checkReady()
      return
    }

    // Setup progress events
    window.electronAPI?.onSetupProgress((data) => {
      setSetupPhase('progress')
      setSetupData(data)
    })

    // Python not found
    window.electronAPI?.onSetupPythonMissing((data) => {
      setSetupPhase('python_missing')
      setSetupData(data)
    })

    // Sidecar ready — check onboarding before showing main UI
    window.electronAPI?.onSidecarReady(async ({ port }) => {
      setPort(port)
      try {
        const res = await fetch(`http://127.0.0.1:${port}/api/onboarding/status`)
        const data = await res.json()
        if (data.onboarding_complete) {
          setSetupPhase('ready')
        } else {
          setSetupPhase('onboarding')
        }
      } catch {
        setSetupPhase('ready')
      }
    })

    // Sidecar error — could be during setup or runtime
    window.electronAPI?.onSidecarError(({ message, details }) => {
      setSidecarError(message)
      if (setupPhase !== 'ready') {
        setSetupPhase('error')
        setSetupData({ message, details })
      }
    })

    // Check if port already set (HMR / reload)
    window.electronAPI?.getPort().then(async (port) => {
      if (port) {
        setPort(port)
        try {
          const res = await fetch(`http://127.0.0.1:${port}/api/onboarding/status`)
          const data = await res.json()
          if (data.onboarding_complete) {
            setSetupPhase('ready')
          } else {
            setSetupPhase('onboarding')
          }
        } catch {
          setSetupPhase('ready')
        }
      }
    })
  }, [])

  // Poll /api/status every 8s once sidecar is up
  useEffect(() => {
    if (!port && port !== 0) return
    const statusUrl = window.__INDIA_TRADE_WEB__
      ? '/api/status'
      : `http://127.0.0.1:${port}/api/status`
    const fetchStatus = () =>
      fetch(statusUrl)
        .then(r => r.json())
        .then(setBrokerStatuses)
        .catch(() => {})
    fetchStatus()
    const t = setInterval(fetchStatus, 8000)
    return () => clearInterval(t)
  }, [port])

  // Show onboarding wizard for first-launch setup
  if (setupPhase === 'onboarding') {
    return <OnboardingWizard port={port} onComplete={() => setSetupPhase('ready')} />
  }

  // Show setup screen until ready
  if (setupPhase !== 'ready') {
    return <SetupScreen phase={setupPhase} data={setupData} />
  }

  return (
    <div className="flex flex-col h-full bg-surface">

      {/* Title bar */}
      <div className="drag flex items-center h-[52px] bg-panel border-b border-border flex-shrink-0">
        <div className="w-[76px] flex-shrink-0" />
        <div className="flex-1 flex items-center justify-center gap-2 pointer-events-none">
          <span className="text-amber text-[15px]">◆</span>
          <span className="text-text text-[13px] font-semibold tracking-wide font-ui">
            India Trade
          </span>
        </div>
        <div className="no-drag flex items-center gap-3 pr-4">
          <MarketBadge />
          <StatusDot />
        </div>
      </div>

      {/* Main layout */}
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
        {sidecarError ? 'error' : connected ? 'connected' : 'starting...'}
      </span>
    </div>
  )
}
