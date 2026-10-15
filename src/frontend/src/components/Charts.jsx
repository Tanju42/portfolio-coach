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

export const DONUT_COLORS = ['#4f8ef7', '#3fb950', '#d29922', '#f778ba', '#8957e5', '#39c5cf']

export function donutSlices(rows) {
  return rows
    .filter((row) => row.value_usd > 0.5)
    .map((row, index) => ({ label: row.asset.replace(/^LD/, ''), value: row.value_usd, color: DONUT_COLORS[index % DONUT_COLORS.length] }))
}
