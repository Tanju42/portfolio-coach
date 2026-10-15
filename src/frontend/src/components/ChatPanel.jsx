import React, { useEffect, useRef, useState } from 'react'
import { sendChat } from '../api.js'

const LIGHT = { BUY: 'buy', SELL: 'sell', HOLD: 'hold' }

function SignalCard({ signal }) {
  if (!signal) return null
  return (
    <div className={`signal-card ${LIGHT[signal.action] || 'hold'}`}>
      <div className="signal-head">
        <span className="traffic-light">{signal.action}</span>
        <span className="symbol">{signal.symbol}</span>
        <span className="confidence">{signal.confidence}% confidence</span>
      </div>
      <div className="signal-risk">Risk: {signal.risk_level}</div>
      <div className="signal-headline">{signal.headline}</div>
      <ul className="signal-rationale">
        {signal.rationale.map((reason, index) => (
          <li key={index}>{reason}</li>
        ))}
      </ul>
      <div className="signal-beginner">{signal.beginner_explanation}</div>
      <div className="signal-disclaimer">{signal.disclaimer}</div>
    </div>
  )
}

export default function ChatPanel({ sessionId, beginnerMode, onSignal }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const listEnd = useRef(null)

  useEffect(() => {
    listEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function submit(event) {
    event.preventDefault()
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setBusy(true)
    setError(null)
    try {
      const reply = await sendChat(text, sessionId, beginnerMode)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply.content, signal: reply.signal, tools: reply.tools_used },
      ])
      if (reply.signal) onSignal()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="chat-panel">
      <div className="messages">
        {messages.length === 0 && (
          <div className="empty">
            <h2>Ask anything about your portfolio.</h2>
            <p>Try: “How is my portfolio doing?” or “Should I sell my SOL?”</p>
          </div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="bubble">
              {message.content}
              {message.tools?.length > 0 && (
                <div className="tools-used">
                  {message.tools.length} tool call{message.tools.length === 1 ? '' : 's'}
                </div>
              )}
            </div>
            {message.role === 'assistant' && <SignalCard signal={message.signal} />}
          </div>
        ))}
        {busy && <div className="message assistant"><div className="bubble thinking">Thinking…</div></div>}
        {error && <div className="error">{error}</div>}
        <div ref={listEnd} />
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask your coach…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>Send</button>
      </form>
    </section>
  )
}
