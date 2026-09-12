/**
 * Budgets: spending envelopes with a period, a limit and linked accounts.
 *
 * @typedef {Object} Budget
 * @property {number} id
 * @property {string} name
 * @property {string} min_amount
 * @property {string} max_amount
 * @property {string|null} [spent_amount]
 * @property {number} currency
 * @property {Currency} [currency_detail]
 * @property {string} start_date
 * @property {string} end_date
 * @property {number[]} accounts
 * @property {boolean} is_active
 * @property {boolean} [is_current]
 *
 * @typedef {Object} BudgetInput
 * @property {string} name
 * @property {string} min_amount
 * @property {string} max_amount
 * @property {number} currency
 * @property {string} start_date
 * @property {string} end_date
 * @property {number[]} [accounts]
 * @property {boolean} [is_active]
 *
 * @typedef {Object} BudgetStatus
 * @property {number} id
 * @property {string} name
 * @property {string} currency
 * @property {string} max_amount
 * @property {string} spent_amount
 * @property {string} remaining_amount
 * @property {number} percentage_used
 * @property {boolean} is_over_budget
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery, fetchAllPages, unwrapList } from './http'

/** @returns {Promise<Budget[]>} */
export const fetchBudgets = async () => {
  const response = await api.get(`${ENDPOINTS.budgets}${buildQuery({ page_size: PAGE_SIZE })}`)
  return unwrapList(response)
}

/**
 * @param {BudgetInput} data
 * @returns {Promise<Budget>}
 */
export const createBudget = async (data) => (await api.post(ENDPOINTS.budgets, data)).data

/**
 * @param {number} id
 * @param {Partial<BudgetInput>} data
 * @returns {Promise<Budget>}
 */
export const updateBudget = async (id, data) =>
  (await api.patch(`${ENDPOINTS.budgets}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteBudget = async (id) => {
  await api.delete(`${ENDPOINTS.budgets}${id}/`)
}

/**
 * Limit, spent, remaining and percentage for every active budget.
 * @returns {Promise<BudgetStatus[]>}
 */
export const fetchBudgetStatus = () =>
  fetchAllPages((url) => api.get(url), `${ENDPOINTS.budgets}status/`)
