import { useEffect, useState } from 'react'
import { fetchAssetDetail } from '../api.js'
import { Sparkline } from './Charts.jsx'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function AssetDetail({ asset, onClose }) {
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setDetail(null)
    setError(null)
    fetchAssetDetail(asset)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [asset])

  return (
    <div className="asset-detail">
      <div className="asset-detail-head">
        <h3>{asset} <span className="kind-chip">{detail?.kind || '…'}</span></h3>
        <button className="close-btn" onClick={onClose} aria-label="Close detail">✕</button>
      </div>
      {error && <p className="error">{error}</p>}
      {!detail && !error && <div className="skeleton table-skeleton" />}
      {detail && (
        <>
          <div className="detail-grid">
            <div>
              <div className="label">Price</div>
              <div className="big">{detail.price_usd ? money(detail.price_usd) : '—'}</div>
            </div>
            <div>
              <div className="label">Holdings</div>
              <div className="big">{Number(detail.qty).toLocaleString('en-US', { maximumFractionDigits: 8 })}</div>
            </div>
            <div>
              <div className="label">Value</div>
              <div className="big">{money(detail.value_usd)}</div>
            </div>
            <div>
              <div className="label">Avg cost</div>
              <div className="big">{detail.avg_cost_usd ? `$${detail.avg_cost_usd.toFixed(4)}` : '—'}</div>
            </div>
            <div>
              <div className="label">P&amp;L</div>
              <div className={`big ${detail.pnl_usd >= 0 ? 'pos' : 'neg'}`}>
                {detail.pnl_usd >= 0 ? '+' : ''}{money(detail.pnl_usd)}
              </div>
            </div>
            <div>
              <div className="label">Basis</div>
              <div className="big">{Math.round((detail.basis_reliable_share || 0) * 100)}%</div>
            </div>
          </div>
          <div className="detail-spark">
            <Sparkline points={detail.sparkline} width={280} height={48} />
            {detail.sparkline.length < 2 && <span className="note">no price history available</span>}
          </div>
          <h4>Where it lives</h4>
          <table className="mini-table">
            <thead>
              <tr><th>Provider</th><th>Qty</th><th>Value</th><th>Avg cost</th></tr>
            </thead>
            <tbody>
              {detail.providers.map((p) => (
                <tr key={p.provider}>
                  <td>{p.label}</td>
                  <td>{Number(p.qty).toLocaleString('en-US', { maximumFractionDigits: 8 })}</td>
                  <td>{money(p.value_usd)}</td>
                  <td>{p.avg_cost_usd ? `$${p.avg_cost_usd.toFixed(4)}` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {detail.signals.length > 0 && (
            <>
              <h4>Latest signals</h4>
              {detail.signals.map((signal, index) => (
                <div key={index} className="signal-row">
                  <span className={`badge ${signal.action === 'BUY' ? 'pos' : signal.action === 'SELL' ? 'neg' : ''}`}>
                    {signal.action}
                  </span>
                  <span>{signal.headline}</span>
                </div>
              ))}
            </>
          )}
          {detail.knowledge.length > 0 && (
            <>
              <h4>Related knowledge</h4>
              {detail.knowledge.map((entry) => (
                <div key={entry.id} className="knowledge-row">
                  <strong>{entry.topic}</strong>
                  <p className="note">{entry.summary.slice(0, 160)}…</p>
                </div>
              ))}
            </>
          )}
          {detail.signals.length === 0 && detail.knowledge.length === 0 && (
            <p className="note">No signals or knowledge entries for this asset yet — ask the Coach in the chat.</p>
          )}
        </>
      )}
    </div>
  )
}
