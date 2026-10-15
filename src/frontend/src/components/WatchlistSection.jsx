import { useEffect, useState } from 'react'
import { addWatch, fetchWatchlist, removeWatch } from '../api.js'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })}`
}

export default function WatchlistSection() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [symbol, setSymbol] = useState('')
  const [kind, setKind] = useState('crypto')
  const [busy, setBusy] = useState(false)

  async function load() {
    try {
      setItems((await fetchWatchlist()).watchlist)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function submit(event) {
    event.preventDefault()
    const clean = symbol.trim().toUpperCase()
    if (!clean) return
    setBusy(true)
    setError(null)
    try {
      await addWatch(clean, kind)
      setSymbol('')
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function drop(item) {
    setBusy(true)
    try {
      await removeWatch(item.symbol)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="portfolio-section">
      <h3>Watchlist</h3>
      {error && <p className="error">{error}</p>}
      {items && items.length === 0 && <p className="note">Nothing tracked yet. Add a symbol to follow its price.</p>}
      {items && items.length > 0 && (
        <table className="mini-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Kind</th>
              <th>Price</th>
              <th>24h</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol}>
                <td>{item.symbol}</td>
                <td><span className="kind-chip">{item.kind}</span></td>
                <td>{item.price_usd ? money(item.price_usd) : '—'}</td>
                <td className={(item.change_24h_pct || 0) >= 0 ? 'pos' : 'neg'}>
                  {item.change_24h_pct != null ? `${item.change_24h_pct > 0 ? '+' : ''}${item.change_24h_pct}%` : '—'}
                </td>
                <td>
                  <button className="remove-btn" disabled={busy} onClick={() => drop(item)} aria-label={`Remove ${item.symbol}`}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form className="watch-form" onSubmit={submit}>
        <input
          value={symbol}
          placeholder="e.g. SOL or SAP.DE"
          onChange={(event) => setSymbol(event.target.value)}
          aria-label="Symbol"
        />
        <select value={kind} onChange={(event) => setKind(event.target.value)} aria-label="Kind">
          <option value="crypto">crypto</option>
          <option value="stocks">stock</option>
        </select>
        <button type="submit" disabled={busy || !symbol.trim()}>Add</button>
      </form>
    </div>
  )
}
