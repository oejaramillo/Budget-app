/**
 * Date and number formatting.
 *
 * Two rules this module exists to enforce:
 *
 * 1. **Dates are always shown as DD/MM/YYYY**, independent of the browser locale.
 *    `09/08/2026` means 9 August here; letting the browser decide the order would
 *    silently swap day and month for some users.
 *
 * 2. **A calendar date never shifts timezone.** `new Date('2026-09-08')` is parsed
 *    as *UTC* midnight, so anywhere behind UTC shows it as 7 September. Date-only
 *    values are parsed field by field into a local date instead. Only real instants
 *    (timestamps returned by the API) go through `new Date()`.
 */

/** Shown when a value cannot be interpreted. */
const EMPTY = '—'

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

/** Matches the leading `YYYY-MM-DD` of a date or datetime string. */
const DATE_ONLY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})/

/**
 * Parse a `YYYY-MM-DD` value into a **local** Date at midnight.
 *
 * @param {string|null|undefined} value
 * @returns {Date|null} null when the value is not a calendar date
 */
export function parseLocalDate(value) {
  const match = DATE_ONLY_PATTERN.exec(String(value ?? '').trim())
  if (!match) return null

  const [, year, month, day] = match
  const date = new Date(Number(year), Number(month) - 1, Number(day))
  // Reject impossible dates, which would otherwise roll forward (2026-02-31 → 3 March).
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    return null
  }
  return date
}

/**
 * True when a value carries a time component, i.e. it is a real instant.
 * @param {string|null|undefined} value
 */
export function hasTimeComponent(value) {
  return /\d{2}:\d{2}/.test(String(value ?? ''))
}

/**
 * Format a date as `DD/MM/YYYY`.
 *
 * Date-only values are calendar dates and never shift. Timestamps are real
 * instants and are rendered in the viewer's local time.
 *
 * @param {string|Date|null|undefined} value
 * @returns {string}
 */
export function formatDate(value) {
  if (!value) return EMPTY

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? EMPTY : DATE_FORMATTER.format(value)
  }

  const text = String(value).trim()
  const local = parseLocalDate(text)
  if (local) return DATE_FORMATTER.format(local)

  const parsed = new Date(text)
  return Number.isNaN(parsed.getTime()) ? text : DATE_FORMATTER.format(parsed)
}

/**
 * Format a timestamp as `DD/MM/YYYY HH:mm` in local time.
 * Use for `created_date`, `started_at`, `last_login` and similar.
 *
 * @param {string|Date|null|undefined} value
 * @returns {string}
 */
export function formatDateTime(value) {
  if (!value) return EMPTY
  const parsed = value instanceof Date ? value : new Date(String(value))
  if (Number.isNaN(parsed.getTime())) return formatDate(value)
  return DATE_TIME_FORMATTER.format(parsed)
}

/**
 * Render a value for an `<input type="date">`, which requires `YYYY-MM-DD`.
 *
 * Never derive this with `new Date(...).toISOString()` — that converts to UTC and
 * shifts the day. The leading ten characters of an ISO value are already right.
 *
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function toDateInput(value) {
  if (!value) return ''
  const match = DATE_ONLY_PATTERN.exec(String(value).trim())
  return match ? match[0] : ''
}

/**
 * Format a decimal string as money without doing float arithmetic.
 *
 * The value arrives from the API as a decimal string (for example "1234.50").
 * `Intl.NumberFormat` parses it for display only; no rounding decisions are made on
 * the client.
 *
 * @param {string|number|null|undefined} value
 * @param {string} [currencyCode]
 * @returns {string}
 */
export function formatMoney(value, currencyCode) {
  if (value === null || value === undefined || value === '') return EMPTY
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
 * Format a percentage value that already arrived as a number.
 * @param {number|string|null|undefined} value
 * @param {number} [digits]
 * @returns {string}
 */
export function formatPercent(value, digits = 2) {
  if (value === null || value === undefined || value === '') return EMPTY
  const numeric = Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return `${numeric.toFixed(digits)}%`
}

/** @param {Date} date */
export function toIsoDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/**
 * Today as `YYYY-MM-DD` in **local** time, for pre-filling date inputs.
 * `toISOString()` would return yesterday for anyone west of UTC late in the day.
 */
export function today() {
  return toIsoDate(new Date())
}

/** First and last day of the current month as `YYYY-MM-DD`. */
export function currentMonthRange() {
  const now = new Date()
  const first = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { start: first, end: toIsoDate(last) }
}
