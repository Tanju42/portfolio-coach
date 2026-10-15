export function DonutChart({ slices, size = 160, thickness = 22, centerLabel, centerValue }) {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0)
  if (total <= 0) return null
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius
  let offset = 0
  const top = slices.slice(0, 6)
  const restValue = total - top.reduce((sum, slice) => sum + slice.value, 0)
  const shown = restValue > 0 ? [...top, { label: 'Other', value: restValue, color: '#3a4454' }] : top
  return (
    <div className="donut-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1c2330" strokeWidth={thickness} />
        {shown.map((slice) => {
          const fraction = slice.value / total
          const dash = fraction * circumference
          const element = (
            <circle
              key={slice.label}
              cx={size / 2} cy={size / 2} r={radius}
              fill="none"
              stroke={slice.color}
              strokeWidth={thickness}
              strokeDasharray={`${Math.max(dash - 1.5, 0.5)} ${circumference - dash + 1.5}`}
              strokeDashoffset={-offset}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
              strokeLinecap="butt"
            />
          )
          offset += dash
          return element
        })}
        <text x="50%" y="47%" textAnchor="middle" className="donut-value">{centerValue}</text>
        <text x="50%" y="61%" textAnchor="middle" className="donut-label">{centerLabel}</text>
      </svg>
      <ul className="donut-legend">
        {shown.map((slice) => (
          <li key={slice.label}>
            <span className="dot" style={{ background: slice.color }} />
            <span className="legend-name">{slice.label}</span>
            <span className="legend-pct">{Math.round((slice.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function LineChart({ points, height = 140, color = '#4f8ef7' }) {
  if (!points || points.length < 2) {
    return <div className="chart-empty">Collecting portfolio snapshots — the chart fills in as the backend records values.</div>
  }
  const width = 320
  const values = points.map((p) => p.value_usd)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const stepX = width / (points.length - 1)
  const coords = points.map((p, i) => [
    i * stepX,
    height - 12 - ((p.value_usd - min) / span) * (height - 24),
  ])
  const path = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${path} L${width},${height} L0,${height} Z`
  const first = values[0]
  const last = values[values.length - 1]
  const change = last - first
  const changeClass = change >= 0 ? 'pos' : 'neg'
  return (
    <div className="linechart-wrap">
      <div className="linechart-meta">
        <span>{`$${min.toLocaleString('en-US', { maximumFractionDigits: 0 })} – $${max.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}</span>
        <span className={changeClass}>
          {change >= 0 ? '+' : '-'}${Math.abs(change).toLocaleString('en-US', { maximumFractionDigits: 0 })} ({Math.round((change / (first || 1)) * 100)}%)
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="linechart">
        <path d={area} fill={color} opacity="0.12" />
        <path d={path} fill="none" stroke={color} strokeWidth="2" />
        <circle cx={coords[coords.length - 1][0]} cy={coords[coords.length - 1][1]} r="3.5" fill={color} />
      </svg>
      <div className="linechart-times">
        <span>{new Date(points[0].ts * 1000).toLocaleString()}</span>
        <span>{new Date(points[points.length - 1].ts * 1000).toLocaleString()}</span>
      </div>
    </div>
  )
}

export function Sparkline({ points, width = 96, height = 28, color }) {
  if (!points || points.length < 2) return <span className="spark-empty">—</span>
  const values = points.map((p) => p.close)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const stepX = width / (points.length - 1)
  const coords = values.map((v, i) => [
    i * stepX,
    height - 3 - ((v - min) / span) * (height - 6),
  ])
  const path = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const stroke = color || (values[values.length - 1] >= values[0] ? '#3fb950' : '#f778ba')
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} className="sparkline">
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.6" />
    </svg>
  )
}

export const DONUT_COLORS = ['#4f8ef7', '#3fb950', '#d29922', '#f778ba', '#8957e5', '#39c5cf']

export function donutSlices(rows) {
  return rows
    .filter((row) => row.value_usd > 0.5)
    .map((row, index) => ({ label: row.asset.replace(/^LD/, ''), value: row.value_usd, color: DONUT_COLORS[index % DONUT_COLORS.length] }))
}
