/**
 * MarkdownCard
 *
 * Renders markdown-ish text responses from the chat/skills endpoints.
 * Handles the subset produced by the AI: ## headers, **bold**, - bullets, \n line breaks.
 * No external dependency needed.
 */

// Extract text from various response shapes
function extractText(data) {
  if (typeof data === 'string') return data
  // Chat endpoint returns { response, session_id, history_length }
  if (data?.response) return data.response
  if (data?.text)     return data.text
  if (data?.result)   return data.result
  return JSON.stringify(data, null, 2)
}

// Render inline markdown: **bold**, *italic*, and `code`
function renderInline(text) {
  const parts = []
  const re    = /\*\*(.+?)\*\*|`(.+?)`|(?<!\*)\*([^*]+?)\*(?!\*)/g
  let last    = 0
  let match

  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    if (match[1] != null) parts.push(<strong key={match.index} className="font-semibold text-text">{match[1]}</strong>)
    if (match[2] != null) parts.push(<code key={match.index} className="font-mono text-amber bg-panel px-1 rounded text-[10px]">{match[2]}</code>)
    if (match[3] != null) parts.push(<em key={match.index} className="italic text-text">{match[3]}</em>)
    last = re.lastIndex
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function renderBlock(line, idx) {
  // H2 / H3
  if (line.startsWith('### ')) {
    return (
      <h3 key={idx} className="text-text text-[12px] font-semibold font-ui mt-3 mb-1 uppercase tracking-wide text-muted">
        {renderInline(line.slice(4))}
      </h3>
    )
  }
  if (line.startsWith('## ')) {
    return (
      <h2 key={idx} className="text-text text-[14px] font-bold font-ui mt-4 mb-1.5">
        {renderInline(line.slice(3))}
      </h2>
    )
  }
  if (line.startsWith('# ')) {
    return (
      <h1 key={idx} className="text-text text-[16px] font-bold font-ui mt-4 mb-2">
        {renderInline(line.slice(2))}
      </h1>
    )
  }
  // Horizontal rule
  if (/^---+$/.test(line.trim())) {
    return <hr key={idx} className="border-border my-3" />
  }
  // Bullet
  if (line.startsWith('- ') || line.startsWith('* ')) {
    return (
      <li key={idx} className="flex gap-2 text-text text-[13px] font-ui leading-relaxed">
        <span className="text-muted flex-shrink-0 mt-0.5">·</span>
        <span>{renderInline(line.slice(2))}</span>
      </li>
    )
  }
  // Empty line → spacer
  if (line.trim() === '') {
    return <div key={idx} className="h-2" />
  }
  // Normal paragraph line
  return (
    <p key={idx} className="text-text text-[13px] font-ui leading-relaxed">
      {renderInline(line)}
    </p>
  )
}

export default function MarkdownCard({ data }) {
  const raw   = extractText(data)
  // Normalise \n escape sequences that some endpoints send as literal strings
  const text  = raw.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
  const lines = text.split('\n')

  // Process lines: merge code blocks (``` ... ```) into single elements
  const elements = []
  let i = 0
  while (i < lines.length) {
    if (lines[i].trimStart().startsWith('```')) {
      // Collect code block lines
      const codeLines = []
      i++ // skip opening ```
      while (i < lines.length && !lines[i].trimStart().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      i++ // skip closing ```
      elements.push(
        <pre key={`code-${i}`} className="font-mono text-[11px] text-amber bg-panel rounded px-3 py-2 overflow-x-auto my-2 whitespace-pre-wrap">
          {codeLines.join('\n')}
        </pre>
      )
    } else {
      // Check for numbered list items (e.g. "1. Item")
      const numMatch = lines[i].match(/^(\d+)\.\s+(.*)/)
      if (numMatch) {
        elements.push(
          <li key={i} className="flex gap-2 text-text text-[13px] font-ui leading-relaxed">
            <span className="text-muted flex-shrink-0 mt-0.5">{numMatch[1]}.</span>
            <span>{renderInline(numMatch[2])}</span>
          </li>
        )
      } else {
        elements.push(renderBlock(lines[i], i))
      }
      i++
    }
  }

  return (
    <div className="bg-elevated border border-border rounded-xl px-5 py-4 max-w-2xl w-full">
      <ul className="list-none space-y-0.5">
        {elements}
      </ul>
    </div>
  )
}
