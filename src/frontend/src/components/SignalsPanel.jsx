import React, { useEffect, useState } from 'react'
import { fetchSignals } from '../api.js'

const LIGHT = { BUY: 'buy', SELL: 'sell', HOLD: 'hold' }

export default function SignalsPanel() {
  const [signals, setSignals] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSignals()
      .then((data) => setSignals(data.signals))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <section className="panel">
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
      </section>
    )
  }
  if (error) return <section className="panel"><p className="error">{error}</p></section>
  if (!signals?.length) {
    return (
      <section className="panel">
        <h2>Signal history</h2>
        <p className="lead">No signals yet. Ask the Coach for a BUY / SELL / HOLD recommendation — every structured signal is saved here.</p>
      </section>
    )
  }

  return (
    <section className="panel">
      <h2>Signal history</h2>
      <ul className="signal-history">
        {signals.map((signal) => (
          <li key={signal.id} className={`signal-item ${LIGHT[signal.action] || 'hold'}`}>
            <div className="signal-item-head">
              <span className={`traffic-light ${LIGHT[signal.action]}`}>{signal.action}</span>
              <span className="symbol">{signal.symbol.replace(/USDT$/, '')}</span>
              <span className={`risk-chip ${signal.risk_level}`}>{signal.risk_level}</span>
              <span className="signal-time">{signal.created_at}</span>
            </div>
            <div className="signal-item-headline">{signal.headline}</div>
            <div className="signal-item-confidence">{signal.confidence}% confidence</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
