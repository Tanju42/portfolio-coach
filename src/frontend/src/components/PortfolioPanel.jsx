import React, { useEffect, useState } from 'react'
import { fetchPortfolios } from '../api.js'
import { DonutChart, donutSlices } from './Charts.jsx'
import HistorySection from './HistorySection.jsx'
import AssetDetail from './AssetDetail.jsx'
import AllocationSection from './AllocationSection.jsx'
import RiskSection from './RiskSection.jsx'
import WatchlistSection from './WatchlistSection.jsx'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function ReliabilityBadge({ share }) {
  const percent = Math.round((share || 0) * 100)
  const label = percent >= 90 ? 'verified' : percent >= 50 ? 'partial' : 'unknown'
  return <span className={`badge ${label}`} title="How much of the cost basis comes from your imported history">{percent}% basis</span>
}

const STATUS_LABELS = {
  ok: 'connected',
  error: 'error',
  not_connected: 'not connected',
}

function ProviderCard({ block }) {
  const statusClass = block.status === 'ok' ? 'ok' : block.status === 'error' ? 'error' : ''
  return (
    <div className={`provider-card ${statusClass}`}>
      <div className="provider-head">
        <span className="provider-name">{block.label}</span>
        <span className={`status-badge ${statusClass}`}>{STATUS_LABELS[block.status] || block.status}</span>
      </div>
      <div className="provider-kv">
        <span className="kind-chip">{block.kind}</span>
        <span className="provider-value">{block.status === 'ok' ? money(block.total_value_usd) : '—'}</span>
      </div>
      {block.status === 'ok' ? (
        <>
          <div className={`provider-pnl ${block.total_pnl_usd >= 0 ? 'pos' : 'neg'}`}>
            {block.total_pnl_usd >= 0 ? '+' : ''}{money(block.total_pnl_usd)} P&amp;L · {block.asset_count} assets
          </div>
          <ul className="provider-top">
            {block.rows.slice(0, 3).map((row) => (
              <li key={row.asset}>
                <span>{row.asset}</span>
                <span>{money(row.value_usd)}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="note">{block.error}</p>
      )}
    </div>
  )
}

export default function PortfolioPanel({ registerRefresh }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [sortKey, setSortKey] = useState('value_usd')
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      setData(await fetchPortfolios())
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

  if (loading && !data) {
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
  if (!data) return null

  const totals = data.totals
  const filters = data.portfolios
    .filter((block) => block.status === 'ok')
    .map((block) => block.provider + ':' + block.label)
  const activeLabel = filter === 'all' ? null : filter.split(':')[1]
  const rows = data.rows
    .filter((row) => activeLabel === null || row.providers.some((p) => p.label === activeLabel))
    .sort((a, b) => (b[sortKey] || 0) - (a[sortKey] || 0))
  const pnlClass = totals.total_pnl_usd >= 0 ? 'pos' : 'neg'
  const connected = data.portfolios.filter((block) => block.status === 'ok').length

  return (
    <section className="panel">
      <div className="summary-grid">
        <div className="stat-card">
          <div className="label">Total across {connected} portfolios</div>
          <div className="big">{money(totals.total_value_usd)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Cost basis (est.)</div>
          <div className="big">{money(totals.total_cost_usd)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Unrealized P&amp;L</div>
          <div className={`big ${pnlClass}`}>
            {totals.total_pnl_usd >= 0 ? '+' : ''}{money(totals.total_pnl_usd)}
          </div>
          <div className={`sub ${pnlClass}`}>
            {totals.total_cost_usd > 0
              ? `${((totals.total_pnl_usd / totals.total_cost_usd) * 100).toFixed(1)}% on basis`
              : '—'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Assets</div>
          <div className="big">{totals.asset_count}</div>
          <div className="sub">across all providers</div>
        </div>
      </div>

      <div className="provider-cards">
        {data.portfolios.map((block, index) => (
          <ProviderCard key={`${block.provider}-${index}`} block={block} />
        ))}
      </div>

      <HistorySection fetchedAt={data.fetched_at} />

      <div className="filter-row">
        <button className={`filter-chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>
          All
        </button>
        {filters.map((item) => (
          <button
            key={item}
            className={`filter-chip ${filter === item ? 'active' : ''}`}
            onClick={() => setFilter(item)}
          >
            {item.split(':')[1]}
          </button>
        ))}
      </div>

      <div className="portfolio-columns">
        <DonutChart slices={donutSlices(rows)} centerLabel="total" centerValue={money(totals.total_value_usd)} />
        <div className="table-scroll">
          <table className="portfolio-table">
            <thead>
              <tr>
                <th onClick={() => setSortKey('asset')}>Asset</th>
                <th onClick={() => setSortKey('value_usd')}>Value</th>
                <th>24h</th>
                <th onClick={() => setSortKey('pnl_usd')}>P&amp;L</th>
                <th>Share</th>
                <th>Providers</th>
                <th onClick={() => setSortKey('basis_reliable_share')}>Basis</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const share = totals.total_value_usd > 0 ? row.value_usd / totals.total_value_usd : 0
                return (
                  <tr
                    key={row.asset}
                    className="asset-row"
                    onClick={() => setSelected(selected === row.asset ? null : row.asset)}
                  >
                    <td>
                      <span className="asset-cell">{row.asset}</span>
                    </td>
                    <td>{money(row.value_usd)}</td>
                    <td className={(row.change_24h_pct || 0) >= 0 ? 'pos' : 'neg'}>
                      {row.change_24h_pct != null
                        ? `${row.change_24h_pct > 0 ? '+' : ''}${row.change_24h_pct}%`
                        : '—'}
                    </td>
                    <td className={row.pnl_usd >= 0 ? 'pos' : 'neg'}>
                      {row.pnl_usd >= 0 ? '+' : ''}{money(row.pnl_usd)}
                    </td>
                    <td>
                      <div className="share-bar"><div className="share-fill" style={{ width: `${Math.round(share * 100)}%` }} /></div>
                      <span className="share-text">{Math.round(share * 100)}%</span>
                    </td>
                    <td>
                      <span className="provider-badges">
                        {row.providers.map((p) => (
                          <span key={p.provider} className="provider-badge" title={`${p.label}: ${p.qty}`}>{p.label.split(' ')[0]}</span>
                        ))}
                      </span>
                    </td>
                    <td><ReliabilityBadge share={row.basis_reliable_share} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p className="note">Tap an asset for its detail view.</p>
        </div>
      </div>

      {selected && <AssetDetail asset={selected} onClose={() => setSelected(null)} />}

      <AllocationSection />
      <RiskSection />
      <WatchlistSection />

      <div className="provider-footer">
        <span className="label">Providers</span>
        <div className="provider-footer-list">
          {data.providers.map((provider) => (
            <span key={provider.name} className={`status-badge ${provider.connected ? 'ok' : ''}`}>
              {provider.name}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
