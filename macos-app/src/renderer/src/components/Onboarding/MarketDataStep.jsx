import { useState, useEffect, useRef } from 'react'

const BROKERS = {
  fyers: {
    name: 'Fyers',
    badge: 'Free',
    badgeColor: 'bg-green/20 text-green',
    desc: 'Best options chain data — free API',
    portalUrl: 'https://myapi.fyers.in',
    portalLabel: 'myapi.fyers.in',
    redirectUrl: 'http://127.0.0.1:8765/fyers/callback',
    keys: [
      { env: 'FYERS_APP_ID', label: 'App ID', placeholder: 'XXXX-100', secret: false },
      { env: 'FYERS_SECRET_KEY', label: 'Secret Key', placeholder: 'Your secret key', secret: true },
    ],
    steps: [
      'Create a free account at fyers.in (if you don\'t have one)',
      'Go to myapi.fyers.in → Create App',
      'Set the redirect URL exactly as shown below',
      'Copy your App ID and Secret Key',
    ],
  },
  zerodha: {
    name: 'Zerodha',
    badge: 'Free*',
    badgeColor: 'bg-blue/20 text-blue',
    desc: 'Order execution — free Personal plan',
    portalUrl: 'https://developers.kite.trade',
    portalLabel: 'developers.kite.trade',
    redirectUrl: 'http://localhost:8765/zerodha/callback',
    keys: [
      { env: 'KITE_API_KEY', label: 'API Key', placeholder: 'Your API key', secret: false },
      { env: 'KITE_API_SECRET', label: 'API Secret', placeholder: 'Your API secret', secret: true },
    ],
    steps: [
      'Log in at developers.kite.trade',
      'Create App → choose Personal (free) or Connect (Rs 500/mo)',
      'Set the redirect URL exactly as shown below',
      'Copy your API Key and API Secret',
      'Register your static IP on your Zerodha profile (SEBI requirement)',
    ],
  },
}

export default function MarketDataStep({ formData, setFormData, onNext, port }) {
  const [newsKey, setNewsKey] = useState('')
  const [newsTesting, setNewsTesting] = useState(false)
  const [newsResult, setNewsResult] = useState(null)
  const [newsSaved, setNewsSaved] = useState(formData.newsApiSet || false)
  const [brokerConnected, setBrokerConnected] = useState(formData.brokerName || '')
  const [expandedBroker, setExpandedBroker] = useState(null)
  const [brokerStatus, setBrokerStatus] = useState({})
  const [brokerPolling, setBrokerPolling] = useState(null)
  const pollRef = useRef(null)

  const base = `http://127.0.0.1:${port}`

  // Fetch broker status on mount
  useEffect(() => {
    fetch(`${base}/api/status`)
      .then(r => r.json())
      .then(data => {
        setBrokerStatus(data)
        // Auto-detect already connected broker
        for (const key of ['fyers', 'zerodha']) {
          if (data[key]?.authenticated) {
            setBrokerConnected(key)
            setFormData(prev => ({ ...prev, brokerName: key }))
          }
        }
      })
      .catch(() => {})
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  // ── NewsAPI ──────────────────────────────────────────────────

  const handleTestNews = async () => {
    setNewsTesting(true)
    setNewsResult(null)
    try {
      const res = await fetch(`${base}/api/onboarding/test-newsapi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: newsKey }),
      })
      const data = await res.json()
      setNewsResult(data)
      if (data.ok) {
        await fetch(`${base}/api/onboarding/credential`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: 'NEWSAPI_KEY', value: newsKey }),
        })
        setNewsSaved(true)
        setFormData(prev => ({ ...prev, newsApiSet: true }))
      }
    } catch (err) {
      setNewsResult({ ok: false, error: err.message })
    } finally {
      setNewsTesting(false)
    }
  }

  // ── Broker Setup ─────────────────────────────────────────────

  const handleSaveBrokerKeys = async (brokerId) => {
    const broker = BROKERS[brokerId]
    const inputs = document.querySelectorAll(`[data-broker="${brokerId}"]`)
    const values = {}
    inputs.forEach(input => { values[input.dataset.key] = input.value })

    // Validate all fields filled
    for (const key of broker.keys) {
      if (!values[key.env]?.trim()) return
    }

    // Save each key
    for (const key of broker.keys) {
      await fetch(`${base}/api/onboarding/credential`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: key.env, value: values[key.env].trim() }),
      })
    }

    // Trigger OAuth login
    handleBrokerLogin(brokerId)
  }

  const handleBrokerLogin = (brokerId) => {
    setBrokerPolling(brokerId)
    const url = `http://127.0.0.1:${port}/${brokerId}/login`
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(url)
    } else {
      window.open(url, '_blank')
    }

    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${base}/api/status`)
        const data = await res.json()
        setBrokerStatus(data)
        if (data[brokerId]?.authenticated) {
          clearInterval(pollRef.current)
          pollRef.current = null
          setBrokerPolling(null)
          setBrokerConnected(brokerId)
          setFormData(prev => ({ ...prev, brokerName: brokerId }))
        }
      } catch { /* keep polling */ }
    }, 2000)
  }

  const openExternal = (url) => {
    if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url)
    else window.open(url, '_blank')
  }

  const canProceed = newsSaved

  return (
    <div className="flex flex-col flex-1 gap-6 animate-fade-slide">
      <div className="text-center">
        <h2 className="text-text text-lg font-semibold font-ui">Market Data</h2>
        <p className="text-muted text-xs font-ui mt-1">Connect news and broker data sources</p>
      </div>

      <div className="max-w-xl mx-auto w-full space-y-4 overflow-y-auto flex-1">

        {/* ── NewsAPI ─────────────────────────────────────────── */}
        <div className="bg-panel border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-text text-sm font-semibold font-ui">NewsAPI</h3>
              <p className="text-muted text-[11px] font-ui">Required for AI news analysis</p>
            </div>
            {newsSaved && <span className="text-green text-xs font-ui font-semibold">Configured</span>}
          </div>

          {!newsSaved && (
            <>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="Enter NewsAPI key"
                  value={newsKey}
                  onChange={(e) => { setNewsKey(e.target.value); setNewsResult(null) }}
                  className="flex-1 bg-elevated border border-border rounded-lg px-3 py-2
                             text-text text-sm font-mono placeholder:text-subtle
                             focus:outline-none focus:border-amber"
                />
                <button
                  onClick={handleTestNews}
                  disabled={!newsKey || newsTesting}
                  className="px-3 py-2 bg-amber/10 text-amber border border-amber/30 rounded-lg
                             text-xs font-ui font-semibold hover:bg-amber/20 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {newsTesting ? 'Testing...' : 'Test'}
                </button>
              </div>
              <button
                onClick={() => openExternal('https://newsapi.org/register')}
                className="text-amber text-[11px] font-ui hover:underline cursor-pointer"
              >
                Get a free key at newsapi.org &rarr;
              </button>
              {newsResult && (
                <p className={`text-xs font-ui ${newsResult.ok ? 'text-green' : 'text-red'}`}>
                  {newsResult.ok ? 'NewsAPI key is valid' : newsResult.error}
                </p>
              )}
            </>
          )}
        </div>

        {/* ── Broker Section ──────────────────────────────────── */}
        <div className="bg-panel border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-text text-sm font-semibold font-ui">Broker (Optional)</h3>
              <p className="text-muted text-[11px] font-ui">Connect for live market data and trading</p>
            </div>
            {brokerConnected && (
              <span className="text-green text-xs font-ui font-semibold capitalize">
                {brokerConnected} connected
              </span>
            )}
          </div>

          <div className="bg-elevated border border-border rounded-lg p-3">
            <p className="text-muted text-[11px] font-ui leading-relaxed">
              Without a broker, you get 15-min delayed data and paper trading only.
              A broker gives you <span className="text-text">live quotes, options chain, and real order execution</span>.
            </p>
          </div>

          {!brokerConnected && (
            <div className="space-y-2">
              {Object.entries(BROKERS).map(([id, broker]) => {
                const isExpanded = expandedBroker === id
                const isConfigured = brokerStatus[id]?.configured
                const isPolling = brokerPolling === id

                return (
                  <div key={id} className="border border-border rounded-lg overflow-hidden">
                    {/* Broker header — click to expand */}
                    <button
                      onClick={() => setExpandedBroker(isExpanded ? null : id)}
                      className={`w-full flex items-center justify-between p-4 bg-elevated
                                 hover:border-amber/50 transition-all text-left border-b
                                 ${isExpanded ? 'border-amber/30' : 'border-transparent'}`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-text text-sm font-semibold font-ui">{broker.name}</span>
                          <span className={`text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded ${broker.badgeColor}`}>
                            {broker.badge}
                          </span>
                          {isConfigured && <span className="text-green text-[10px] font-ui">Keys set</span>}
                        </div>
                        <span className="text-muted text-[11px] font-ui mt-0.5 block">{broker.desc}</span>
                      </div>
                      <span className={`px-3 py-1.5 rounded-lg text-xs font-ui font-semibold transition-all
                        ${isExpanded
                          ? 'bg-amber/10 text-amber border border-amber/30'
                          : 'bg-elevated text-muted border border-border hover:text-text'}`}>
                        {isExpanded ? 'Hide' : 'Set Up'}
                      </span>
                    </button>

                    {/* Expanded: setup guide + key inputs */}
                    {isExpanded && (
                      <div className="p-3 border-t border-border space-y-3 bg-panel">

                        {/* Already configured — just connect */}
                        {isConfigured ? (
                          <div className="space-y-2">
                            <p className="text-green text-xs font-ui">API keys configured. Click to authenticate.</p>
                            <button
                              onClick={() => handleBrokerLogin(id)}
                              disabled={isPolling}
                              className="px-4 py-2 bg-green/10 text-green border border-green/30 rounded-lg
                                         text-sm font-ui font-semibold hover:bg-green/20 transition-all
                                         disabled:opacity-40 w-full"
                            >
                              {isPolling ? 'Waiting for login...' : 'Connect'}
                            </button>
                          </div>
                        ) : (
                          <>
                            {/* Step-by-step guide */}
                            <div className="space-y-1.5">
                              <p className="text-muted text-[10px] font-ui uppercase tracking-wider">Setup Guide</p>
                              {broker.steps.map((step, i) => (
                                <p key={i} className="text-muted text-[11px] font-ui flex gap-2">
                                  <span className="text-amber flex-shrink-0">{i + 1}.</span>
                                  <span>{step}</span>
                                </p>
                              ))}
                            </div>

                            {/* Open portal link */}
                            <button
                              onClick={() => openExternal(broker.portalUrl)}
                              className="w-full px-3 py-2 bg-amber/10 text-amber border border-amber/30
                                         rounded-lg text-xs font-ui font-semibold hover:bg-amber/20
                                         transition-all cursor-pointer"
                            >
                              Open {broker.portalLabel} &rarr;
                            </button>

                            {/* Redirect URL — copyable */}
                            <div>
                              <p className="text-muted text-[10px] font-ui mb-1">Redirect URL (copy this exactly):</p>
                              <CopyableCode text={broker.redirectUrl} />
                            </div>

                            {/* API key inputs */}
                            <div className="space-y-2">
                              {broker.keys.map((key) => (
                                <input
                                  key={key.env}
                                  data-broker={id}
                                  data-key={key.env}
                                  type={key.secret ? 'password' : 'text'}
                                  placeholder={key.label + ': ' + key.placeholder}
                                  className="w-full bg-elevated border border-border rounded-lg px-3 py-2
                                             text-text text-sm font-mono placeholder:text-subtle
                                             focus:outline-none focus:border-amber"
                                />
                              ))}
                            </div>

                            {/* Save & Connect */}
                            <button
                              onClick={() => handleSaveBrokerKeys(id)}
                              disabled={isPolling}
                              className="w-full px-4 py-2 bg-green/10 text-green border border-green/30
                                         rounded-lg text-sm font-ui font-semibold hover:bg-green/20
                                         transition-all disabled:opacity-40"
                            >
                              {isPolling ? 'Waiting for login...' : 'Save & Connect'}
                            </button>
                          </>
                        )}

                        {isPolling && (
                          <p className="text-amber text-[10px] font-ui animate-pulse text-center">
                            Complete the login in your browser...
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between max-w-xl mx-auto w-full">
        {!brokerConnected && !brokerPolling && (
          <span className="text-muted text-[11px] font-ui self-center">
            You can connect a broker later from Settings
          </span>
        )}
        <div className="ml-auto">
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
    </div>
  )
}

// ── Copyable code block ──────────────────────────────────────

function CopyableCode({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-2">
      <code className="flex-1 bg-elevated text-amber text-[11px] font-mono px-3 py-2 rounded border border-border truncate">
        {text}
      </code>
      <button
        onClick={handleCopy}
        className="text-muted hover:text-text text-xs px-2 py-2 border border-border rounded
                   transition-colors cursor-pointer flex-shrink-0"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}
