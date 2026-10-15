import React, { useEffect, useState } from 'react'
import { fetchMarket, fetchSettings, setAccountMode } from '../api.js'

function fngColor(value) {
  if (value <= 24) return { color: 'var(--red)', label: 'extreme fear' }
  if (value <= 44) return { color: 'var(--amber)', label: 'fear' }
  if (value <= 55) return { color: 'var(--amber)', label: 'neutral' }
  if (value <= 75) return { color: 'var(--green)', label: 'greed' }
  return { color: 'var(--green)', label: 'extreme greed' }
}

function bigMoney(value) {
  const num = Number(value || 0)
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
  if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
  return `$${(num / 1e6).toFixed(1)}M`
}

function MoverRow({ mover }) {
  const pct = mover.change_24h_pct
  return (
    <li className="mover-row">
      <span className="mover-sym">{mover.symbol}</span>
      <span className="mover-name">{mover.name}</span>
      <span className="mover-price">${mover.price_usd?.toLocaleString('en-US')}</span>
      <span className={pct >= 0 ? 'pos' : 'neg'}>
        {pct >= 0 ? '+' : ''}{pct?.toFixed(1)}%
      </span>
    </li>
  )
}

function ModeToggle({ settings, onChanged }) {
  const [busy, setBusy] = useState(false)
  if (!settings) return null
  const mode = settings.account_mode
  async function switchTo(next) {
    if (next === mode || busy) return
    setBusy(true)
    try {
      await setAccountMode(next)
      onChanged?.(next)
    } catch (err) {
      alert(err.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="mode-seg" role="radiogroup" aria-label="Account mode">
      <button className={mode === 'demo' ? 'seg active' : 'seg'} disabled={busy} onClick={() => switchTo('demo')}>Demo</button>
      <button
        className={mode === 'live' ? 'seg active' : 'seg'}
        disabled={busy || !settings.has_live_keys}
        onClick={() => switchTo('live')}
        title={settings.has_live_keys ? 'Your read-only Binance account' : 'Add read-only Binance keys in the backend .env first'}
      >
        Live
      </button>
    </div>
  )
}

export default function MarketPanel({ registerRefresh }) {
  const [market, setMarket] = useState(null)
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const [data, cfg] = await Promise.all([fetchMarket(), fetchSettings()])
      setMarket(data)
      setSettings(cfg)
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

  if (loading && !market) {
    return (
      <section className="panel">
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
        <div className="skeleton table-skeleton" />
      </section>
    )
  }
  if (error) return <section className="panel"><p className="error">{error}</p></section>
  if (!market || market.error) {
    return <section className="panel"><p className="error">{market?.error || 'Market data unavailable'}</p></section>
  }

  const fng = market.fear_greed?.current
  const fngMeta = fng ? fngColor(fng.value) : null
  const globalData = market.global
  const gainers = market.movers?.gainers || []
  const losers = market.movers?.losers || []
  const news = market.news?.news || []

  return (
    <section className="panel">
      <div className="market-header">
        <h2>Market</h2>
        <ModeToggle settings={settings} onChanged={(mode) => setSettings((prev) => ({ ...prev, account_mode: mode }))} />
      </div>

      {fng && (
        <div className="fng-card">
          <div className="fng-left">
            <div className="fng-number" style={{ color: fngMeta.color }}>{fng.value}</div>
            <div className="fng-caption">Fear &amp; Greed Index</div>
          </div>
          <div className="fng-right">
            <span className="fng-label" style={{ background: `${fngMeta.color}22`, color: fngMeta.color }}>{fng.label}</span>
            <div className="fng-bar">
              <div className="fng-fill" style={{ width: `${fng.value}%`, background: fngMeta.color }} />
            </div>
          </div>
        </div>
      )}

      {globalData && !globalData.error && (
        <div className="market-stats">
          <div><span className="label">Total cap</span><span className="value">{bigMoney(globalData.total_market_cap_usd)}</span></div>
          <div><span className="label">24h vol</span><span className="value">{bigMoney(globalData.total_volume_24h_usd)}</span></div>
          <div><span className="label">BTC dom.</span><span className="value">{globalData.btc_dominance_pct?.toFixed(1)}%</span></div>
          <div><span className="label">Coins</span><span className="value">{globalData.active_coins?.toLocaleString('en-US')}</span></div>
        </div>
      )}

      <div className="movers-grid">
        <div>
          <h3>Top gainers 24h</h3>
          <ul className="movers">{gainers.map((mover) => <MoverRow key={mover.symbol} mover={mover} />)}</ul>
        </div>
        <div>
          <h3>Top losers 24h</h3>
          <ul className="movers">{losers.map((mover) => <MoverRow key={mover.symbol} mover={mover} />)}</ul>
        </div>
      </div>

      <h3>Latest news</h3>
      <ul className="news-list">
        {news.map((item, index) => (
          <li key={index} className="news-item">
            <a href={item.link} target="_blank" rel="noreferrer">{item.title}</a>
            <span className="news-source">{item.source}</span>
          </li>
        ))}
      </ul>
      <p className="note">Data: CoinGecko, alternative.me, RSS feeds — fetched live, cached 60s.</p>
    </section>
  )
}
