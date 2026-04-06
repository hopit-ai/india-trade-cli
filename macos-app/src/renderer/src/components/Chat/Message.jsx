import QuoteCard from '../Cards/QuoteCard'
import MarkdownCard from '../Cards/MarkdownCard'
import ErrorCard from '../Cards/ErrorCard'
import HoldingsCard from '../Cards/HoldingsCard'
import MorningBriefCard from '../Cards/MorningBriefCard'

export default function Message({ message }) {
  const { role, text, cardType, data } = message

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg bg-elevated border border-border rounded-xl px-4 py-2.5
                        text-text text-sm font-mono">
          {text}
        </div>
      </div>
    )
  }

  if (role === 'error') {
    return <ErrorCard text={text} />
  }

  // Assistant cards
  switch (cardType) {
    case 'quote':        return <QuoteCard data={data} />
    case 'holdings':     return <HoldingsCard data={data} />
    case 'morning_brief':return <MorningBriefCard data={data} />
    case 'markdown':
    default:
      return <MarkdownCard data={data} />
  }
}
