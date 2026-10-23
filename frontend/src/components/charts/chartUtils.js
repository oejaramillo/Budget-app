/**
 * Chart helpers — no JSX here, so this stays a `.js` module.
 *
 * A charting library would add 100–200 kB for six chart types, and each one needs
 * the same three things: a scale, ticks and a tooltip. `ChartPrimitives.jsx` holds
 * the rendering pieces.
 */

import { useEffect, useRef, useState } from 'react'

/** Axis and grid colours, shared so every chart looks consistent. */
export const AXIS_COLOR = '#adb5bd'
export const GRID_COLOR = '#eef0f2'

/** A colour ramp that stays distinguishable in greyscale and for colour blindness. */
export const CATEGORY_COLORS = [
  '#fb8500',
  '#219ebc',
  '#8ecae6',
  '#023047',
  '#52b788',
  '#ffb703',
  '#d62828',
  '#6a4c93',
  '#2a9d8f',
  '#e76f51',
  '#457b9d',
  '#b5179e',
]

/** Stable colour for the nth series, so a category keeps its colour between views. */
export function colorFor(index) {
  return CATEGORY_COLORS[index % CATEGORY_COLORS.length]
}

/**
 * Measure the element a chart renders into, so charts are responsive rather than
 * assuming a fixed width.
 */
export function useChartSize(fallbackWidth = 640, fallbackHeight = 260) {
  const ref = useRef(null)
  const [size, setSize] = useState({ width: fallbackWidth, height: fallbackHeight })

  useEffect(() => {
    const element = ref.current
    if (!element) return undefined

    const measure = () => {
      const rect = element.getBoundingClientRect()
      if (rect.width > 0) {
        setSize({ width: Math.floor(rect.width), height: Math.floor(rect.height) })
      }
    }
    measure()

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure)
      return () => window.removeEventListener('resize', measure)
    }
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return [ref, size]
}

/** Highlighted series index for hover-driven tooltips. */
export function useHover() {
  const [index, setIndex] = useState(null)
  return [index, setIndex]
}

/** Compact axis labels: 12 400 -> "12.4k", so ticks stay readable. */
export function compactNumber(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return ''
  const absolute = Math.abs(numeric)
  if (absolute >= 1_000_000) return `${(numeric / 1_000_000).toFixed(1)}M`
  if (absolute >= 1_000) return `${(numeric / 1_000).toFixed(absolute >= 10_000 ? 0 : 1)}k`
  return String(Math.round(numeric))
}

/**
 * A "nice" upper bound and step for an axis, so ticks land on round numbers
 * instead of 13 742.
 */
export function niceScale(max, ticks = 4) {
  if (!Number.isFinite(max) || max <= 0) return { max: 1, step: 0.25 }
  const rough = max / ticks
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const residual = rough / magnitude
  const step = (residual >= 5 ? 10 : residual >= 2 ? 5 : residual >= 1 ? 2 : 1) * magnitude
  return { max: step * ticks, step }
}

/**
 * Downsample a long series so a chart never renders more points than it has pixels.
 * Keeps the final point, which is the one people look at.
 */
export function thin(values, maxPoints) {
  if (values.length <= maxPoints) return values
  const stride = Math.ceil(values.length / maxPoints)
  const kept = values.filter((_, index) => index % stride === 0)
  const last = values[values.length - 1]
  if (kept[kept.length - 1] !== last) kept.push(last)
  return kept
}
