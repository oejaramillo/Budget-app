/**
 * Date formatting guarantees.
 *
 * These are plain assertions against the pure helpers, run by `npm run test:dates`
 * under a non-UTC timezone (`TZ=America/Guayaquil`, UTC-5). That timezone is the
 * point: the bug these tests lock down was invisible in UTC and shifted every
 * transaction date back by one day everywhere west of Greenwich.
 */

import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  formatDate,
  formatDateTime,
  hasTimeComponent,
  parseLocalDate,
  toDateInput,
  toIsoDate,
  today,
} from '../src/utils/format.js'

test('a date-only value is not shifted by the timezone', () => {
  // The regression: `new Date('2026-09-08')` is UTC midnight, which is
  // 7 September 19:00 in UTC-5, so the table used to show the wrong day.
  assert.equal(formatDate('2026-09-08'), '08/09/2026')
  assert.equal(formatDate('2026-01-01'), '01/01/2026')
  assert.equal(formatDate('2026-12-31'), '31/12/2026')
})

test('dates are always day-first, regardless of locale', () => {
  // 09/08/2026 must mean 9 August, never 8 September.
  assert.equal(formatDate('2026-08-09'), '09/08/2026')
  assert.equal(formatDate('2026-09-08'), '08/09/2026')
})

test('the day is preserved across a range of dates', () => {
  for (const iso of ['2024-02-29', '2025-03-01', '2026-07-04', '2026-11-30']) {
    const [year, month, day] = iso.split('-')
    assert.equal(formatDate(iso), `${day}/${month}/${year}`)
  }
})

test('a datetime value is shown in local time with its time', () => {
  // 2026-09-08T02:30:00Z is 7 September 21:30 in UTC-5 — a real instant, so it
  // legitimately belongs to the previous local day.
  assert.equal(formatDateTime('2026-09-08T02:30:00Z'), '07/09/2026, 21:30')
  // 2026-09-08T18:00:00Z is 13:00 the same day in UTC-5.
  assert.equal(formatDateTime('2026-09-08T18:00:00Z'), '08/09/2026, 13:00')
})

test('hasTimeComponent distinguishes dates from instants', () => {
  assert.equal(hasTimeComponent('2026-09-08'), false)
  assert.equal(hasTimeComponent('2026-09-08T02:30:00Z'), true)
})

test('toDateInput returns a value an <input type="date"> accepts', () => {
  assert.equal(toDateInput('2026-09-08'), '2026-09-08')
  // A datetime is truncated to its date, never converted to UTC first.
  assert.equal(toDateInput('2026-09-08T02:30:00Z'), '2026-09-08')
  assert.equal(toDateInput(null), '')
  assert.equal(toDateInput('not a date'), '')
})

test('today() is the local calendar day, not the UTC one', () => {
  const expected = toIsoDate(new Date())
  assert.equal(today(), expected)
  // Late in the local day, `toISOString()` would already be tomorrow or yesterday.
  const now = new Date()
  const utcDay = now.toISOString().slice(0, 10)
  assert.equal(today().slice(8, 10), String(now.getDate()).padStart(2, '0'))
  // Both can differ in UTC-5; the local one is what we must report.
  if (utcDay !== today()) {
    assert.equal(today(), expected)
  }
})

test('impossible dates are rejected rather than silently rolled forward', () => {
  // 31 February does not exist; the parser must say so instead of returning 3 March.
  assert.equal(parseLocalDate('2026-02-31'), null)
  assert.equal(parseLocalDate('2026-13-01'), null)
  assert.equal(parseLocalDate('2026-02-28') instanceof Date, true)
})

test('non-date values are passed through or blanked, never invented', () => {
  assert.equal(formatDate(null), '—')
  assert.equal(formatDate(''), '—')
  assert.equal(formatDate('whenever'), 'whenever')
})
