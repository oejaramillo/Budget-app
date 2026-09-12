/**
 * Categories: user-defined labels, optionally attached to a budget.
 *
 * @typedef {Object} Category
 * @property {number} id
 * @property {string} name
 * @property {number|null} budget
 * @property {boolean} is_active
 * @property {number} [transaction_count]
 *
 * @typedef {Object} CategoryInput
 * @property {string} name
 * @property {number|null} [budget]
 * @property {boolean} [is_active]
 */

import api from '../api'
import { ENDPOINTS, PAGE_SIZE } from '../constants'
import { buildQuery, unwrapList } from './http'

/** @returns {Promise<Category[]>} */
export const fetchCategories = async () => {
  const response = await api.get(
    `${ENDPOINTS.categories}${buildQuery({ page_size: PAGE_SIZE })}`
  )
  return unwrapList(response)
}

/**
 * @param {CategoryInput} data
 * @returns {Promise<Category>}
 */
export const createCategory = async (data) => (await api.post(ENDPOINTS.categories, data)).data

/**
 * @param {number} id
 * @param {Partial<CategoryInput>} data
 * @returns {Promise<Category>}
 */
export const updateCategory = async (id, data) =>
  (await api.patch(`${ENDPOINTS.categories}${id}/`, data)).data

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export const deleteCategory = async (id) => {
  await api.delete(`${ENDPOINTS.categories}${id}/`)
}
