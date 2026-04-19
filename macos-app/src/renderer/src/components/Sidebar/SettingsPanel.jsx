import { useState, useEffect } from 'react'
import { useChatStore } from '../../store/chatStore'

const SECTIONS = [
  {
    title: 'AI Provider',
    fields: [
      {
        key: 'AI_PROVIDER',
        label: 'Provider',
        type: 'select',
        options: ['anthropic', 'openai', 'gemini', 'ollama', 'openrouter'],
        placeholder: 'anthropic',
      },
      { key: 'AI_MODEL', label: 'Deep model', type: 'text', placeholder: 'claude-sonnet-4-5' },
      {
        key: 'AI_FAST_PROVIDER',
        label: 'Fast provider',
        type: 'select',
        options: ['', 'anthropic', 'openai', 'gemini', 'ollama', 'openrouter'],
        placeholder: '(same as provider)',
      },
      { key: 'AI_FAST_MODEL', label: 'Fast model', type: 'text', placeholder: 'claude-haiku-3-5' },
      { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API key', type: 'password', placeholder: 'sk-ant-...' },
      { key: 'OPENAI_API_KEY', label: 'OpenAI API key', type: 'password', placeholder: 'sk-...' },
      { key: 'OPENAI_BASE_URL', label: 'OpenAI base URL', type: 'text', placeholder: 'https://openrouter.ai/api/v1' },
      { key: 'OPENAI_MODEL', label: 'OpenAI model', type: 'text', placeholder: 'gpt-4o' },
      { key: 'GEMINI_API_KEY', label: 'Gemini API key', type: 'password', placeholder: 'AIza...' },
    ],
  },
  {
    title: 'Trading',
    fields: [
      {
        key: 'TRADING_MODE',
        label: 'Mode',
        type: 'select',
        options: ['paper', 'live'],
        placeholder: 'paper',
      },
      { key: 'TRADING_CAPITAL', label: 'Total capital (INR)', type: 'text', placeholder: '100000' },
      { key: 'DEFAULT_RISK_PCT', label: 'Default risk per trade (%)', type: 'text', placeholder: '1.0' },
    ],
  },
  {
    title: 'Notifications',
    fields: [
      { key: 'TELEGRAM_BOT_TOKEN', label: 'Telegram bot token', type: 'password', placeholder: 'bot12345:...' },
    ],
  },
  {
    title: 'Data',
    fields: [
      { key: 'NEWSAPI_KEY', label: 'NewsAPI key', type: 'password', placeholder: 'abcdef...' },
    ],
  },
]

export default function SettingsPanel({ onClose }) {
  const port = useChatStore((s) => s.port)
  const base = window.__INDIA_TRADE_WEB__
    ? window.location.origin
    : `http://127.0.0.1:${port}`

  const [current, setCurrent] = useState({})
  const [edits, setEdits] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${base}/skills/settings`)
      .then((r) => r.json())
      .then((d) => {
        if (d.status === 'ok') setCurrent(d.data ?? {})
      })
      .catch(() => {})
  }, [base])

  function handleChange(key, value) {
    setEdits((prev) => ({ ...prev, [key]: value }))
  }

  function currentValue(field) {
    // For password fields, never show the actual value — show blank
    if (field.type === 'password') return edits[field.key] ?? ''
    return edits[field.key] ?? current[field.key.toLowerCase()] ?? ''
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      // Only send keys that were actually edited and non-empty
      const toSend = Object.fromEntries(
        Object.entries(edits).filter(([, v]) => v.trim() !== '')
      )
      if (Object.keys(toSend).length === 0) {
        setSaving(false)
        onClose()
        return
      }
      const r = await fetch(`${base}/skills/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: toSend }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail ?? `HTTP ${r.status}`)
      setSaved(true)
      setTimeout(() => onClose(), 1000)
    } catch (e) {
      setError(e.message)
    }
    setSaving(false)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-[520px] max-h-[85vh] flex flex-col bg-panel border border-border rounded-xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
          <p className="text-text text-[13px] font-semibold font-ui">Settings</p>
          <button
            onClick={onClose}
            className="text-muted hover:text-text text-lg transition-colors leading-none cursor-pointer"
          >
            &times;
          </button>
        </div>

        {/* Sections */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">
          {SECTIONS.map((section) => (
            <div key={section.title}>
              <p className="text-subtle text-[10px] font-ui font-semibold uppercase tracking-wider mb-2">
                {section.title}
              </p>
              <div className="space-y-2">
                {section.fields.map((field) => (
                  <div key={field.key} className="flex items-center gap-3">
                    <label className="text-muted text-[11px] font-ui w-44 flex-shrink-0">
                      {field.label}
                    </label>
                    {field.type === 'select' ? (
                      <select
                        value={currentValue(field)}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        className="flex-1 bg-elevated border border-border rounded-lg px-2 py-1.5
                                   text-text text-[11px] font-ui focus:outline-none focus:border-amber
                                   cursor-pointer"
                      >
                        {field.options.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt || '(inherit)'}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={field.type}
                        value={currentValue(field)}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        placeholder={
                          field.type === 'password' && current[field.key.toLowerCase() + '_set']
                            ? '••••••••••••'
                            : field.placeholder
                        }
                        className="flex-1 bg-elevated border border-border rounded-lg px-2 py-1.5
                                   text-text text-[11px] font-mono placeholder:text-subtle
                                   focus:outline-none focus:border-amber"
                      />
                    )}
                    {/* Show a small green dot for keys that are already set */}
                    {field.type === 'password' && current[field.key.toLowerCase() + '_set'] && !edits[field.key] && (
                      <span className="w-1.5 h-1.5 rounded-full bg-green flex-shrink-0" title="Set" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border flex-shrink-0">
          {saved && (
            <p className="text-green text-[11px] font-ui text-center mb-2">Saved successfully</p>
          )}
          {error && (
            <p className="text-red text-[10px] font-ui mb-2">Error: {error}</p>
          )}
          <div className="flex gap-2 justify-end">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-muted hover:text-text text-[11px] font-ui
                         border border-border rounded-lg transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 bg-amber/10 text-amber border border-amber/30
                         rounded-lg text-[11px] font-ui font-semibold
                         hover:bg-amber/20 transition-all disabled:opacity-40 cursor-pointer"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
