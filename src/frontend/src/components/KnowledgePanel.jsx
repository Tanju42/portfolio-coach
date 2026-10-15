import React, { useEffect, useRef, useState } from 'react'
import { fetchKnowledge, researchKnowledge } from '../api.js'

const CONFIDENCE = { low: 'unknown', medium: 'partial', high: 'verified' }

function KnowledgeCard({ item }) {
  return (
    <div className="knowledge-card">
      <div className="knowledge-head">
        <span className="knowledge-topic">{item.topic}</span>
        <span className={`badge ${CONFIDENCE[item.confidence] || 'unknown'}`}>{item.confidence} confidence</span>
      </div>
      <p className="knowledge-summary">{item.summary}</p>
      {item.key_points?.length > 0 && (
        <ul className="knowledge-points">
          {item.key_points.map((point, index) => <li key={index}>{point}</li>)}
        </ul>
      )}
      {item.sources?.length > 0 && (
        <div className="knowledge-sources">
          <span className="label">Sources:</span>
          <ul>
            {item.sources.map((source, index) => (
              <li key={index}>
                {source.url && source.url.startsWith('http')
                  ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                  : <span>{source.title}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="knowledge-date">{item.created_at}</div>
    </div>
  )
}

export default function KnowledgePanel() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [topic, setTopic] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)

  async function refresh() {
    try {
      const data = await fetchKnowledge()
      setItems(data.knowledge)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { refresh() }, [])

  async function startResearch(event) {
    event.preventDefault()
    const text = topic.trim()
    if (!text || busy) return
    setBusy(true)
    setError(null)
    setStatus('Researching with the agent — this can take a few minutes…')
    try {
      const result = await researchKnowledge(text)
      if (result.saved) {
        setStatus('Saved to your knowledge base ✓')
        setTopic('')
        await refresh()
      } else {
        setError(result.content)
      }
    } catch (err) {
      setError(err.message)
      setStatus(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Knowledge</h2>
      <p className="lead">
        Ask the coach to research anything about your holdings — it searches the web,
        cross-checks market data and saves the insight with sources here.
      </p>
      <form className="composer research-composer" onSubmit={startResearch}>
        <div className="composer-row">
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="e.g. NVIDIA outlook, SOL vs ETH, Fed rate impact"
            disabled={busy}
          />
          <button type="submit" disabled={busy || !topic.trim()} aria-label="Research">
            {busy ? '…' : 'Go'}
          </button>
        </div>
      </form>
      {status && <p className="note">{status}</p>}
      {error && <p className="error">{error}</p>}

      {items === null && !error && <div className="skeleton table-skeleton" />}
      {items?.length === 0 && (
        <p className="note">Nothing saved yet — research your first topic above.</p>
      )}
      <div className="knowledge-list">
        {items?.map((item) => <KnowledgeCard key={item.id} item={item} />)}
      </div>
    </section>
  )
}
