const PROVIDER_META = {
  anthropic:             { label: 'Anthropic',     color: 'text-blue',   bg: 'bg-blue/5   border-blue/20',   dot: '#5294e0' },
  openai:                { label: 'OpenAI',         color: 'text-green',  bg: 'bg-green/5  border-green/20',  dot: '#52e07a' },
  gemini:                { label: 'Google Gemini',  color: 'text-amber',  bg: 'bg-amber/5  border-amber/20',  dot: '#e06c00' },
  ollama:                { label: 'Ollama (local)', color: 'text-muted',  bg: 'bg-panel    border-border',    dot: '#666666' },
  claude_subscription:   { label: 'Claude.ai',      color: 'text-blue',   bg: 'bg-blue/5   border-blue/20',   dot: '#5294e0' },
  openai_subscription:   { label: 'ChatGPT',        color: 'text-green',  bg: 'bg-green/5  border-green/20',  dot: '#52e07a' },
  gemini_subscription:   { label: 'Gemini Pro',     color: 'text-amber',  bg: 'bg-amber/5  border-amber/20',  dot: '#e06c00' },
}

export default function ProviderCard({ data }) {
  const d         = data?.data ?? data ?? {}
  const current   = d.current   ?? 'unknown'
  const model     = d.model     ?? ''
  const available = d.available ?? []

  const meta = PROVIDER_META[current] ?? { label: current, color: 'text-text', bg: 'bg-panel border-border', dot: '#666666' }

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-md w-full space-y-4">
      <p className="text-muted text-[10px] uppercase tracking-widest font-ui">AI Provider</p>

      {/* Current provider */}
      <div className={`border rounded-xl px-4 py-3 ${meta.bg}`}>
        <p className="text-muted text-[9px] uppercase tracking-wider font-ui mb-1">Active</p>
        <p className={`text-[17px] font-ui font-semibold ${meta.color}`}>{meta.label}</p>
        {model && <p className="text-muted text-[11px] font-mono mt-0.5">{model}</p>}
      </div>

      {/* Available providers */}
      {available.length > 0 && (
        <div>
          <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Available</p>
          <div className="space-y-1.5">
            {available.map((p) => {
              const m = PROVIDER_META[p] ?? { label: p, color: 'text-muted', dot: '#444' }
              const isActive = p === current
              return (
                <div key={p} className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border ${isActive ? 'border-green/30 bg-green/5' : 'border-border bg-panel'}`}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: isActive ? '#52e07a' : m.dot, display: 'inline-block', flexShrink: 0 }} />
                  <span className={`text-[12px] font-ui ${isActive ? 'text-green font-semibold' : m.color}`}>{m.label}</span>
                  {isActive && <span className="ml-auto text-green text-[9px] font-ui uppercase tracking-wider">active</span>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Switch hint */}
      <p className="text-subtle text-[10px] font-ui">
        Switch with: <span className="font-mono text-muted">provider anthropic</span> · <span className="font-mono text-muted">provider openai</span> · <span className="font-mono text-muted">provider gemini</span>
      </p>
    </div>
  )
}
