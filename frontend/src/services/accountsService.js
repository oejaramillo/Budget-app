/**
 * Accounts: containers for money (bank, cash, card, investment, ...).
 *
 * @typedef {Object} Account
 * @property {number} id
 * @property {string} name
 * @property {'checking'|'savings'|'credit'|'cash'|'investment'|'loan'|'other'} account_type
 * @property {string} account_type_display
 * @property {string} balance            Decimal serialised as a string
 * @property {number} currency           Currency id
 * @property {Currency} [currency_detail]
 * @property {string} institution
 * @property {string} official_number
 * @property {boolean} is_active
 * @property {string} created_date
 * @property {string} last_updated
 *
 * @typedef {Object} AccountInput
 * @property {string} name
 * @property {string} account_type
 * @property {number} currency
 * @property {string} [institution]
 * @property {string} [official_number]
 * @property {boolean} [is_active]
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery, fetchAllPages, unwrapList } from './http'

/** @returns {Promise<Account[]>} */
export const fetchAccounts = async () => {
  const response = await api.get(`${ENDPOINTS.accounts}${buildQuery({ page_size: PAGE_SIZE })}`)
  return unwrapList(response)
}

/**
 * @param {number} id
 * @returns {Promise<Account>}
 */
export const fetchAccount = async (id) => (await api.get(`${ENDPOINTS.accounts}${id}/`)).data

/**
 * @param {AccountInput} data
 * @returns {Promise<Account>}
 */
export const createAccount = async (data) => (await api.post(ENDPOINTS.accounts, data)).data

/**
 * @param {number} id
 * @param {Partial<AccountInput>} data
 * @returns {Promise<Account>}
 */
export const updateAccount = async (id, data) =>
  (await api.patch(`${ENDPOINTS.accounts}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteAccount = async (id) => {
  await api.delete(`${ENDPOINTS.accounts}${id}/`)
}

/**
 * Set a balance explicitly (opening balance or reconciliation).
 * `PUT`/`PATCH` deliberately cannot change a balance: routine movements must come
 * from transactions so the ledger stays consistent.
 *
 * @param {number} id
 * @param {string} balance
 * @returns {Promise<Account>}
 */
export const adjustAccountBalance = async (id, balance) =>
  (await api.post(`${ENDPOINTS.accounts}${id}/adjust-balance/`, { balance })).data

/**
 * Net worth, either per currency or converted into `target`.
 *
 * @param {string} [target] ISO code, e.g. 'USD'
 * @returns {Promise<{per_currency: Array<{currency: string, total: string}>, target_currency: string|null, converted_total: string|null}>}
 */
export const fetchNetWorth = async (target) =>
  (await api.get(`${ENDPOINTS.accounts}net-worth/${buildQuery({ target })}`)).data

/**
 * Every account balance, with an optional converted reference value.
 *
 * @param {string} [target]
 * @returns {Promise<Array<{account_id: number, account_name: string, currency: string, balance: string, reference_balance: string|null, reference_currency: string|null}>>}
 */
export const fetchAccountBalances = (target) =>
  fetchAllPages(
    (url) => api.get(url),
    `${ENDPOINTS.accounts}balances/${buildQuery({ target })}`
  )
