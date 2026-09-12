/**
 * Superuser console: maintenance operations, system overview and tenant admin.
 *
 * Every call here is gated by `IsSuperUser` on the backend; `is_staff` is not
 * enough. The frontend hides the console from non-superusers for usability, but
 * the API is what actually enforces it.
 *
 * @typedef {Object} OperationField
 * @property {string} name
 * @property {string} label
 * @property {'string'|'integer'|'boolean'|'select'} type
 * @property {boolean} required
 * @property {any} default
 * @property {string} help_text
 * @property {Array<{value: string, label: string}>} choices
 * @property {string} caution
 *
 * @typedef {Object} OperationSpec
 * @property {string} key
 * @property {string} label
 * @property {string} description
 * @property {'read'|'mutate'|'destructive'} safety
 * @property {string} group
 * @property {OperationField[]} fields
 * @property {boolean} allowed
 * @property {string} blocked_reason
 *
 * @typedef {Object} OperationRun
 * @property {number} id
 * @property {string} operation
 * @property {Object} arguments
 * @property {'running'|'success'|'failed'|'skipped'} status
 * @property {string} output
 * @property {string} error
 * @property {Object|null} result
 * @property {number|null} duration_ms
 * @property {string} started_at
 * @property {string} finished_at
 * @property {string|null} triggered_by_username
 *
 * @typedef {Object} Tenant
 * @property {number} id
 * @property {string} username
 * @property {string} email
 * @property {string} first_name
 * @property {string} last_name
 * @property {boolean} is_active
 * @property {boolean} is_staff
 * @property {boolean} is_superuser
 * @property {string} date_joined
 * @property {string|null} last_login
 * @property {number} account_count
 * @property {number} transaction_count
 * @property {number} holding_count
 */

import api from '../api'
import { OPS_ENDPOINTS } from '../constants'
import { buildQuery, unwrapList } from './http'

/** Dashboard data for the console: stats, integrity, rates, registry, apps. */
export const fetchOpsOverview = async () => (await api.get(OPS_ENDPOINTS.overview)).data

/** Every operation the backend allows, with its declared input fields. */
export const fetchOperations = async () =>
  unwrapList(await api.get(OPS_ENDPOINTS.operations))

/**
 * Run one operation. `arguments` is validated again on the backend.
 *
 * @param {string} key
 * @param {Object} [args]
 * @returns {Promise<OperationRun>}
 */
export const runOperation = async (key, args = {}) =>
  (await api.post(`${OPS_ENDPOINTS.operations}${key}/run/`, { arguments: args })).data

/**
 * Recent runs, newest first.
 *
 * @param {{operation?: string, status?: string}} [filters]
 * @returns {Promise<OperationRun[]>}
 */
export const fetchRunHistory = async (filters = {}) =>
  unwrapList(await api.get(`${OPS_ENDPOINTS.history}${buildQuery(filters)}`))

/** Read the console's safety switches. */
export const fetchOpsSettings = async () => (await api.get(OPS_ENDPOINTS.settings)).data

/**
 * Update the safety switches.
 * @param {{allow_mutating_operations?: boolean, allow_destructive_operations?: boolean}} data
 */
export const updateOpsSettings = async (data) =>
  (await api.patch(OPS_ENDPOINTS.settings, data)).data

/**
 * Tenants with their data footprint.
 * @param {{search?: string, page_size?: number}} [params]
 * @returns {Promise<Tenant[]>}
 */
export const fetchTenants = async (params = {}) =>
  unwrapList(await api.get(`${OPS_ENDPOINTS.tenants}${buildQuery(params)}`))

/** Headline tenant counts. */
export const fetchTenantsSummary = async () =>
  (await api.get(OPS_ENDPOINTS.tenantsSummary)).data

/**
 * Change a tenant's flags.
 * @param {number} id
 * @param {{is_active?: boolean, is_staff?: boolean, is_superuser?: boolean}} data
 * @returns {Promise<Tenant>}
 */
export const updateTenant = async (id, data) =>
  (await api.patch(`${OPS_ENDPOINTS.tenants}${id}/`, data)).data

/**
 * Administrative password reset.
 * @param {number} id
 * @param {string} newPassword
 */
export const setTenantPassword = async (id, newPassword) =>
  (await api.post(`${OPS_ENDPOINTS.tenants}${id}/set-password/`, { new_password: newPassword }))
    .data

/**
 * Delete a tenant and everything they own. The username must be typed back.
 * @param {number} id
 * @param {string} username
 */
export const deleteTenant = async (id, username) =>
  (await api.delete(`${OPS_ENDPOINTS.tenants}${id}/`, { data: { confirm_username: username } }))
    .data
