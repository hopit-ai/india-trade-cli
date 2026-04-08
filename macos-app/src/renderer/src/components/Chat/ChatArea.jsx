import { useEffect, useRef, useState } from 'react'
import { useChatStore } from '../../store/chatStore'
import Message from './Message'

export default function ChatArea() {
  const messages     = useChatStore((s) => s.messages)
  const isLoading    = useChatStore((s) => s.isLoading)
  const sidecarError = useChatStore((s) => s.sidecarError)
  const port         = useChatStore((s) => s.port)
  const bottomRef    = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

      {/* Welcome / status */}
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <span className="text-amber text-4xl">◆</span>
          <p className="text-text text-lg font-semibold font-ui">India Trade</p>
          {sidecarError ? (
            <p className="text-red text-sm max-w-sm font-ui">{sidecarError}</p>
          ) : port ? (
            <p className="text-muted text-sm font-ui">
              Type a command below or use the sidebar shortcuts.
            </p>
          ) : (
            <p className="text-muted text-sm font-ui">Starting API server…</p>
          )}
        </div>
      )}

      {/* Message list */}
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}

      {/* Loading indicator — hide when a streaming card is already showing live progress */}
      {isLoading && !messages.some(m => m.cardType === 'streaming_analysis') && (
        <ThinkingIndicator />
      )}

      <div ref={bottomRef} />
    </div>
  )
}

function ThinkingIndicator() {
  const [secs, setSecs] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const hint = secs > 15
    ? 'Running multi-agent analysis — this takes 30–90s…'
    : secs > 5
    ? 'Calling AI agents…'
    : 'Thinking…'

  return (
    <div className="flex items-center gap-3 bg-elevated border border-border rounded-xl px-4 py-3 max-w-sm">
      <span className="text-amber animate-pulse text-lg">◆</span>
      <div>
        <p className="text-text text-sm font-ui">{hint}</p>
        <p className="text-muted text-xs font-mono mt-0.5">{secs}s elapsed</p>
      </div>
    </div>
  )
}
