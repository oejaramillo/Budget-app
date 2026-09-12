/**
 * Investments: holdings and their point-in-time valuations.
 *
 * @typedef {Object} Holding
 * @property {number} id
 * @property {string} symbol
 * @property {string} name
 * @property {'stock'|'etf'|'fund'|'bond'|'crypto'|'real_estate'|'other'} kind
 * @property {string} kind_display
 * @property {string} quantity              up to 10 decimal places
 * @property {string} cost_basis
 * @property {number} currency
 * @property {Currency} [currency_detail]
 * @property {number|null} account
 * @property {string|null} opened_date
 * @property {string} notes
 * @property {string} market_value          latest valuation, or cost basis
 * @property {string} unrealised_gain
 * @property {string} unrealised_gain_percent
 * @property {string|null} latest_valuation_date
 *
 * @typedef {Object} Valuation
 * @property {number} id
 * @property {number} holding
 * @property {string} valued_on
 * @property {string} value
 * @property {string} note
 *
 * @typedef {Object} Portfolio
 * @property {string|null} target_currency
 * @property {string} total_market_value
 * @property {string} total_cost_basis
 * @property {string} unrealised_gain
 * @property {string} unrealised_gain_percent
 * @property {number} holding_count
 * @property {Array<{kind: string, value: string, cost: string, count: number}>} by_kind
 * @property {Array<Object>} positions
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery, unwrapList } from './http'

/** @returns {Promise<Holding[]>} */
export const fetchHoldings = async () => {
  const response = await api.get(`${ENDPOINTS.holdings}${buildQuery({ page_size: PAGE_SIZE })}`)
  return unwrapList(response)
}

/**
 * @param {Partial<Holding>} data
 * @returns {Promise<Holding>}
 */
export const createHolding = async (data) => (await api.post(ENDPOINTS.holdings, data)).data

/**
 * @param {number} id
 * @param {Partial<Holding>} data
 * @returns {Promise<Holding>}
 */
export const updateHolding = async (id, data) =>
  (await api.patch(`${ENDPOINTS.holdings}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteHolding = async (id) => {
  await api.delete(`${ENDPOINTS.holdings}${id}/`)
}

/**
 * Portfolio totals, optionally converted into `target`.
 *
 * @param {string} [target]
 * @returns {Promise<Portfolio>}
 */
export const fetchPortfolio = async (target) =>
  (await api.get(`${ENDPOINTS.holdings}portfolio/${buildQuery({ target })}`)).data

/**
 * Total portfolio value per valuation date.
 *
 * @returns {Promise<Array<{date: string, value: string}>>}
 */
export const fetchPortfolioHistory = async () =>
  (await api.get(`${ENDPOINTS.holdings}history/`)).data

/**
 * @param {{holding: number, valued_on: string, value: string, note?: string}} data
 * @returns {Promise<Valuation>}
 */
export const createValuation = async (data) => (await api.post(ENDPOINTS.valuations, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteValuation = async (id) => {
  await api.delete(`${ENDPOINTS.valuations}${id}/`)
}
