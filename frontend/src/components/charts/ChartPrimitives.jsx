/**
 * Chart primitives: axes and overlays.
 *
 * Kept apart from `chartUtils.js` because these render JSX, which only compiles in
 * a `.jsx` file.
 */

import { AXIS_COLOR, GRID_COLOR } from './chartUtils'

/** Axis ticks and horizontal grid lines. */
export function YAxis({ scale, format, width, height, padding }) {
  const ticks = []
  for (let value = 0; value <= scale.max + 1e-9; value += scale.step) {
    ticks.push(value)
  }
  const plotHeight = height - padding * 2
  const y = (value) => padding + plotHeight - (value / scale.max) * plotHeight

  return (
    <g>
      {ticks.map((value) => (
        <g key={value}>
          <line
            x1={padding}
            x2={width - 4}
            y1={y(value)}
            y2={y(value)}
            stroke={GRID_COLOR}
            strokeWidth={1}
          />
          <text x={padding - 6} y={y(value) + 3} textAnchor="end" fontSize={10} fill={AXIS_COLOR}>
            {format(value)}
          </text>
        </g>
      ))}
    </g>
  )
}

/** Floating tooltip anchored inside the chart box. */
export function ChartTooltip({ x, y, width, children }) {
  const flip = x > width - 150
  return (
    <foreignObject
      x={Math.max(0, Math.min(flip ? x - 165 : x + 10, Math.max(0, width - 170)))}
      y={Math.max(0, y - 10)}
      width={160}
      height={140}
      style={{ pointerEvents: 'none' }}
    >
      <div className="chart-tooltip" xmlns="http://www.w3.org/1999/xhtml">
        {children}
      </div>
    </foreignObject>
  )
}

/** Horizontal legend, wrapping onto as many lines as needed. */
export function Legend({ items, onToggle, hidden = [] }) {
  return (
    <div className="chart-legend">
      {items.map((item) => {
        const isHidden = hidden.includes(item.key)
        return (
          <button
            key={item.key}
            type="button"
            className={`chart-legend__item${isHidden ? ' is-hidden' : ''}`}
            onClick={onToggle ? () => onToggle(item.key) : undefined}
            disabled={!onToggle}
            title={onToggle ? 'Click to show or hide' : undefined}
          >
            <span className="chart-legend__swatch" style={{ background: item.color }} />
            {item.label}
          </button>
        )
      })}
    </div>
  )
}

/** A muted message shown when a chart has nothing to draw. */
export function NoData({ message = 'No data in this range yet.' }) {
  return <div className="chart-empty text-muted">{message}</div>
}
