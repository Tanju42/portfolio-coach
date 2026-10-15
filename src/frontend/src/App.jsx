import React, { useEffect, useRef, useState } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import PortfolioPanel from './components/PortfolioPanel.jsx'
import MarketPanel from './components/MarketPanel.jsx'
import KnowledgePanel from './components/KnowledgePanel.jsx'
import SignalsPanel from './components/SignalsPanel.jsx'
import ImportPanel from './components/ImportPanel.jsx'
import { fetchHealth, fetchPortfolio } from './api.js'

const NAV = [
  { id: 'chat', label: 'Coach', icon: 'M4 5h16v11H7l-3 3V5z' },
  { id: 'portfolio', label: 'Portfolio', icon: 'M12 3a9 9 0 1 0 9 9h-9V3z M14 3a7 7 0 0 1 7 7h-7V3z' },
  { id: 'market', label: 'Market', icon: 'M3 17l6-6 4 4 8-8M16 7h5v5' },
  { id: 'knowledge', label: 'Knowledge', icon: 'M4 19V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zm0 0a2 2 0 0 0 2 2h13' },
  { id: 'signals', label: 'Signals', icon: 'M12 3l10 18H2L12 3z M12 10v5m0 3h.01' },
  { id: 'import', label: 'Import', icon: 'M12 3v10m0 0l-4-4m4 4l4-4M4 17v4h16v-4' },
]

function Icon({ path }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="20" height="20">
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

  const pnl = portfolio?.total_pnl_usd
  const pnlClass = pnl >= 0 ? 'pos' : 'neg'

  return (
    <div className="viewport">
      <div className="phone">
        {!apiOk && <div className="banner">Backend not reachable — is the server running?</div>}
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark">PC</span>
            <div>
              <div className="brand-name">Portfolio Coach</div>
              <div className="brand-sub">you decide, we explain</div>
            </div>
          </div>
          <label className="mode-toggle" aria-label="Toggle beginner mode">
            <span className={`switch ${beginnerMode ? 'on' : ''}`} onClick={() => setBeginnerMode(!beginnerMode)}>
              <span className="knob" />
            </span>
          </label>
        </header>

        {(tab !== 'import') && (
          <div className="value-hero">
            <div className="label">Total value</div>
            <div className="hero-value">{portfolio ? money(portfolio.total_value_usd) : '—'}</div>
            {pnl !== undefined && (
              <div className={`hero-pnl ${pnlClass}`}>
                {pnl >= 0 ? '▲ +' : '▼ '}{money(pnl)} unrealized
              </div>
            )}
          </div>
        )}

        <main className={tab === 'chat' ? 'content chat-view' : 'content'}>
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
          {tab === 'market' && <MarketPanel registerRefresh={refreshPortfolio} />}
          {tab === 'knowledge' && <KnowledgePanel />}
          {tab === 'signals' && <SignalsPanel />}
          {tab === 'import' && <ImportPanel onImported={() => refreshPortfolio.current?.()} />}
        </main>

        <nav className="bottom-nav">
          {NAV.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? 'nav-item active' : 'nav-item'}
              onClick={() => setTab(item.id)}
              aria-label={item.label}
            >
              <Icon path={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>
    </div>
  )
}
