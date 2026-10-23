import { formatMoney, formatPercent } from '../../utils/format'
import { NoData } from './ChartPrimitives'
import { colorFor, niceScale, useChartSize } from './chartUtils'

/**
 * Category comparison bars: the previous period behind, the current one in front.
 *
 * A grouped bar is right here because the question is "more or less than before",
 * and two bars per category answer it without arithmetic. The delta is printed
 * beside each pair so the chart does not have to be measured by eye.
 *
 * @param {Object} props
 * @param {Array<{category: string, total: number, count: number, is_money_movement: boolean}>} props.current
 * @param {Array<{category: string, total: number}>} props.previous
 * @param {string} props.currency
 * @param {number} [props.limit]
 * @param {boolean} [props.includeMoneyMovement]
 */
export default function CategoryBars({
  current = [],
  previous = [],
  currency,
  limit = 10,
  includeMoneyMovement = false,
}) {
  const [ref, { width }] = useChartSize(560, 320)

  const rows = current
    .filter((row) => includeMoneyMovement || !row.is_money_movement)
    .slice(0, limit)

  if (!rows.length) return <NoData message="No spending in this period." />

  const previousByName = Object.fromEntries(previous.map((row) => [row.category, row.total]))
  const peak = Math.max(1, ...rows.flatMap((row) => [row.total, previousByName[row.category] ?? 0]))
  const scale = niceScale(peak)
  const labelWidth = 150
  const valueWidth = 116
  const barArea = Math.max(60, width - labelWidth - valueWidth)
  const rowHeight = 30
  const barHeight = 9
  const height = rows.length * rowHeight + 8

  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label="Spending by category, current versus previous">
        {rows.map((row, index) => {
          const before = previousByName[row.category] ?? 0
          const y = index * rowHeight
          const currentWidth = (row.total / scale.max) * barArea
          const previousWidth = (before / scale.max) * barArea
          const change = before ? ((row.total - before) / before) * 100 : null
          const grew = row.total > before

          return (
            <g key={row.category}>
              <text x={0} y={y + 13} fontSize={11} fill="#023047">
                {row.category.length > 23 ? `${row.category.slice(0, 22)}…` : row.category}
              </text>
              <text x={0} y={y + 25} fontSize={9} fill="#adb5bd">
                {row.count} transaction{row.count === 1 ? '' : 's'}
              </text>

              {/* previous period, ghosted behind */}
              <rect
                x={labelWidth}
                y={y + 3}
                width={previousWidth}
                height={barHeight}
                fill="#e9ecef"
                rx={2}
              />
              <rect
                x={labelWidth}
                y={y + 3 + barHeight}
                width={currentWidth}
                height={barHeight}
                fill={colorFor(index)}
                rx={2}
              />

              <text
                x={labelWidth + Math.max(currentWidth, previousWidth) + 8}
                y={y + 18}
                fontSize={11}
                fill="#023047"
              >
                {formatMoney(row.total, currency)}
              </text>
              {change !== null && (
                <text
                  x={labelWidth + Math.max(currentWidth, previousWidth) + 8}
                  y={y + 29}
                  fontSize={9}
                  fill={grew ? 'var(--alert-red)' : 'var(--success-green)'}
                >
                  {grew ? '▲' : '▼'} {formatPercent(Math.abs(change), 0)} vs {formatMoney(before, currency)}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
