import React, { useEffect, useRef, useState } from 'react'
import { sendChat } from '../api.js'
import Markdown from './Markdown.jsx'
import { SignalCard, EmptyChat, ThinkingDots } from './ChatParts.jsx'

export default function ChatPanel({ sessionId, beginnerMode, onSignal }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const listEnd = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    listEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function submit(text) {
    const prompt = (typeof text === 'string' ? text : input).trim()
    if (!prompt || busy) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: prompt }])
    setBusy(true)
    setError(null)
    try {
      const reply = await sendChat(prompt, sessionId, beginnerMode)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply.content, signal: reply.signal, tools: reply.tools_used },
      ])
      if (reply.signal) onSignal()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  return (
    <section className="chat-panel">
      <div className="messages">
        {messages.length === 0 && <EmptyChat onPrompt={submit} />}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="avatar">{message.role === 'user' ? 'You' : 'PC'}</div>
            <div className="message-body">
              {message.role === 'assistant'
                ? <div className="bubble assistant-bubble"><Markdown text={message.content} /></div>
                : <div className="bubble">{message.content}</div>}
              {message.tools?.length > 0 && (
                <div className="tools-used">
                  <span className="tool-dot" />
                  {message.tools.length} tool call{message.tools.length === 1 ? '' : 's'}
                </div>
              )}
              {message.role === 'assistant' && <SignalCard signal={message.signal} />}
            </div>
          </div>
        ))}
        {busy && <ThinkingDots />}
        {error && <div className="error">{error}</div>}
        <div ref={listEnd} />
      </div>
      <form className="composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
        <div className="composer-row">
          <input
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask your coach — e.g. how is my SOL doing?"
            disabled={busy}
          />
          <button type="submit" disabled={busy || !input.trim()} aria-label="Send">➤</button>
        </div>
      </form>
    </section>
  )
}
