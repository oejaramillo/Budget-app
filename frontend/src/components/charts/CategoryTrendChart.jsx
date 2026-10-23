import { useMemo, useState } from 'react'

import { formatMoney, formatPercent } from '../../utils/format'
import { NoData } from './ChartPrimitives'
import { colorFor, compactNumber, niceScale, useChartSize } from './chartUtils'

/**
 * Per-category spending over time, stacked.
 *
 * Stacking answers "is my total rising because everything is rising, or because of
 * one thing", which a set of separate lines does not. Categories can be toggled
 * from the legend so a single one can be isolated.
 *
 * @param {Object} props
 * @param {{months: string[], labels: string[], categories: string[], series: Array<{category: string, values: number[]}>, other: number[], money_movement: number[]}} props.data
 * @param {string} props.currency
 * @param {number} [props.height]
 */
export default function CategoryTrendChart({ data, currency, height = 300 }) {
  const [ref, { width }] = useChartSize(720, height)
  const [hidden, setHidden] = useState([])
  const [hover, setHover] = useState(null)

  const visibleSeries = useMemo(
    () => (data?.series ?? []).filter((series) => !hidden.includes(series.category)),
    [data, hidden]
  )

  const geometry = useMemo(() => {
    if (!data?.months?.length) return null
    const totals = data.months.map((_, index) =>
      visibleSeries.reduce((sum, series) => sum + (series.values[index] ?? 0), 0)
    )
    const scale = niceScale(Math.max(1, ...totals))
    return { totals, scale }
  }, [data, visibleSeries])

  if (!data?.months?.length || !data.series?.length) {
    return <NoData message="Not enough history for a category trend yet." />
  }

  const padding = { left: 48, right: 12, top: 14, bottom: 34 }
  const plotWidth = Math.max(10, width - padding.left - padding.right)
  const plotHeight = height - padding.top - padding.bottom
  const slot = plotWidth / data.months.length
  const barWidth = Math.max(4, Math.min(26, slot * 0.66))

  const y = (value) => padding.top + plotHeight - (value / geometry.scale.max) * plotHeight

  // Stack one category on top of the previous within each month.
  const stacks = data.months.map((_, index) => {
    let cursor = 0
    return visibleSeries.map((series) => {
      const value = series.values[index] ?? 0
      const segment = { series: series.category, value, from: cursor, to: cursor + value }
      cursor += value
      return segment
    })
  })

  const labelEvery = Math.ceil(data.months.length / 10)

  return (
    <div ref={ref}>
      <div className="chart-legend">
        {data.series.map((series) => {
          const isHidden = hidden.includes(series.category)
          return (
            <button
              key={series.category}
              type="button"
              className={`chart-legend__item${isHidden ? ' is-hidden' : ''}`}
              onClick={() =>
                setHidden((current) =>
                  current.includes(series.category)
                    ? current.filter((item) => item !== series.category)
                    : [...current, series.category]
                )
              }
            >
              <span
                className="chart-legend__swatch"
                style={{ background: colorFor(data.series.findIndex((s) => s.category === series.category)) }}
              />
              {series.category}
            </button>
          )
        })}
      </div>

      <svg
        width={width}
        height={height}
        role="img"
        aria-label="Spending by category over time"
        onMouseLeave={() => setHover(null)}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <g key={fraction}>
            <line
              x1={padding.left}
              x2={width - 4}
              y1={y(geometry.scale.max * fraction)}
              y2={y(geometry.scale.max * fraction)}
              stroke="#eef0f2"
            />
            <text
              x={padding.left - 6}
              y={y(geometry.scale.max * fraction) + 3}
              fontSize={10}
              fill="#adb5bd"
              textAnchor="end"
            >
              {compactNumber(geometry.scale.max * fraction)}
            </text>
          </g>
        ))}

        {stacks.map((segments, index) => (
          <g key={data.months[index]} onMouseEnter={() => setHover(index)}>
            <rect
              x={padding.left + slot * index}
              y={padding.top}
              width={slot}
              height={plotHeight}
              fill={hover === index ? 'rgba(2,48,71,0.04)' : 'transparent'}
            />
            {segments.map((segment) => {
              if (segment.value <= 0) return null
              const top = y(segment.to)
              const bottom = y(segment.from)
              const colour = colorFor(
                data.series.findIndex((series) => series.category === segment.series)
              )
              return (
                <rect
                  key={segment.series}
                  x={padding.left + slot * index + (slot - barWidth) / 2}
                  y={top}
                  width={barWidth}
                  height={Math.max(1, bottom - top)}
                  fill={colour}
                  pointerEvents="none"
                />
              )
            })}
          </g>
        ))}

        {data.months.map((month, index) =>
          index % labelEvery === 0 ? (
            <text
              key={month}
              x={padding.left + slot * index + slot / 2}
              y={height - 12}
              fontSize={10}
              fill="#adb5bd"
              textAnchor="middle"
            >
              {data.labels[index].slice(0, 3)}
            </text>
          ) : null
        )}
      </svg>

      {hover !== null && (
        <div className="trend-hover card">
          <strong>{data.labels[hover]}</strong>
          <div className="text-muted" style={{ fontSize: '0.8rem' }}>
            total {formatMoney(geometry.totals[hover], currency)}
          </div>
          <ul>
            {stacks[hover]
              .filter((segment) => segment.value > 0)
              .sort((a, b) => b.value - a.value)
              .slice(0, 6)
              .map((segment) => (
                <li key={segment.series}>
                  <span
                    className="chart-legend__swatch"
                    style={{
                      background: colorFor(
                        data.series.findIndex((series) => series.category === segment.series)
                      ),
                    }}
                  />
                  {segment.series}
                  <b>{formatMoney(segment.value, currency)}</b>
                  <span className="text-muted">
                    {formatPercent(
                      geometry.totals[hover] ? (segment.value / geometry.totals[hover]) * 100 : 0,
                      0
                    )}
                  </span>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  )
}
