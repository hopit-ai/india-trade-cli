export default function MorningBriefCard({ data }) {
  const text = typeof data === 'string' ? data : data?.brief ?? data?.summary ?? JSON.stringify(data, null, 2)

  return (
    <div className="bg-elevated border border-amber/30 rounded-xl p-4 max-w-2xl w-full">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-amber">☀️</span>
        <p className="text-amber text-[11px] uppercase tracking-widest font-ui">Morning Brief</p>
      </div>
      <p className="text-text text-sm font-ui leading-relaxed whitespace-pre-wrap">{text}</p>
    </div>
  )
}
