/**
 * Currencies and exchange rates.
 *
 * @typedef {Object} Currency
 * @property {number} id
 * @property {string} code
 * @property {string} name
 * @property {string} symbol
 * @property {string} exchange_rate      Decimal string
 * @property {boolean} principal         The app-wide reporting currency
 * @property {boolean} is_active
 * @property {string|null} rate_updated_at
 * @property {number|null} rate_age_hours
 *
 * @typedef {Object} CurrencySummaryRow
 * @property {string} currency_code
 * @property {string} currency_name
 * @property {string} total_balance
 * @property {number} account_count
 * @property {boolean} converted
 * @property {string|null} conversion_rate
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery, unwrapList } from './http'

/** @returns {Promise<Currency[]>} */
export const fetchCurrencies = async (params = {}) => {
  const response = await api.get(
    `${ENDPOINTS.currencies}${buildQuery({ page_size: PAGE_SIZE, ...params })}`
  )
  return unwrapList(response)
}

/**
 * @param {Partial<Currency>} data
 * @returns {Promise<Currency>}
 */
export const createCurrency = async (data) => (await api.post(ENDPOINTS.currencies, data)).data

/**
 * @param {number} id
 * @param {Partial<Currency>} data
 * @returns {Promise<Currency>}
 */
export const updateCurrency = async (id, data) =>
  (await api.patch(`${ENDPOINTS.currencies}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteCurrency = async (id) => {
  await api.delete(`${ENDPOINTS.currencies}${id}/`)
}

/**
 * Convert an amount between two currencies using the stored cross rate.
 *
 * @param {number} currencyId source currency id
 * @param {string} target ISO code
 * @param {string} amount decimal string
 */
export const convertAmount = async (currencyId, target, amount) =>
  (
    await api.get(
      `${ENDPOINTS.currencies}${currencyId}/convert/${buildQuery({ target, amount })}`
    )
  ).data

/**
 * Total balance per currency, optionally converted into `target`.
 *
 * @param {string} [target]
 * @returns {Promise<{target_currency: string|null, results: CurrencySummaryRow[]}>}
 */
export const fetchCurrencySummary = async (target) =>
  (await api.get(`${ENDPOINTS.currencies}summary/${buildQuery({ target })}`)).data

/**
 * Ask the backend to re-fetch rates from the provider. Staff accounts only.
 *
 * @returns {Promise<{source: string, updated: string[], created: string[], message: string}>}
 */
export const refreshExchangeRates = async (base) =>
  (await api.post(`${ENDPOINTS.currencies}refresh/`, base ? { base } : {})).data
