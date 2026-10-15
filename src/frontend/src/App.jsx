import React, { useEffect, useRef, useState } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import PortfolioPanel from './components/PortfolioPanel.jsx'
import ImportPanel from './components/ImportPanel.jsx'

const TABS = [
  { id: 'chat', label: 'Chat' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'import', label: 'Import' },
]

export default function App() {
  const [tab, setTab] = useState('chat')
  const [beginnerMode, setBeginnerMode] = useState(true)
  const [sessionId] = useState(() => `s-${Math.random().toString(36).slice(2, 10)}`)
  const [portfolio, setPortfolio] = useState(null)
  const refreshPortfolio = useRef(null)

  useEffect(() => {
    if (refreshPortfolio.current) refreshPortfolio.current()
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">PC</span>
          <span className="brand-name">Portfolio Coach</span>
          <span className="brand-sub">educational support — you decide</span>
        </div>
        <label className="mode-toggle">
          <input
            type="checkbox"
            checked={beginnerMode}
            onChange={(event) => setBeginnerMode(event.target.checked)}
          />
          Beginner mode
        </label>
      </header>
      <nav className="tabs">
        {TABS.map((item) => (
          <button
            key={item.id}
            className={tab === item.id ? 'tab active' : 'tab'}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
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
  )
}
