import { useState, useEffect, useRef } from 'react'

export default function MarketDataStep({ formData, setFormData, onNext, port }) {
  const [newsKey, setNewsKey] = useState('')
  const [newsTesting, setNewsTesting] = useState(false)
  const [newsResult, setNewsResult] = useState(null)
  const [newsSaved, setNewsSaved] = useState(formData.newsApiSet || false)
  const [brokerPolling, setBrokerPolling] = useState(null)
  const [brokerConnected, setBrokerConnected] = useState(formData.brokerName || '')
  const pollRef = useRef(null)

  const base = `http://127.0.0.1:${port}`

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

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
        setFormData((prev) => ({ ...prev, newsApiSet: true }))
      }
    } catch (err) {
      setNewsResult({ ok: false, error: err.message })
    } finally {
      setNewsTesting(false)
    }
  }

  const handleBrokerLogin = (broker) => {
    setBrokerPolling(broker)
    const url = `http://127.0.0.1:${port}/${broker}/login`
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
        if (data[broker]?.authenticated) {
          clearInterval(pollRef.current)
          pollRef.current = null
          setBrokerPolling(null)
          setBrokerConnected(broker)
          setFormData((prev) => ({ ...prev, brokerName: broker }))
        }
      } catch {
        // keep polling
      }
    }, 2000)
  }

  const handleGetFreeKey = () => {
    const url = 'https://newsapi.org/register'
    if (window.electronAPI?.openExternal) {
      window.electronAPI.openExternal(url)
    } else {
      window.open(url, '_blank')
    }
  }

  const canProceed = newsSaved

  return (
    <div className="flex flex-col flex-1 gap-6 animate-fade-slide">
      <div className="text-center">
        <h2 className="text-text text-lg font-semibold font-ui">Market Data</h2>
        <p className="text-muted text-xs font-ui mt-1">
          Connect news and broker data sources
        </p>
      </div>

      <div className="max-w-lg mx-auto w-full space-y-6">
        {/* NewsAPI Section */}
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
                  onChange={(e) => {
                    setNewsKey(e.target.value)
                    setNewsResult(null)
                  }}
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
                onClick={handleGetFreeKey}
                className="text-amber text-[11px] font-ui hover:underline"
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

        {/* Broker Section */}
        <div className="bg-panel border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-text text-sm font-semibold font-ui">Broker (Optional)</h3>
              <p className="text-muted text-[11px] font-ui">Connect for live market data and execution</p>
            </div>
            {brokerConnected && (
              <span className="text-green text-xs font-ui font-semibold capitalize">
                {brokerConnected} connected
              </span>
            )}
          </div>

          <div className="bg-elevated border border-border rounded-lg p-3">
            <p className="text-muted text-[11px] font-ui leading-relaxed">
              Without a broker, you get delayed data and paper trading.
              Connect a broker for real-time data and live execution.
            </p>
          </div>

          {!brokerConnected && (
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleBrokerLogin('fyers')}
                disabled={brokerPolling === 'fyers'}
                className="flex flex-col items-start gap-1 p-3 rounded-lg border border-border
                           bg-elevated hover:border-subtle transition-all text-left
                           disabled:opacity-60"
              >
                <div className="flex items-center gap-2">
                  <span className="text-text text-sm font-semibold font-ui">Fyers</span>
                  <span className="text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded bg-green/20 text-green">
                    Free
                  </span>
                </div>
                <span className="text-muted text-[10px] font-ui">Best options data</span>
                {brokerPolling === 'fyers' && (
                  <span className="text-amber text-[10px] font-ui animate-pulse">
                    Waiting for login...
                  </span>
                )}
              </button>

              <button
                onClick={() => handleBrokerLogin('zerodha')}
                disabled={brokerPolling === 'zerodha'}
                className="flex flex-col items-start gap-1 p-3 rounded-lg border border-border
                           bg-elevated hover:border-subtle transition-all text-left
                           disabled:opacity-60"
              >
                <div className="flex items-center gap-2">
                  <span className="text-text text-sm font-semibold font-ui">Zerodha</span>
                  <span className="text-[10px] font-ui font-semibold px-1.5 py-0.5 rounded bg-blue/20 text-blue">
                    Paid
                  </span>
                </div>
                <span className="text-muted text-[10px] font-ui">Free personal plan</span>
                {brokerPolling === 'zerodha' && (
                  <span className="text-amber text-[10px] font-ui animate-pulse">
                    Waiting for login...
                  </span>
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-between max-w-lg mx-auto w-full mt-auto">
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
