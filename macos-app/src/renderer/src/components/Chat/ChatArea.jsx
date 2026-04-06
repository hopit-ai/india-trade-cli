import { useEffect, useRef } from 'react'
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

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 text-muted text-sm font-mono">
          <span className="animate-pulse">◆</span>
          <span>Thinking…</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
