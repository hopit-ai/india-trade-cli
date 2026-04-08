export default function ErrorCard({ text }) {
  return (
    <div className="bg-elevated border border-red/40 rounded-xl px-4 py-3 max-w-lg">
      <div className="flex items-start gap-2">
        <span className="text-red text-sm mt-0.5">✕</span>
        <p className="text-red text-sm font-ui leading-relaxed">{text}</p>
      </div>
    </div>
  )
}
