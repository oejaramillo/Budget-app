/** Small presentational helpers reused across the app. */

/**
 * Format a decimal string as money without ever doing float arithmetic.
 *
 * The value arrives from the API as a decimal string (for example "1234.50").
 * `Intl.NumberFormat` parses it for display only; no rounding decisions are made
 * on the client.
 *
 * @param {string|number|null|undefined} value
 * @param {string} [currencyCode]
 * @returns {string}
 */
export function formatMoney(value, currencyCode) {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)

  if (currencyCode && currencyCode.length === 3) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: currencyCode,
        currencyDisplay: 'code',
      }).format(numeric)
    } catch {
      // Fall through to plain formatting for non-ISO codes.
    }
  }
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric)
}

/**
 * Format an ISO date (or datetime) for display.
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString()
}

/**
 * Format a percentage value that already arrived as a number.
 * @param {number|string|null|undefined} value
 * @param {number} [digits]
 * @returns {string}
 */
export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return `${numeric.toFixed(digits)}%`
}

/** First and last day of the current month as YYYY-MM-DD. */
export function currentMonthRange() {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth(), 1)
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { start: toIsoDate(first), end: toIsoDate(last) }
}

/** @param {Date} date */
export function toIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

/** Today as YYYY-MM-DD. */
export function today() {
  return toIsoDate(new Date())
}
