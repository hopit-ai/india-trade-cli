export default function ProfileCard({ data }) {
  const d    = data?.data ?? data ?? {}
  const demo = d.demo ?? false

  const fields = [
    { label: 'Name',      value: d.name      ?? d.user_name   ?? '—' },
    { label: 'Client ID', value: d.client_id ?? d.user_id     ?? '—' },
    { label: 'Email',     value: d.email                      ?? '—' },
    { label: 'Broker',    value: d.broker    ?? d.broker_name ?? '—' },
    { label: 'Exchanges', value: Array.isArray(d.exchanges) ? d.exchanges.join(', ') : (d.exchanges ?? '—') },
  ]

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-sm w-full space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Account Profile</p>
        {demo && <span className="text-amber text-[10px] font-ui border border-amber/30 px-1.5 py-0.5 rounded">demo</span>}
      </div>

      <div className="space-y-2.5">
        {fields.map(({ label, value }) => (
          <div key={label} className="flex items-start justify-between gap-4">
            <span className="text-muted text-[11px] font-ui flex-shrink-0">{label}</span>
            <span className="text-text text-[12px] font-ui text-right truncate">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
