import React, { useEffect, useState } from 'react'
import { fetchPortfolio } from '../api.js'
import { DonutChart, donutSlices } from './Charts.jsx'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function ReliabilityBadge({ share }) {
  const percent = Math.round((share || 0) * 100)
  const label = percent >= 90 ? 'verified' : percent >= 50 ? 'partial' : 'unknown'
  return <span className={`badge ${label}`} title="How much of the cost basis comes from your imported history">{percent}% basis</span>
}

export default function PortfolioPanel({ portfolio, setPortfolio, registerRefresh }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sortKey, setSortKey] = useState('value_usd')

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

  if (loading && !portfolio) {
    return (
      <section className="panel">
        <div className="skeleton summary-skeleton" />
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
      </section>
    )
  }
  if (error) return <section className="panel"><p className="error">{error}</p></section>
  if (!portfolio) return null
  if (portfolio.error) {
    return (
      <section className="panel">
        <h2>Portfolio</h2>
        <p className="error">{portfolio.error}</p>
        <p className="note">Connect your read-only Binance API keys in the backend .env, or import your transaction history on the Import tab.</p>
      </section>
    )
  }

  const rows = [...portfolio.rows].sort((a, b) => (b[sortKey] || 0) - (a[sortKey] || 0))
  const pnlClass = portfolio.total_pnl_usd >= 0 ? 'pos' : 'neg'
  const topAsset = rows[0]
  const topShare = topAsset && portfolio.total_value_usd > 0 ? topAsset.value_usd / portfolio.total_value_usd : 0

  return (
    <section className="panel">
      <div className="summary-grid">
        <div className="stat-card">
          <div className="label">Total value</div>
          <div className="big">{money(portfolio.total_value_usd)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Cost basis (est.)</div>
          <div className="big">{money(portfolio.total_cost_usd)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Unrealized P&amp;L</div>
          <div className={`big ${pnlClass}`}>
            {portfolio.total_pnl_usd >= 0 ? '+' : ''}{money(portfolio.total_pnl_usd)}
          </div>
          <div className={`sub ${pnlClass}`}>
            {portfolio.total_cost_usd > 0
              ? `${((portfolio.total_pnl_usd / portfolio.total_cost_usd) * 100).toFixed(1)}% on basis`
              : '—'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Concentration</div>
          <div className="big">{Math.round(topShare * 100)}%</div>
          <div className="sub">{topAsset ? `in ${topAsset.asset.replace(/^LD/, '')}` : ''}</div>
        </div>
      </div>

      <div className="portfolio-columns">
        <DonutChart slices={donutSlices(rows)} centerLabel="total" centerValue={money(portfolio.total_value_usd)} />
      <div className="table-scroll">
        <table className="portfolio-table">
          <thead>
            <tr>
              <th onClick={() => setSortKey('asset')}>Asset</th>
              <th onClick={() => setSortKey('value_usd')}>Value</th>
              <th onClick={() => setSortKey('pnl_usd')}>P&amp;L</th>
              <th>Share</th>
              <th>Avg cost</th>
              <th onClick={() => setSortKey('basis_reliable_share')}>Basis</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const share = portfolio.total_value_usd > 0 ? row.value_usd / portfolio.total_value_usd : 0
              return (
                <tr key={row.asset}>
                  <td>
                    <span className="asset-cell">
                      {row.asset.replace(/^LD/, '')}
                      {row.asset.startsWith('LD') && <span className="leveraged" title="2x leveraged earn token">2×</span>}
                    </span>
                  </td>
                  <td>{money(row.value_usd)}</td>
                  <td className={row.pnl_usd >= 0 ? 'pos' : 'neg'}>
                    {row.pnl_usd >= 0 ? '+' : ''}{money(row.pnl_usd)}
                  </td>
                  <td>
                    <div className="share-bar"><div className="share-fill" style={{ width: `${Math.round(share * 100)}%` }} /></div>
                    <span className="share-text">{Math.round(share * 100)}%</span>
                  </td>
                  <td>{row.avg_cost_usd ? `$${row.avg_cost_usd.toFixed(4)}` : '—'}</td>
                  <td><ReliabilityBadge share={row.basis_reliable_share} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      </div>
      <p className="note">{portfolio.note}</p>
    </section>
  )
}
