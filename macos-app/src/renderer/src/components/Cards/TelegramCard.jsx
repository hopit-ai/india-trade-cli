export default function TelegramCard({ data }) {
  const d = data?.data ?? data ?? {}
  const configured = d.configured ?? false
  const running    = d.running    ?? false
  const hint       = d.token_hint

  const BOT_COMMANDS = [
    { cmd: '/quote INFY',   desc: 'Live price' },
    { cmd: '/analyze INFY', desc: 'Full AI analysis' },
    { cmd: '/brief',        desc: 'Morning market brief' },
    { cmd: '/flows',        desc: 'FII/DII flows' },
    { cmd: '/alerts',       desc: 'List active alerts' },
    { cmd: '/macro',        desc: 'Macro snapshot' },
    { cmd: '/memory',       desc: 'Trade history' },
    { cmd: '/help',         desc: 'All commands' },
  ]

  return (
    <div className="bg-elevated border border-border rounded-xl p-4 max-w-2xl w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-muted text-[10px] uppercase tracking-widest font-ui">Telegram Bot</p>
        <span className={`text-[10px] font-ui border rounded px-2 py-0.5 ${
          running    ? 'text-green border-green/30 bg-green/5'
          : configured ? 'text-amber border-amber/30 bg-amber/5'
          : 'text-red border-red/30 bg-red/5'
        }`}>
          {running ? '● Running' : configured ? '◌ Configured' : '○ Not configured'}
        </span>
      </div>

      {/* Status message */}
      {!configured && (
        <div className="border border-border bg-panel rounded-lg px-3 py-3 space-y-2">
          <p className="text-muted text-[11px] font-ui">To enable Telegram alerts and commands:</p>
          <ol className="space-y-1 text-[11px] font-ui text-text list-decimal list-inside">
            <li>Create a bot via <span className="text-blue">@BotFather</span> on Telegram</li>
            <li>Copy the bot token</li>
            <li>In the CLI: <span className="font-mono text-amber bg-panel px-1 rounded">credentials setup</span></li>
            <li>Enter the token as <span className="font-mono text-amber">TELEGRAM_BOT_TOKEN</span></li>
            <li>Start the bot: <span className="font-mono text-amber bg-panel px-1 rounded">telegram start</span></li>
          </ol>
        </div>
      )}

      {configured && !running && (
        <div className="border border-amber/30 bg-amber/5 rounded-lg px-3 py-2">
          <p className="text-amber text-[11px] font-ui">
            Token configured {hint ? `(…${hint})` : ''}. Start the bot from the CLI: <span className="font-mono">telegram start</span>
          </p>
        </div>
      )}

      {running && (
        <div className="border border-green/30 bg-green/5 rounded-lg px-3 py-2">
          <p className="text-green text-[11px] font-ui">
            Bot is active {hint ? `· token …${hint}` : ''}
          </p>
        </div>
      )}

      {/* Available commands */}
      <div>
        <p className="text-muted text-[10px] uppercase tracking-wider font-ui mb-2">Bot Commands</p>
        <div className="grid grid-cols-2 gap-1.5">
          {BOT_COMMANDS.map(({ cmd, desc }) => (
            <div key={cmd} className="flex items-center gap-2 bg-panel border border-border rounded px-2 py-1.5">
              <span className="text-blue text-[10px] font-mono">{cmd}</span>
              <span className="text-muted text-[10px] font-ui truncate">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
