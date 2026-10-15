import { useEffect, useState } from 'react'
import { fetchAllocation, setAllocationTargets } from '../api.js'

function money(value) {
  return `$${Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

const PRESETS = [
  { name: 'Balanced', targets: { MAJOR: 35, ALT: 15, STABLES: 15, STOCKS: 35 } },
  { name: 'Growth', targets: { MAJOR: 40, ALT: 30, STABLES: 5, STOCKS: 25 } },
  { name: 'Defensive', targets: { MAJOR: 20, ALT: 5, STABLES: 40, STOCKS: 35 } },
]

export default function AllocationSection() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [draft, setDraft] = useState({})

  async function load() {
    try {
      const result = await fetchAllocation()
      setData(result)
      const current = result.targets || {}
      setDraft({ MAJOR: current.MAJOR ?? 35, ALT: current.ALT ?? 15, STABLES: current.STABLES ?? 15, STOCKS: current.STOCKS ?? 35 })
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function save(targets) {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      await setAllocationTargets(targets)
      setSaved(true)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const draftSum = Object.values(draft).reduce((sum, v) => sum + Number(v || 0), 0)

  return (
    <div className="portfolio-section">
      <h3>Rebalance Coach</h3>
      {error && <p className="error">{error}</p>}
      {!data && !error && <div className="skeleton table-skeleton" />}
      {data && (
        <>
          <div className="preset-row">
            {PRESETS.map((preset) => (
              <button
                key={preset.name}
                className="preset-btn"
                disabled={saving}
                onClick={async () => {
                  setDraft(preset.targets)
                  await save(preset.targets)
                }}
              >
                {preset.name}
              </button>
            ))}
          </div>
          <div className="target-editor">
            {Object.entries(draft).map(([key, value]) => (
              <label key={key} className="target-field">
                <span>{key}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={value}
                  onChange={(event) => setDraft({ ...draft, [key]: event.target.value })}
                />
              </label>
            ))}
            <span className={`target-sum ${Math.abs(draftSum - 100) <= 0.5 ? 'pos' : 'neg'}`}>{draftSum}%</span>
          </div>
          <button
            className="apply-btn"
            disabled={saving || Math.abs(draftSum - 100) > 0.5}
            onClick={async () => {
              const cleaned = {}
              Object.entries(draft).forEach(([key, value]) => {
                if (Number(value) > 0) cleaned[key] = Number(value)
              })
              await save(cleaned)
            }}
          >
            {saving ? 'Saving…' : 'Set target allocation'}
          </button>
          {saved && <p className="note">Target saved.</p>}
          <table className="mini-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Now</th>
                <th>Target</th>
                <th>Drift</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.current.map((item) => (
                <tr key={item.asset} className={item.action ? 'drift-active' : ''}>
                  <td>{item.asset}</td>
                  <td>{item.weight_pct}%</td>
                  <td>{item.target_pct}%</td>
                  <td className={item.drift_pct >= 0 ? 'pos' : 'neg'}>
                    {item.drift_pct > 0 ? '+' : ''}{item.drift_pct}%
                  </td>
                  <td>
                    {item.action ? (
                      <span className={item.action === 'buy' ? 'pos' : 'neg'}>
                        {item.action === 'buy' ? '▲ buy' : '▼ sell'} {money(item.amount_usd)}
                      </span>
                    ) : (
                      <span className="note">within ±{data.tolerance_pct}%</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note">{data.note}</p>
        </>
      )}
    </div>
  )
}
