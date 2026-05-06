import { useState } from 'react'

export default function SetupScreen({ phase, data }) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="h-screen w-screen bg-[#0d0d0d] flex flex-col items-center justify-center px-8 text-center select-none"
         style={{ WebkitAppRegion: 'drag' }}>

      {/* Logo */}
      <div className="mb-8">
        <span className="text-4xl">◆</span>
        <h1 className="text-text text-xl font-semibold mt-2">Vibe Trading</h1>
      </div>

      {/* Progress state */}
      {(phase === 'initializing' || phase === 'progress') && (
        <ProgressView data={data} />
      )}

      {/* Python missing */}
      {phase === 'python_missing' && (
        <PythonMissingView data={data} />
      )}

      {/* Error */}
      {phase === 'error' && (
        <ErrorView data={data} showDetails={showDetails} setShowDetails={setShowDetails} />
      )}
    </div>
  )
}

// ── Progress ─────────────────────────────────────────────────────

function ProgressView({ data }) {
  const message = data?.message ?? 'Starting up...'
  const percent = data?.percent ?? null

  return (
    <div className="max-w-md w-full space-y-4" style={{ WebkitAppRegion: 'no-drag' }}>
      <p className="text-muted text-sm font-ui">{message}</p>

      {/* Progress bar */}
      <div className="w-full bg-border rounded-full h-1.5 overflow-hidden">
        {percent != null ? (
          <div
            className="bg-amber h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        ) : (
          <div className="bg-amber h-full rounded-full w-1/3 animate-pulse" />
        )}
      </div>

      {percent != null && (
        <p className="text-muted text-xs font-mono">{percent}%</p>
      )}

      <p className="text-muted/50 text-xs font-ui">
        {data?.stage === 'installing_deps'
          ? 'This only happens on first launch (~2 min)'
          : ''}
      </p>
    </div>
  )
}

// ── Python Missing ───────────────────────────────────────────────

function PythonMissingView({ data }) {
  const [copied, setCopied] = useState(false)

  function copyBrewCommand() {
    navigator.clipboard.writeText(data?.brewCommand ?? 'brew install python@3.12')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-lg w-full space-y-6" style={{ WebkitAppRegion: 'no-drag' }}>
      <div>
        <p className="text-amber text-lg font-semibold">Python 3.11+ Required</p>
        <p className="text-muted text-sm font-ui mt-2">
          Vibe Trading needs Python to run its analysis engine. Install it using one of the options below, then click Retry.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {/* Option 1: python.org */}
        <button
          onClick={() => window.electronAPI?.openExternal(data?.installUrl ?? 'https://www.python.org/downloads/')}
          className="bg-panel border border-border rounded-lg p-4 text-left hover:border-amber/50 transition-colors cursor-pointer"
        >
          <p className="text-text text-sm font-semibold">Download from python.org</p>
          <p className="text-muted text-xs mt-1">Official installer — works on all Macs</p>
        </button>

        {/* Option 2: Homebrew */}
        <div className="bg-panel border border-border rounded-lg p-4">
          <p className="text-text text-sm font-semibold">Install with Homebrew</p>
          <div className="flex items-center gap-2 mt-2">
            <code className="flex-1 bg-elevated text-amber text-xs font-mono px-3 py-2 rounded">
              {data?.brewCommand ?? 'brew install python@3.12'}
            </code>
            <button
              onClick={copyBrewCommand}
              className="text-muted hover:text-text text-xs px-2 py-2 border border-border rounded transition-colors cursor-pointer"
            >
              {copied ? '✓' : 'Copy'}
            </button>
          </div>
        </div>
      </div>

      <button
        onClick={() => window.electronAPI?.retrySetup()}
        className="w-full bg-amber/10 border border-amber/30 text-amber text-sm font-ui py-2.5 rounded-lg
                   hover:bg-amber/20 transition-colors cursor-pointer"
      >
        Retry
      </button>
    </div>
  )
}

// ── Error ────────────────────────────────────────────────────────

function ErrorView({ data, showDetails, setShowDetails }) {
  return (
    <div className="max-w-lg w-full space-y-4" style={{ WebkitAppRegion: 'no-drag' }}>
      <div>
        <p className="text-red text-lg font-semibold">Setup Failed</p>
        <p className="text-muted text-sm font-ui mt-2">{data?.message ?? 'An unknown error occurred.'}</p>
      </div>

      {data?.details && (
        <div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-muted text-xs font-ui hover:text-text transition-colors cursor-pointer"
          >
            {showDetails ? '▼ Hide details' : '▶ Show details'}
          </button>
          {showDetails && (
            <pre className="mt-2 bg-panel border border-border rounded-lg p-3 text-xs font-mono text-red/80
                           max-h-48 overflow-y-auto whitespace-pre-wrap">
              {data.details}
            </pre>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => window.electronAPI?.retrySetup()}
          className="flex-1 bg-amber/10 border border-amber/30 text-amber text-sm font-ui py-2.5 rounded-lg
                     hover:bg-amber/20 transition-colors cursor-pointer"
        >
          Retry
        </button>
        <button
          onClick={() => window.electronAPI?.resetVenv()}
          className="flex-1 bg-red/10 border border-red/30 text-red text-sm font-ui py-2.5 rounded-lg
                     hover:bg-red/20 transition-colors cursor-pointer"
        >
          Reset Environment
        </button>
      </div>
    </div>
  )
}
