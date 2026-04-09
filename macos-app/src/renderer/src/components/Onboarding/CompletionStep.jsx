export default function CompletionStep({ formData, onComplete, completing }) {
  const providerNames = {
    gemini: 'Google Gemini',
    anthropic: 'Claude (Anthropic)',
    openai: 'OpenAI',
    ollama: 'Ollama (Local)',
  }

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(val || 200000)
  }

  const items = [
    {
      label: 'AI Provider',
      value: providerNames[formData.aiProvider] || formData.aiProvider || 'Not set',
      ok: !!formData.aiProvider,
    },
    {
      label: 'NewsAPI',
      value: formData.newsApiSet ? 'Configured' : 'Not set',
      ok: !!formData.newsApiSet,
    },
    {
      label: 'Broker',
      value: formData.brokerName
        ? formData.brokerName.charAt(0).toUpperCase() + formData.brokerName.slice(1)
        : 'Skipped',
      ok: !!formData.brokerName,
      skipped: !formData.brokerName,
    },
    {
      label: 'Capital',
      value: formatCurrency(formData.capital),
      ok: true,
    },
    {
      label: 'Risk',
      value: `${formData.riskPct || 2}%`,
      ok: true,
    },
    {
      label: 'Mode',
      value: formData.tradingMode === 'LIVE' ? 'Live' : 'Paper',
      ok: true,
    },
  ]

  return (
    <div className="flex flex-col items-center flex-1 gap-6 animate-fade-slide">
      <div className="text-center">
        <span className="text-green text-4xl leading-none block mb-3">&#10003;</span>
        <h2 className="text-text text-lg font-semibold font-ui">All Set</h2>
        <p className="text-muted text-xs font-ui mt-1">
          Here is a summary of your configuration
        </p>
      </div>

      <div className="bg-panel border border-border rounded-lg p-4 max-w-md w-full space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-muted text-sm font-ui">{item.label}</span>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-mono ${item.ok ? 'text-text' : 'text-subtle'}`}>
                {item.value}
              </span>
              <span className={`text-xs ${item.skipped ? 'text-subtle' : item.ok ? 'text-green' : 'text-red'}`}>
                {item.skipped ? '\u2298' : item.ok ? '\u2713' : '\u2717'}
              </span>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onComplete}
        disabled={completing}
        className="mt-4 px-8 py-2.5 bg-amber text-surface font-ui font-semibold text-sm rounded-lg
                   hover:brightness-110 transition-all active:scale-95
                   disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {completing ? 'Saving...' : 'Start Trading'}
      </button>
    </div>
  )
}
