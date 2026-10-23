import { formatMoney } from '../../utils/format'
import { compactNumber, niceScale, useChartSize } from './chartUtils'

/**
 * Spending by day of week.
 *
 * A bar per weekday with the monthly average marked, so "I spend too much on
 * Mondays" becomes something measurable rather than a feeling.
 *
 * @param {Object} props
 * @param {Array<{weekday: number, label: string, total: number, count: number}>} props.data
 * @param {string} props.currency
 * @param {number} [props.height]
 */
export function WeekdayChart({ data = [], currency, height = 190 }) {
  const [ref, { width }] = useChartSize(420, height)
  if (!data.length || data.every((row) => row.total === 0)) {
    return <p className="text-muted">No spending in the last 12 months.</p>
  }

  const padding = { left: 40, right: 8, top: 12, bottom: 26 }
  const plotWidth = Math.max(10, width - padding.left - padding.right)
  const plotHeight = height - padding.top - padding.bottom
  const scale = niceScale(Math.max(...data.map((row) => row.total)), 3)
  const slot = plotWidth / data.length
  const barWidth = Math.min(34, slot * 0.6)

  const average = data.reduce((sum, row) => sum + row.total, 0) / data.length
  const averageY = padding.top + plotHeight - (average / scale.max) * plotHeight
  const peak = Math.max(...data.map((row) => row.total))

  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label="Spending by day of week">
        {[0, 0.5, 1].map((fraction) => (
          <g key={fraction}>
            <line
              x1={padding.left}
              x2={width - 4}
              y1={padding.top + plotHeight * (1 - fraction)}
              y2={padding.top + plotHeight * (1 - fraction)}
              stroke="#eef0f2"
            />
            <text
              x={padding.left - 6}
              y={padding.top + plotHeight * (1 - fraction) + 3}
              fontSize={10}
              fill="#adb5bd"
              textAnchor="end"
            >
              {compactNumber(scale.max * fraction)}
            </text>
          </g>
        ))}

        <line
          x1={padding.left}
          x2={width - 4}
          y1={averageY}
          y2={averageY}
          stroke="var(--ocean-blue)"
          strokeDasharray="4 3"
        />
        <text x={width - 6} y={averageY - 4} fontSize={9} fill="var(--ocean-blue)" textAnchor="end">
          avg {formatMoney(average, currency)}
        </text>

        {data.map((row, index) => {
          const barHeight = (row.total / scale.max) * plotHeight
          const isPeak = row.total === peak && peak > 0
          const x = padding.left + slot * index + (slot - barWidth) / 2
          return (
            <g key={row.weekday}>
              <rect
                x={x}
                y={padding.top + plotHeight - barHeight}
                width={barWidth}
                height={Math.max(1, barHeight)}
                fill={isPeak ? 'var(--deep-orange)' : 'var(--sky-blue)'}
                rx={3}
              >
                <title>
                  {row.label}: {formatMoney(row.total, currency)} across {row.count} transactions
                </title>
              </rect>
              <text
                x={x + barWidth / 2}
                y={height - 8}
                fontSize={10}
                fill="#6c757d"
                textAnchor="middle"
              >
                {row.label.slice(0, 3)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/**
 * This month's spending against a typical month.
 *
 * The bar is drawn against the user's own median, not an arbitrary target, and the
 * marker shows where the month is expected to land at the current pace.
 *
 * @param {Object} props
 * @param {import('../../../services/analyticsService').SpendingOutlook} props.outlook
 * @param {string} props.currency
 */
export function OutlookMeter({ outlook, currency }) {
  if (!outlook) return null

  const typical = outlook.typical_month || 0
  const projected = outlook.projected_month_end || 0
  const spent = outlook.spent_so_far || 0
  const ceiling = Math.max(typical, projected, spent) * 1.12 || 1

  const widthOf = (value) => `${Math.min(100, (value / ceiling) * 100)}%`

  const verdictText = {
    high: 'heading above your usual month',
    low: 'comfortably below your usual month',
    normal: 'in line with your usual month',
    in_progress: 'not enough history to compare yet',
  }[outlook.verdict]

  const tone = { high: 'neg', low: 'pos', normal: '', in_progress: 'text-muted' }[outlook.verdict]

  return (
    <div className="outlook">
      <div className="row-between">
        <span className="text-muted">
          Day {outlook.days_elapsed} of {outlook.days_in_month}
        </span>
        <span className={tone}>{verdictText}</span>
      </div>

      <div className="outlook__track" title={`Typical month ${formatMoney(typical, currency)}`}>
        <div className="outlook__bar" style={{ width: widthOf(spent) }} />
        <div className="outlook__typical" style={{ left: widthOf(typical) }} />
        <div className="outlook__projected" style={{ left: widthOf(projected) }}>
          <span>projected</span>
        </div>
      </div>

      <div className="outlook__figures">
        <div>
          <span className="text-muted">Spent</span>
          <strong>{formatMoney(spent, currency)}</strong>
        </div>
        <div>
          <span className="text-muted">Typical month</span>
          <strong>{formatMoney(typical, currency)}</strong>
        </div>
        <div>
          <span className="text-muted">At this pace</span>
          <strong className={tone}>{formatMoney(projected, currency)}</strong>
        </div>
        <div>
          <span className="text-muted">Left to usual</span>
          <strong className={outlook.budget_remaining_to_typical < 0 ? 'neg' : 'pos'}>
            {formatMoney(outlook.budget_remaining_to_typical, currency)}
          </strong>
        </div>
      </div>

      <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>
        Compared with your median over the last {outlook.months_compared} complete months
        {outlook.monthly_spread ? ` (typical variation ±${formatMoney(outlook.monthly_spread, currency)})` : ''}.
      </p>
    </div>
  )
}

/** A small stat used inside the insight cards. */
export function MiniStat({ label, value, tone, hint }) {
  return (
    <div className="mini-stat">
      <span className="text-muted">{label}</span>
      <strong className={tone}>{value}</strong>
      {hint && <small className="text-muted">{hint}</small>}
    </div>
  )
}

