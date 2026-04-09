import { useState } from 'react'

const PROVIDERS = [
  {
    id: 'gemini',
    name: 'Google Gemini',
    badge: 'Free',
    badgeColor: 'bg-green/20 text-green',
    desc: 'Free tier at aistudio.google.com',
    keyEnv: 'GEMINI_API_KEY',
    keyLabel: 'Gemini API key',
    needsKey: true,
  },
  {
    id: 'anthropic',
    name: 'Claude API',
    badge: 'API',
    badgeColor: 'bg-blue/20 text-blue',
    desc: 'Anthropic Claude — pay per token',
    keyEnv: 'ANTHROPIC_API_KEY',
    keyLabel: 'Anthropic API key',
    needsKey: true,
  },
  {
    id: 'claude_subscription',
    name: 'Claude Pro/Max',
    badge: 'Free*',
    badgeColor: 'bg-blue/20 text-blue',
    desc: 'Uses your Claude subscription — no API key',
    keyEnv: null,
    keyLabel: null,
    needsKey: false,
    setupHint: 'Requires: npm i -g @anthropic-ai/claude-code && claude login',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    badge: 'API',
    badgeColor: 'bg-green/20 text-green',
    desc: 'GPT-4o and compatible endpoints',
    keyEnv: 'OPENAI_API_KEY',
    keyLabel: 'OpenAI API key',
    needsKey: true,
  },
  {
    id: 'ollama',
    name: 'Ollama',
    badge: 'Free',
    badgeColor: 'bg-green/20 text-green',
    desc: 'Local models — no API key needed',
    keyEnv: null,
    keyLabel: null,
    needsKey: false,
    setupHint: 'Requires: brew install ollama && ollama pull llama3.1',
  },
]

export default function ProviderStep({ formData, setFormData, onNext, port }) {
  const [selected, setSelected] = useState(formData.aiProvider || '')
  const [apiKey, setApiKey] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [saved, setSaved] = useState(false)

  const base = `http://127.0.0.1:${port}`

  const provider = PROVIDERS.find((p) => p.id === selected)

  const handleTest = async () => {
    if (!provider) return
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch(`${base}/api/onboarding/test-provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: provider.id,
          api_key: apiKey,
          model: '',
        }),
      })
      const data = await res.json()
      setTestResult(data)
      if (data.ok) {
        // Save AI_PROVIDER
        await fetch(`${base}/api/onboarding/credential`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: 'AI_PROVIDER', value: provider.id }),
        })
        // Save the API key if applicable
        if (provider.keyEnv && apiKey) {
          await fetch(`${base}/api/onboarding/credential`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: provider.keyEnv, value: apiKey }),
          })
        }
        setSaved(true)
        setFormData((prev) => ({ ...prev, aiProvider: provider.id }))
      }
    } catch (err) {
      setTestResult({ ok: false, error: err.message })
    } finally {
      setTesting(false)
    }
  }

  const handleSelect = (id) => {
    setSelected(id)
    setApiKey('')
    setTestResult(null)
    setSaved(false)
  }

  const canProceed = saved || formData.aiProvider

  return (
    <div className="flex flex-col flex-1 gap-6 animate-fade-slide">
      <div className="text-center">
        <h2 className="text-text text-lg font-semibold font-ui">Choose AI Provider</h2>
        <p className="text-muted text-xs font-ui mt-1">
          Powers market analysis, strategy generation, and trade signals
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 max-w-xl mx-auto w-full">
        {PROVIDERS.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelect(p.id)}
            className={`relative flex flex-col items-start gap-1.5 p-4 rounded-lg border transition-all text-left
              ${
                selected === p.id
                  ? 'border-amber bg-amber/5'
                  : 'border-border bg-panel hover:border-subtle'
              }`}
          >
            <div className="flex items-center gap-2 w-full">
              <span className="text-text text-sm font-semibold font-ui">{p.name}</span>
              <span className={`text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded ${p.badgeColor}`}>
                {p.badge}
              </span>
            </div>
            <span className="text-muted text-[11px] font-ui leading-snug">{p.desc}</span>
          </button>
        ))}
      </div>

      {selected && provider && (
        <div className="max-w-lg mx-auto w-full space-y-3">
          {provider.needsKey ? (
            <>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder={`Enter ${provider.name} API key`}
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value)
                    setTestResult(null)
                    setSaved(false)
                  }}
                  className="flex-1 bg-elevated border border-border rounded-lg px-3 py-2
                             text-text text-sm font-mono placeholder:text-subtle
                             focus:outline-none focus:border-amber"
                />
                <button
                  onClick={handleTest}
                  disabled={!apiKey || testing}
                  className="px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg
                             text-sm font-ui font-semibold hover:bg-amber/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {testing ? 'Testing...' : 'Test Key'}
                </button>
              </div>
              {testResult && (
                <p className={`text-xs font-ui ${testResult.ok ? 'text-green' : 'text-red'}`}>
                  {testResult.ok ? testResult.message : testResult.error}
                </p>
              )}
            </>
          ) : (
            <SetupRunner
              provider={provider}
              base={base}
              onComplete={() => {
                setSaved(true)
                setFormData((prev) => ({ ...prev, aiProvider: provider.id }))
                setTestResult({ ok: true, message: `${provider.name} configured` })
              }}
              saved={saved}
            />
          )}
        </div>
      )}

      <div className="flex justify-end max-w-lg mx-auto w-full mt-auto">
        <button
          onClick={onNext}
          disabled={!canProceed}
          className="px-6 py-2 bg-amber text-surface font-ui font-semibold text-sm rounded-lg
                     hover:brightness-110 transition-all active:scale-95
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
    </div>
  )
}

// ── Built-in setup runner for Ollama / Claude subscription ─────

function SetupRunner({ provider, base, onComplete, saved }) {
  const [steps, setSteps] = useState([])       // [{label, status, output}]
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const addStep = (label, status = 'pending') => {
    setSteps(prev => [...prev, { label, status, output: '' }])
    return prev => prev.length // index
  }

  const updateStep = (index, update) => {
    setSteps(prev => prev.map((s, i) => i === index ? { ...s, ...update } : s))
  }

  const callSetup = async (step) => {
    const res = await fetch(`${base}/api/onboarding/setup-provider`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: provider.id, step }),
    })
    return res.json()
  }

  const saveProvider = async () => {
    await fetch(`${base}/api/onboarding/credential`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'AI_PROVIDER', value: provider.id }),
    })
  }

  const runSetup = async () => {
    setRunning(true)
    setError(null)
    setSteps([])

    try {
      if (provider.id === 'ollama') {
        // Step 1: Check
        setSteps([{ label: 'Checking if Ollama is installed...', status: 'running', output: '' }])
        const check = await callSetup('check')

        if (!check.installed) {
          updateStep(0, { status: 'done', output: 'Not installed' })
          // Step 2: Install
          setSteps(prev => [...prev, { label: 'Installing Ollama via Homebrew...', status: 'running', output: '' }])
          const install = await callSetup('install')
          if (!install.ok) {
            updateStep(1, { status: 'error', output: install.error })
            if (install.download_url) {
              setError({ message: install.error, downloadUrl: install.download_url })
            }
            setRunning(false)
            return
          }
          updateStep(1, { status: 'done', output: install.output || 'Installed' })
        } else {
          updateStep(0, { status: 'done', output: check.message })
        }

        // Step 3: Start if needed
        if (!check.running) {
          setSteps(prev => [...prev, { label: 'Starting Ollama server...', status: 'running', output: '' }])
          const start = await callSetup('start')
          const idx = steps.length // approximate
          setSteps(prev => prev.map((s, i) => i === prev.length - 1 ? { ...s, status: start.ok ? 'done' : 'error', output: start.message || start.error } : s))
          if (!start.ok) { setRunning(false); return }
        }

        // Step 4: Pull model
        const recheck = await callSetup('check')
        if (!recheck.models || recheck.models.length === 0) {
          setSteps(prev => [...prev, { label: 'Downloading llama3.1 (~4GB)...', status: 'running', output: 'This may take a few minutes' }])
          const pull = await callSetup('pull_model')
          setSteps(prev => prev.map((s, i) => i === prev.length - 1 ? { ...s, status: pull.ok ? 'done' : 'error', output: pull.ok ? 'Model ready' : pull.error } : s))
          if (!pull.ok) { setRunning(false); return }
        }

        await saveProvider()
        setSteps(prev => [...prev, { label: 'Ollama configured', status: 'done', output: '' }])
        onComplete()

      } else if (provider.id === 'claude_subscription') {
        // Step 1: Check
        setSteps([{ label: 'Checking for Claude CLI...', status: 'running', output: '' }])
        const check = await callSetup('check')

        if (!check.installed) {
          updateStep(0, { status: 'done', output: 'Not installed' })
          // Step 2: Install
          setSteps(prev => [...prev, { label: 'Installing Claude CLI via npm...', status: 'running', output: '' }])
          const install = await callSetup('install')
          if (!install.ok) {
            updateStep(1, { status: 'error', output: install.error })
            setRunning(false)
            return
          }
          updateStep(1, { status: 'done', output: 'Claude CLI installed' })

          if (install.needs_login) {
            setSteps(prev => [...prev, {
              label: 'Run "claude login" in your terminal to authenticate',
              status: 'waiting',
              output: 'Open a terminal window and run: claude login'
            }])
          }
        } else {
          updateStep(0, { status: 'done', output: check.message })
        }

        await saveProvider()
        setSteps(prev => [...prev, { label: 'Claude subscription configured', status: 'done', output: '' }])
        onComplete()
      }
    } catch (err) {
      setError({ message: err.message })
    }
    setRunning(false)
  }

  if (saved) {
    return (
      <div className="space-y-2">
        <p className="text-green text-xs font-ui">Setup complete</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Setup steps output */}
      {steps.length > 0 && (
        <div className="bg-elevated border border-border rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
          {steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-xs font-mono">
              <span className="flex-shrink-0 mt-0.5">
                {step.status === 'running' ? '...' :
                 step.status === 'done' ? <span className="text-green">ok</span> :
                 step.status === 'waiting' ? <span className="text-amber">!</span> :
                 step.status === 'error' ? <span className="text-red">x</span> :
                 <span className="text-muted">-</span>}
              </span>
              <div>
                <span className="text-text">{step.label}</span>
                {step.output && (
                  <p className="text-muted text-[10px] mt-0.5">{step.output}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error with download link */}
      {error?.downloadUrl && (
        <button
          onClick={() => window.electronAPI?.openExternal(error.downloadUrl)}
          className="text-xs text-amber underline font-ui cursor-pointer"
        >
          Download Ollama manually from ollama.com
        </button>
      )}

      {/* Run button */}
      {!saved && (
        <button
          onClick={runSetup}
          disabled={running}
          className="px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg
                     text-sm font-ui font-semibold hover:bg-amber/20 transition-all
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {running ? 'Setting up...' : steps.length > 0 ? 'Retry Setup' : 'Set Up Automatically'}
        </button>
      )}
    </div>
  )
}
