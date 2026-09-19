/**
 * Transactions and the reporting endpoints built on top of them.
 *
 * @typedef {Object} Transaction
 * @property {number} id
 * @property {number} account
 * @property {Account} [account_detail]
 * @property {number|null} destination_account
 * @property {Account} [destination_account_detail]
 * @property {'income'|'expense'|'transfer'} transaction_type
 * @property {string} transaction_type_display
 * @property {string} transaction_date      YYYY-MM-DD
 * @property {string} amount                 always positive
 * @property {string} signed_amount          negative for expense/transfer
 * @property {number} currency
 * @property {Currency} [currency_detail]
 * @property {string|null} exchange_rate
 * @property {string} description
 * @property {number|null} category
 * @property {Category|null} [category_detail]
 * @property {number|null} budget
 * @property {string} created_date
 *
 * @typedef {Object} TransactionInput
 * @property {number} account
 * @property {'income'|'expense'|'transfer'} transaction_type
 * @property {string} transaction_date       YYYY-MM-DD
 * @property {string} amount                 decimal string, > 0
 * @property {string} [description]
 * @property {number|null} [category]
 * @property {number|null} [budget]
 * @property {number} [currency]             defaults to the account currency
 * @property {number|null} [destination_account] required for transfers
 * @property {string|null} [exchange_rate]   required when currency differs
 *
 * @typedef {Object} TransactionFilters
 * @property {number} [account]
 * @property {string} [transaction_type]
 * @property {number} [category]
 * @property {number} [budget]
 * @property {string} [search]        matches description, account and category
 * @property {string} [date_from]
 * @property {string} [date_to]
 * @property {string} [month]         YYYY-MM shorthand
 * @property {boolean} [uncategorised]
 * @property {string} [ordering]      e.g. '-transaction_date'
 * @property {number} [page]
 * @property {number} [page_size]
 *
 * @typedef {Object} DescriptionSuggestion
 * @property {string} description
 * @property {number} uses
 * @property {string} last_used
 *
 * @typedef {Object} TransactionSummary
 * @property {string} period_start
 * @property {string} period_end
 * @property {string|null} currency
 * @property {string} total_income
 * @property {string} total_expenses
 * @property {string} net
 * @property {number} transaction_count
 * @property {Array<{category_id: number|null, category_name: string, total: string, count: number}>} by_category
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery } from './http'

/**
 * One page of transactions, newest first by default.
 *
 * Returns the whole envelope (`count`, `next`, `previous`, `results`) rather than
 * only the rows: the transaction list is the one screen that needs real pagination,
 * because a ledger can hold tens of thousands of entries.
 *
 * @param {TransactionFilters} [filters]
 * @returns {Promise<{count: number, next: string|null, previous: string|null, results: Transaction[]}>}
 */
export const fetchTransactionsPage = async (filters = {}) => {
  const response = await api.get(
    `${ENDPOINTS.transactions}${buildQuery({ page_size: PAGE_SIZE, ...filters })}`
  )
  return response.data
}

/**
 * Convenience wrapper returning only the rows of the first page.
 * @param {TransactionFilters} [filters]
 * @returns {Promise<Transaction[]>}
 */
export const fetchTransactions = async (filters = {}) => {
  const page = await fetchTransactionsPage(filters)
  return Array.isArray(page) ? page : page.results
}

/**
 * Descriptions the user has typed before, most used first — the autocomplete source
 * for the logging form.
 *
 * @param {{q?: string, account?: number, limit?: number}} [params]
 * @returns {Promise<DescriptionSuggestion[]>}
 */
export const fetchDescriptionSuggestions = async (params = {}) =>
  (await api.get(`${ENDPOINTS.transactionDescriptions}${buildQuery(params)}`)).data

/**
 * The user's latest transactions, for one-tap repeat entry.
 * @param {number} [limit]
 * @returns {Promise<Transaction[]>}
 */
export const fetchRecentTransactions = async (limit = 8) =>
  (await api.get(`${ENDPOINTS.transactionRecent}${buildQuery({ limit })}`)).data

/** A few facts about the ledger, for the logging screen header. */
export const fetchLedgerStats = async () =>
  (await api.get(`${ENDPOINTS.transactionStats}`)).data

/**
 * @param {TransactionInput} data
 * @returns {Promise<Transaction>}
 */
export const createTransaction = async (data) =>
  (await api.post(ENDPOINTS.transactions, data)).data

/**
 * Create several transactions in one atomic request (fast daily entry).
 *
 * @param {TransactionInput[]} data
 * @returns {Promise<Transaction[]>}
 */
export const createTransactionsBulk = async (data) =>
  (await api.post(`${ENDPOINTS.transactions}bulk/`, data)).data

/**
 * @param {number} id
 * @param {Partial<TransactionInput>} data
 * @returns {Promise<Transaction>}
 */
export const updateTransaction = async (id, data) =>
  (await api.patch(`${ENDPOINTS.transactions}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteTransaction = async (id) => {
  await api.delete(`${ENDPOINTS.transactions}${id}/`)
}

/**
 * Income, expenses, net and per-category breakdown for a date range.
 *
 * @param {Object} [params]
 * @param {string} [params.start] YYYY-MM-DD
 * @param {string} [params.end] YYYY-MM-DD
 * @param {string} [params.target] currency code to convert into
 * @returns {Promise<TransactionSummary>}
 */
export const fetchTransactionSummary = async (params = {}) =>
  (await api.get(`${ENDPOINTS.transactions}summary/${buildQuery(params)}`)).data

/**
 * Income/expense totals grouped by month.
 *
 * @param {number} [months]
 * @returns {Promise<Array<{month: string, income: string, expenses: string, net: string, count: number}>>}
 */
export const fetchMonthlyTotals = async (months = 6) =>
  (await api.get(`${ENDPOINTS.transactions}monthly/${buildQuery({ months })}`)).data
