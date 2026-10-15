import React from 'react'
import Markdown from './Markdown.jsx'

const LIGHT = { BUY: 'buy', SELL: 'sell', HOLD: 'hold' }

export function SignalCard({ signal }) {
  if (!signal) return null
  const confidence = Math.min(100, Math.max(0, signal.confidence))
  return (
    <div className={`signal-card ${LIGHT[signal.action] || 'hold'}`}>
      <div className="signal-top">
        <span className={`traffic-light ${LIGHT[signal.action]}`}>{signal.action}</span>
        <span className="symbol">{signal.symbol.replace(/USDT$/, '')}</span>
        <span className={`risk-chip ${signal.risk_level}`}>{signal.risk_level} risk</span>
      </div>
      <div className="confidence-bar" aria-label={`confidence ${confidence} percent`}>
        <div className="confidence-fill" style={{ width: `${confidence}%` }} />
      </div>
      <div className="confidence-caption">{confidence}% confidence</div>
      <div className="signal-headline">{signal.headline}</div>
      {signal.rationale?.length > 0 && (
        <ul className="signal-rationale">
          {signal.rationale.map((reason, index) => <li key={index}>{reason}</li>)}
        </ul>
      )}
      <div className="signal-beginner">
        <Markdown text={signal.beginner_explanation} />
      </div>
      <div className="signal-disclaimer">{signal.disclaimer}</div>
    </div>
  )
}

export const SUGGESTIONS = [
  'How is my portfolio doing?',
  'Should I sell my SOL?',
  'What is trending right now?',
  'What is my biggest risk?',
]

export function EmptyChat({ onPrompt }) {
  return (
    <div className="empty-chat">
      <div className="empty-mark">PC</div>
      <h2>Your personal portfolio coach</h2>
      <p>
        Ask anything about your holdings, get beginner-friendly BUY / SELL / HOLD signals
        with reasoning — the decision always stays yours.
      </p>
      <div className="chips">
        {SUGGESTIONS.map((suggestion) => (
          <button key={suggestion} className="chip" onClick={() => onPrompt?.(suggestion)}>{suggestion}</button>
        ))}
      </div>
    </div>
  )
}

export function ThinkingDots() {
  return (
    <div className="message assistant">
      <div className="bubble thinking">
        <span className="dots"><i /><i /><i /></span> Researching with your tools…
      </div>
    </div>
  )
}
