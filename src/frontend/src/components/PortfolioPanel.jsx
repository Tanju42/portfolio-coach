import React, { useEffect, useState } from 'react'
import { fetchPortfolio } from '../api.js'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function ReliabilityBadge({ share }) {
  const percent = Math.round((share || 0) * 100)
  const label = percent >= 90 ? 'reliable' : percent >= 50 ? 'partial' : 'unknown'
  return <span className={`badge ${label}`}>{percent}% basis</span>
}

export default function PortfolioPanel({ portfolio, setPortfolio, registerRefresh }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      setPortfolio(await fetchPortfolio())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    if (registerRefresh) registerRefresh.current = refresh
  }, [])

  if (loading && !portfolio) return <section className="panel"><p>Loading portfolio…</p></section>
  if (error) return <section className="panel"><p className="error">{error}</p></section>
  if (!portfolio) return null
  if (portfolio.error) {
    return (
      <section className="panel">
        <h2>Portfolio</h2>
        <p className="error">{portfolio.error}</p>
      </section>
    )
  }

  const pnlClass = portfolio.total_pnl_usd >= 0 ? 'pos' : 'neg'
  return (
    <section className="panel">
      <div className="portfolio-summary">
        <div>
          <div className="label">Total value</div>
          <div className="big">{money(portfolio.total_value_usd)}</div>
        </div>
        <div>
          <div className="label">Cost basis (est.)</div>
          <div className="big">{money(portfolio.total_cost_usd)}</div>
        </div>
        <div>
          <div className="label">Unrealized P&amp;L</div>
          <div className={`big ${pnlClass}`}>
            {portfolio.total_pnl_usd >= 0 ? '+' : ''}{money(portfolio.total_pnl_usd)}
          </div>
        </div>
      </div>
      <table className="portfolio-table">
        <thead>
          <tr>
            <th>Asset</th><th>Qty</th><th>Price</th><th>Value</th>
            <th>Avg cost</th><th>Cost</th><th>P&amp;L</th><th>Basis</th>
          </tr>
        </thead>
        <tbody>
          {portfolio.rows.map((row) => (
            <tr key={row.asset}>
              <td>{row.asset}</td>
              <td>{row.qty.toFixed(4)}</td>
              <td>{row.price_usd ? `$${row.price_usd.toFixed(2)}` : '—'}</td>
              <td>{money(row.value_usd)}</td>
              <td>{row.avg_cost_usd ? `$${row.avg_cost_usd.toFixed(4)}` : '—'}</td>
              <td>{money(row.cost_usd)}</td>
              <td className={row.pnl_usd >= 0 ? 'pos' : 'neg'}>
                {row.pnl_usd >= 0 ? '+' : ''}{money(row.pnl_usd)}
              </td>
              <td><ReliabilityBadge share={row.basis_reliable_share} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">{portfolio.note}</p>
    </section>
  )
}
