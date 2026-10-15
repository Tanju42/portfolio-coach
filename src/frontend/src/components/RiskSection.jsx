import { useEffect, useState } from 'react'
import { fetchRisk } from '../api.js'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

const CATEGORY_COLORS = { stables: '#3fb950', major: '#4f8ef7', alt: '#d29922', meme: '#f778ba', stocks: '#8957e5' }

export default function RiskSection() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchRisk()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="portfolio-section">
      <h3>Risk &amp; Exposure</h3>
      {error && <p className="error">{error}</p>}
      {!data && !error && <div className="skeleton table-skeleton" />}
      {data && (
        <>
          <div className="risk-score-row">
            <div className={`risk-score ${data.score >= 70 ? 'pos' : data.score >= 45 ? '' : 'neg'}`}>
              {data.score ?? '—'}
            </div>
            <div>
              <div className="label">Risk score (0–100)</div>
              <div className="note">0 = very risky, 100 = conservative. Based on concentration, cash buffer, category mix and basis quality.</div>
            </div>
          </div>
          <div className="exposure-bars">
            {data.exposure.map((item) => (
              <div key={item.category} className="exposure-row">
                <span className="exposure-name">{item.category}</span>
                <div className="share-bar">
                  <div
                    className="share-fill"
                    style={{ width: `${item.weight_pct}%`, background: CATEGORY_COLORS[item.category] || '#3a4454' }}
                  />
                </div>
                <span className="share-text">{item.weight_pct}% · {money(item.value_usd)}</span>
              </div>
            ))}
          </div>
          <div className="risk-facts">
            <span>Top: {data.top_asset} {data.top_share_pct}%</span>
            <span>Stables: {data.stables_share_pct}%</span>
            <span>Meme: {data.meme_share_pct}%</span>
            <span>Assets: {data.asset_count}</span>
            <span>Basis: {data.basis_reliability_pct}%</span>
            <span className={data.unrealized_pnl_usd >= 0 ? 'pos' : 'neg'}>
              Unrealized: {data.unrealized_pnl_usd >= 0 ? '+' : ''}{money(data.unrealized_pnl_usd)}
            </span>
          </div>
          <ul className="warning-list">
            {data.warnings.map((warning, index) => (
              <li key={index} className={warning.startsWith('no risk flags') ? 'ok' : 'warn'}>{warning}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
