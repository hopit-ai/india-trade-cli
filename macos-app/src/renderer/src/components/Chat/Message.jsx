import QuoteCard from '../Cards/QuoteCard'
import AnalysisCard from '../Cards/AnalysisCard'
import StreamingAnalysisCard from '../Cards/StreamingAnalysisCard'
import BacktestCard from '../Cards/BacktestCard'
import FlowsCard from '../Cards/FlowsCard'
import MorningBriefCard from '../Cards/MorningBriefCard'
import HoldingsCard from '../Cards/HoldingsCard'
import MarkdownCard from '../Cards/MarkdownCard'
import ErrorCard from '../Cards/ErrorCard'

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

  if (role === 'error') return <ErrorCard text={text} />

  switch (cardType) {
    case 'quote':              return <QuoteCard data={data} />
    case 'analysis':           return <AnalysisCard data={data} />
    case 'streaming_analysis': return <StreamingAnalysisCard data={data} />
    case 'backtest':           return <BacktestCard data={data} />
    case 'flows':              return <FlowsCard data={data} />
    case 'morning_brief':      return <MorningBriefCard data={data} />
    case 'holdings':           return <HoldingsCard data={data} />
    case 'markdown':
    default:                   return <MarkdownCard data={data} />
  }
}
