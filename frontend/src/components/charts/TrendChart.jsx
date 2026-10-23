import { useState } from 'react'

import { formatMoney, formatPercent } from '../../utils/format'
import { ChartTooltip, Legend, NoData, YAxis } from './ChartPrimitives'
import { useMemo } from 'react'

import { AXIS_COLOR, compactNumber, niceScale, useChartSize, useHover } from './chartUtils'

/**
 * Monthly income against consumption, with a savings-rate line.
 *
 * Consumption rather than raw expenses: transfers and loan repayments move money,
 * so plotting them beside real spending would exaggerate the bars and hide the
 * habit the chart exists to reveal.
 *
 * @param {Object} props
 * @param {Array<{month: string, label: string, income: number, consumption: number, money_movement: number, net: number, savings_rate: number|null, count: number}>} props.data
 * @param {string} props.currency
 * @param {number} [props.height]
 */
export default function TrendChart({ data = [], currency, height = 300 }) {
  const [ref, { width }] = useChartSize(720, height)
  const [hover, setHover] = useHover()
  const [hidden, setHidden] = useState([])
  const [showRate, setShowRate] = useState(true)
  // A month with an unusually large income (a bonus, a house sale) flattens the
  // spending bars, which is the opposite of what this chart is for. Spending-only
  // rescales it to the bars alone.
  const [spendingOnly, setSpendingOnly] = useState(false)
  const effectiveHidden = useMemo(
    () => (spendingOnly ? [...new Set([...hidden, 'income'])] : hidden),
    [spendingOnly, hidden]
  )

  const padding = { left: 48, right: 44, top: 16, bottom: 34 }
  const plotWidth = Math.max(10, width - padding.left - padding.right)
  const plotHeight = height - padding.top - padding.bottom

  const geometry = useMemo(() => {
    const peak = Math.max(
      1,
      ...data.flatMap((row) => [
        effectiveHidden.includes('income') ? 0 : row.income,
        effectiveHidden.includes('consumption') ? 0 : row.consumption,
      ])
    )
    const scale = niceScale(peak)
    const slot = plotWidth / Math.max(1, data.length)
    const barWidth = Math.max(
      3,
      Math.min(effectiveHidden.includes('income') ? slot * 0.55 : slot / 2.6, 26)
    )
    return { scale, slot, barWidth, peak }
  }, [data, plotWidth, effectiveHidden])

  if (!data.length) return <div ref={ref}><NoData /></div>

  const { scale, slot, barWidth } = geometry
  const barY = (value) => padding.top + plotHeight - (value / scale.max) * plotHeight
  const barHeight = (value) => Math.max(0, padding.top + plotHeight - barY(value))
  const centre = (index) => padding.left + slot * index + slot / 2

  const rates = data.map((row) => row.savings_rate).filter((value) => value !== null)
  const rateMax = Math.max(40, ...rates.map((value) => Math.abs(value)))
  const rateY = (value) =>
    padding.top + plotHeight / 2 - (value / rateMax) * (plotHeight / 2)
  const ratePoints = data
    .map((row, index) => ({ index, value: row.savings_rate }))
    .filter((point) => point.value !== null)
    .map((point) => `${centre(point.index)},${rateY(point.value)}`)
    .join(' ')

  const labelStride = Math.max(1, Math.ceil(data.length / Math.max(3, Math.floor(plotWidth / 92))))
  const visible = data
    .map((row, index) => ({ row, index }))
    .filter(({ index }) => index % labelStride === 0 || index === data.length - 1)

  return (
    <div ref={ref} className="chart">
      <div className="row-between" style={{ marginBottom: '0.35rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <Legend
          items={[
            { key: 'income', label: 'Income', color: 'var(--success-green)' },
            { key: 'consumption', label: 'Spending', color: 'var(--deep-orange)' },
          ]}
          hidden={effectiveHidden}
          onToggle={(key) => {
            if (key === 'income') setSpendingOnly(false)
            setHidden((current) =>
              current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
            )
          }}
        />
        <span style={{ display: 'flex', gap: '0.9rem', alignItems: 'center' }}>
          <label className="text-muted" style={{ fontSize: '0.8rem' }}>
            <input
              type="checkbox"
              checked={spendingOnly}
              onChange={(event) => {
                setSpendingOnly(event.target.checked)
                if (event.target.checked) setShowRate(false)
              }}
            />{' '}
            spending only
          </label>
          <label className="text-muted" style={{ fontSize: '0.8rem' }}>
            <input
              type="checkbox"
              checked={showRate}
              disabled={spendingOnly}
              onChange={(event) => setShowRate(event.target.checked)}
            />{' '}
            savings rate
          </label>
        </span>
      </div>

      <svg width={width} height={height} role="img" aria-label="Monthly income and spending">
        <YAxis
          scale={scale}
          format={compactNumber}
          width={width}
          height={height}
          padding={padding.top}
        />

        {data.map((row, index) => (
          <g key={row.month}>
            <rect
              x={padding.left + slot * index}
              y={padding.top}
              width={slot}
              height={plotHeight}
              fill={hover === index ? 'rgba(2,48,71,0.04)' : 'transparent'}
              onMouseEnter={() => setHover(index)}
              onMouseLeave={() => setHover(null)}
            />
            {!effectiveHidden.includes('income') && (
              <rect
                x={centre(index) - barWidth - 1}
                y={barY(row.income)}
                width={barWidth}
                height={barHeight(row.income)}
                fill="var(--success-green)"
                rx={2}
                pointerEvents="none"
              />
            )}
            {!effectiveHidden.includes('consumption') && (
              <rect
                x={centre(index) + 1}
                y={barY(row.consumption)}
                width={barWidth}
                height={barHeight(row.consumption)}
                fill="var(--deep-orange)"
                rx={2}
                pointerEvents="none"
              />
            )}
          </g>
        ))}

        {showRate && ratePoints && (
          <>
            <polyline points={ratePoints} fill="none" stroke="var(--ocean-blue)" strokeWidth={2} />
            <line
              x1={padding.left}
              x2={width - padding.right + 8}
              y1={rateY(0)}
              y2={rateY(0)}
              stroke={AXIS_COLOR}
              strokeDasharray="3 3"
              strokeWidth={1}
            />
            <text
              x={width - padding.right + 12}
              y={rateY(0) + 3}
              fontSize={10}
              fill={AXIS_COLOR}
              textAnchor="start"
            >
              0%
            </text>
          </>
        )}

        {visible.map(({ row, index }) => {
          const [month, year] = row.label.split(' ')
          // The year is always shown: a 24-month window repeats month names.
          return (
            <text key={row.month} textAnchor="middle" fontSize={10} fill={AXIS_COLOR}>
              <tspan x={centre(index)} y={height - 18}>
                {month}
              </tspan>
              <tspan x={centre(index)} y={height - 7} fontSize={9} fill="#ced4da">
                {year?.slice(2) ? `’${year.slice(2)}` : ''}
              </tspan>
            </text>
          )
        })}

        {hover !== null && data[hover] && (
          <ChartTooltip x={centre(hover)} y={padding.top + 10} width={width}>
            <strong>{data[hover].label}</strong>
            <div>
              Income: <b>{formatMoney(data[hover].income, currency)}</b>
            </div>
            <div>
              Spending: <b>{formatMoney(data[hover].consumption, currency)}</b>
            </div>
            {data[hover].money_movement > 0 && (
              <div className="text-muted">
                Movement: {formatMoney(data[hover].money_movement, currency)}
              </div>
            )}
            <div className={data[hover].net >= 0 ? 'pos' : 'neg'}>
              Net: <b>{formatMoney(data[hover].net, currency)}</b>
            </div>
            {data[hover].savings_rate !== null && (
              <div className="text-muted">
                Savings rate: {formatPercent(data[hover].savings_rate, 0)}
              </div>
            )}
            <div className="text-muted">{data[hover].count} transactions</div>
          </ChartTooltip>
        )}
      </svg>
    </div>
  )
}
