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
            <div className="space-y-3">
              {provider.setupHint && (
                <div className="bg-elevated border border-border rounded-lg px-3 py-2">
                  <code className="text-amber text-xs font-mono">{provider.setupHint}</code>
                </div>
              )}
              {provider.id === 'claude_subscription' ? (
                <button
                  onClick={async () => {
                    // For Claude subscription, just save the provider — no test needed
                    await fetch(`${base}/api/onboarding/credential`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ key: 'AI_PROVIDER', value: 'claude_subscription' }),
                    })
                    setSaved(true)
                    setFormData((prev) => ({ ...prev, aiProvider: 'claude_subscription' }))
                    setTestResult({ ok: true, message: 'Claude subscription selected' })
                  }}
                  disabled={saved}
                  className="px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg
                             text-sm font-ui font-semibold hover:bg-amber/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saved ? 'Selected' : 'Use Claude Subscription'}
                </button>
              ) : (
                <button
                  onClick={handleTest}
                  disabled={testing}
                  className="px-4 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg
                             text-sm font-ui font-semibold hover:bg-amber/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {testing ? 'Testing...' : 'Test Connection'}
                </button>
              )}
              {testResult && (
                <p className={`text-xs font-ui ${testResult.ok ? 'text-green' : 'text-red'}`}>
                  {testResult.ok ? testResult.message : testResult.error}
                </p>
              )}
            </div>
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
