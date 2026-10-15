import React from 'react'

const PATTERNS = {
  bold: /\*\*([^*]+)\*\*/g,
  italic: /(^|\s)\*([^*]+)\*/g,
  code: /`([^`]+)`/g,
}

function renderInline(text, keyPrefix) {
  let parts = [{ type: 'text', value: text }]
  for (const [name, pattern] of Object.entries(PATTERNS)) {
    parts = parts.flatMap((part) => {
      if (part.type !== 'text') return [part]
      const out = []
      let last = 0
      const re = new RegExp(pattern.source, pattern.flags)
      let match
      while ((match = re.exec(part.value)) !== null) {
        if (match.index > last) out.push({ type: 'text', value: part.value.slice(last, match.index) })
        out.push({ type: name, value: name === 'code' ? match[1] : match[2] ?? match[1] })
        last = match.index + match[0].length
        if (re.lastIndex === 0) break
      }
      if (last < part.value.length) out.push({ type: 'text', value: part.value.slice(last) })
      return out
    })
  }
  return parts.map((part, index) => {
    if (part.type === 'text') return part.value
    if (part.type === 'bold') return <strong key={`${keyPrefix}-${index}`}>{part.value}</strong>
    if (part.type === 'italic') return <em key={`${keyPrefix}-${index}`}>{part.value}</em>
    return <code key={`${keyPrefix}-${index}`}>{part.value}</code>
  })
}

export default function Markdown({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  const blocks = []
  let listItems = null
  let listOrdered = false

  const flushList = () => {
    if (listItems) {
      blocks.push(listOrdered ? <ol key={blocks.length}>{listItems}</ol> : <ul key={blocks.length}>{listItems}</ul>)
      listItems = null
    }
  }

  for (const [index, raw] of lines.entries()) {
    const line = raw.trimEnd()
    if (!line.trim()) { flushList(); continue }
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/)
    if (bullet || numbered) {
      if (!listItems || (numbered ? !listOrdered : listOrdered)) { flushList(); listItems = []; listOrdered = Boolean(numbered) }
      listItems.push(<li key={index}>{renderInline((bullet || numbered)[1], `l${index}`)}</li>)
      continue
    }
    flushList()
    const heading = line.match(/^#{1,3}\s+(.*)$/)
    if (heading) {
      blocks.push(<h4 key={blocks.length}>{renderInline(heading[1], `h${index}`)}</h4>)
      continue
    }
    blocks.push(<p key={blocks.length}>{renderInline(line, `p${index}`)}</p>)
  }
  flushList()
  return <div className="markdown">{blocks}</div>
}
