import { useMemo, useState } from 'react'

import { formatMoney, formatPercent } from '../../utils/format'
import { NoData } from './ChartPrimitives'
import { colorFor, useChartSize } from './chartUtils'

/** A colour ramp that stays distinguishable in greyscale and for colour blindness. */
/**
 * Category share as a donut.
 *
 * A donut rather than a pie because the hole holds the total, which is the number
 * people look for first. Money movement is excluded before this component is
 * called: a transfer is not a slice of spending.
 *
 * @param {Object} props
 * @param {Array<{category: string, total: number, count: number, average: number}>} props.data
 * @param {string} props.currency
 * @param {number} [props.size]
 * @param {number} [props.maxSlices]
 */
export default function CategoryDonut({ data = [], currency, size = 240, maxSlices = 7 }) {
  const [ref, { width }] = useChartSize(size, size)
  const [active, setActive] = useState(null)

  const { slices, total, omitted } = useMemo(() => {
    const positive = data.filter((row) => row.total > 0)
    const sorted = [...positive].sort((a, b) => b.total - a.total)
    const head = sorted.slice(0, maxSlices)
    const tail = sorted.slice(maxSlices)
    const sum = sorted.reduce((accumulator, row) => accumulator + row.total, 0)

    const computed = head.map((row, index) => ({
      ...row,
      color: colorFor(index),
      share: sum ? row.total / sum : 0,
    }))
    if (tail.length) {
      const tailSum = tail.reduce((accumulator, row) => accumulator + row.total, 0)
      computed.push({
        category: `Other (${tail.length})`,
        total: tailSum,
        count: tail.reduce((accumulator, row) => accumulator + row.count, 0),
        color: '#ced4da',
        share: sum ? tailSum / sum : 0,
      })
    }
    return { slices: computed, total: sum, omitted: tail.length }
  }, [data, maxSlices])

  if (!slices.length) return <NoData message="No spending in this period." />

  const diameter = Math.min(width, size)
  const radius = diameter / 2 - 6
  const inner = radius * 0.62
  const cx = diameter / 2
  const cy = diameter / 2

  let angle = -Math.PI / 2
  const arcs = slices.map((slice) => {
    const sweep = slice.share * Math.PI * 2
    const start = angle
    const end = angle + sweep
    angle = end
    const large = sweep > Math.PI ? 1 : 0
    const path = [
      `M ${cx + radius * Math.cos(start)} ${cy + radius * Math.sin(start)}`,
      `A ${radius} ${radius} 0 ${large} 1 ${cx + radius * Math.cos(end)} ${cy + radius * Math.sin(end)}`,
      `L ${cx + inner * Math.cos(end)} ${cy + inner * Math.sin(end)}`,
      `A ${inner} ${inner} 0 ${large} 0 ${cx + inner * Math.cos(start)} ${cy + inner * Math.sin(start)}`,
      'Z',
    ].join(' ')
    return { ...slice, path }
  })

  const focused = active !== null ? slices[active] : null

  return (
    <div ref={ref} className="donut">
      <svg width={diameter} height={diameter} role="img" aria-label="Spending by category">
        {arcs.map((slice, index) => (
          <path
            key={slice.category}
            d={slice.path}
            fill={slice.color}
            opacity={active === null || active === index ? 1 : 0.35}
            onMouseEnter={() => setActive(index)}
            onMouseLeave={() => setActive(null)}
            style={{ transition: 'opacity 0.15s ease' }}
          />
        ))}
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize={11} fill="#6c757d">
          {focused ? `${focused.category.slice(0, 20)}${focused.category.length > 20 ? '…' : ''}` : 'Spent'}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fontSize={15} fontWeight="600" fill="#023047">
          {formatMoney(focused ? focused.total : total, currency)}
        </text>
        {focused && (
          <text x={cx} y={cy + 28} textAnchor="middle" fontSize={10} fill="#6c757d">
            {formatPercent(focused.share * 100, 1)} of spending
          </text>
        )}
      </svg>

      <ul className="donut__legend">
        {slices.map((slice, index) => (
          <li
            key={slice.category}
            onMouseEnter={() => setActive(index)}
            onMouseLeave={() => setActive(null)}
          >
            <span className="donut__swatch" style={{ background: slice.color }} />
            <span className="donut__name" title={slice.category}>
              {slice.category}
            </span>
            <span className="donut__value">{formatMoney(slice.total, currency)}</span>
            <span className="donut__share text-muted">{formatPercent(slice.share * 100, 0)}</span>
          </li>
        ))}
      </ul>
      {omitted > 0 && (
        <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>
          {omitted} smaller categories grouped as “Other”.
        </p>
      )}
    </div>
  )
}
