/**
 * Spending analytics.
 *
 * @typedef {Object} Totals
 * @property {number} income
 * @property {number} expenses          everything, including money movement
 * @property {number} consumption       what was actually spent
 * @property {number} money_movement    transfers, loans, currency exchange
 * @property {number} net
 * @property {number} net_consumption
 * @property {number} transaction_count
 * @property {number|null} savings_rate
 * @property {number|null} expense_ratio
 *
 * @typedef {Object} Comparison
 * @property {number} current
 * @property {number} previous
 * @property {number} change
 * @property {number|null} change_percent
 *
 * @typedef {Object} CategoryRow
 * @property {number|null} category_id
 * @property {string} category
 * @property {number} total
 * @property {number} count
 * @property {number} average
 * @property {boolean} is_money_movement
 *
 * @typedef {Object} MonthRow
 * @property {string} month
 * @property {string} label
 * @property {number} income
 * @property {number} consumption
 * @property {number} money_movement
 * @property {number} expenses
 * @property {number} net
 * @property {number} count
 * @property {number|null} savings_rate
 *
 * @typedef {Object} SpendingOutlook
 * @property {string} month
 * @property {string} label
 * @property {number} days_elapsed
 * @property {number} days_in_month
 * @property {number} spent_so_far
 * @property {number} daily_pace
 * @property {number} projected_month_end
 * @property {number} typical_month
 * @property {number|null} monthly_spread
 * @property {'high'|'low'|'normal'|'in_progress'} verdict
 * @property {number} months_compared
 * @property {number|null} budget_remaining_to_typical
 *
 * @typedef {Object} Insight
 * @property {'warning'|'good'|'neutral'} tone
 * @property {string} title
 * @property {string} detail
 * @property {number} value
 */

import api from '../api'
import { ENDPOINTS } from '../constants'
import { buildQuery } from './http'

/**
 * Everything the spending dashboard needs, in one request.
 *
 * @param {{currency?: string, months?: number}} [params]
 * @returns {Promise<Object>}
 */
export const fetchAnalyticsDashboard = async (params = {}) =>
  (await api.get(`${ENDPOINTS.analyticsDashboard}${buildQuery(params)}`)).data

/**
 * Totals and categories for one period, compared with the one before it.
 *
 * @param {'month'|'quarter'|'year'} granularity
 * @param {string} [anchor] `YYYY-MM`, `YYYY-QN` or `YYYY`
 * @param {string} [currency]
 */
export const fetchPeriodAnalytics = async (granularity, anchor, currency) =>
  (
    await api.get(
      `${ENDPOINTS.analyticsPeriod}${buildQuery({ granularity, anchor, currency })}`
    )
  ).data

/**
 * Monthly income/consumption series.
 * @param {{months?: number, currency?: string}} [params]
 */
export const fetchTrend = async (params = {}) =>
  (await api.get(`${ENDPOINTS.analyticsTrend}${buildQuery(params)}`)).data

/**
 * Per-category consumption over time.
 * @param {{months?: number, currency?: string}} [params]
 */
export const fetchCategoryTrend = async (params = {}) =>
  (await api.get(`${ENDPOINTS.analyticsCategories}${buildQuery(params)}`)).data

/** Costs that repeat nearly every month. */
export const fetchRecurring = async (currency) =>
  (await api.get(`${ENDPOINTS.analyticsRecurring}${buildQuery({ currency })}`)).data

/** Current-month pace and projection. */
export const fetchSpendingOutlook = async (currency) =>
  (await api.get(`${ENDPOINTS.analyticsSpending}${buildQuery({ currency })}`)).data
