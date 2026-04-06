export default function MarkdownCard({ data }) {
  const text = typeof data === 'string' ? data : data?.text ?? data?.result ?? JSON.stringify(data, null, 2)

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full">
      <p className="text-text text-sm font-ui leading-relaxed whitespace-pre-wrap">{text}</p>
    </div>
  )
}
