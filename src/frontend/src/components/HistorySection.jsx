import { useEffect, useState } from 'react'
import { fetchHistory } from '../api.js'
import { LineChart } from './Charts.jsx'

const RANGES = [
  { id: '24h', label: '24h' },
  { id: '7d', label: '7d' },
  { id: 'all', label: 'All' },
]

export default function HistorySection({ fetchedAt }) {
  const [range, setRange] = useState('7d')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load(activeRange) {
    setLoading(true)
    try {
      setData(await fetchHistory(activeRange))
    } catch {
      setData({ points: [], collecting: true })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(range)
  }, [range, fetchedAt])

  return (
    <div className="portfolio-section">
      <div className="section-head">
        <h3>Performance</h3>
        <div className="range-toggle">
          {RANGES.map((item) => (
            <button
              key={item.id}
              className={`range-btn ${range === item.id ? 'active' : ''}`}
              onClick={() => setRange(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      {loading && !data ? <div className="skeleton chart-skeleton" /> : <LineChart points={data?.points} />}
      {data?.collecting && (
        <p className="note">Snapshots are recorded every time you open the Portfolio tab. Over time this chart fills up.</p>
      )}
    </div>
  )
}
