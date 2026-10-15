import React, { useEffect, useRef, useState } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import PortfolioPanel from './components/PortfolioPanel.jsx'
import ImportPanel from './components/ImportPanel.jsx'
import { fetchHealth, fetchPortfolio } from './api.js'

const NAV = [
  { id: 'chat', label: 'Coach', icon: 'M4 5h16v11H7l-3 3V5z' },
  { id: 'portfolio', label: 'Portfolio', icon: 'M12 3a9 9 0 1 0 9 9h-9V3z M14 3a7 7 0 0 1 7 7h-7V3z' },
  { id: 'import', label: 'Import', icon: 'M12 3v10m0 0l-4-4m4 4l4-4M4 17v4h16v-4' },
]

function Icon({ path }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
      <path d={path} />
    </svg>
  )
}

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export default function App() {
  const [tab, setTab] = useState('chat')
  const [beginnerMode, setBeginnerMode] = useState(true)
  const [sessionId] = useState(() => `s-${Math.random().toString(36).slice(2, 10)}`)
  const [portfolio, setPortfolio] = useState(null)
  const [apiOk, setApiOk] = useState(true)
  const refreshPortfolio = useRef(null)

  useEffect(() => {
    fetchHealth().then(() => setApiOk(true)).catch(() => setApiOk(false))
    fetchPortfolio().then(setPortfolio).catch(() => {})
  }, [])

  const pnlClass = portfolio?.total_pnl_usd >= 0 ? 'pos' : 'neg'

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">PC</span>
          <div>
            <div className="brand-name">Portfolio Coach</div>
            <div className="brand-sub">you decide, we explain</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <button key={item.id} className={tab === item.id ? 'nav-item active' : 'nav-item'} onClick={() => setTab(item.id)}>
              <Icon path={item.icon} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-summary">
          <div className="label">Total value</div>
          <div className="value">{portfolio ? money(portfolio.total_value_usd) : '—'}</div>
          <div className={`pnl ${pnlClass}`}>
            {portfolio && portfolio.total_pnl_usd !== undefined
              ? `${portfolio.total_pnl_usd >= 0 ? '+' : ''}${money(portfolio.total_pnl_usd)} unrealized`
              : ''}
          </div>
        </div>
        <label className="mode-toggle">
          <span>Beginner mode</span>
          <span className={`switch ${beginnerMode ? 'on' : ''}`} onClick={() => setBeginnerMode(!beginnerMode)}>
            <span className="knob" />
          </span>
        </label>
      </aside>
      <div className="main">
        {!apiOk && <div className="banner">Backend not reachable — is uvicorn running on port 8000?</div>}
        <main className="content">
          {tab === 'chat' && (
            <ChatPanel
              sessionId={sessionId}
              beginnerMode={beginnerMode}
              onSignal={() => refreshPortfolio.current?.()}
            />
          )}
          {tab === 'portfolio' && (
            <PortfolioPanel portfolio={portfolio} setPortfolio={setPortfolio} registerRefresh={refreshPortfolio} />
          )}
          {tab === 'import' && <ImportPanel onImported={() => refreshPortfolio.current?.()} />}
        </main>
        <footer className="footnote">
          Not financial advice. Trading decisions remain yours. Powered by Nebius Token Factory &amp; NVIDIA open source models.
        </footer>
      </div>
    </div>
  )
}
