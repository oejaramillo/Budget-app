/**
 * Authentication: registration, login, token lifecycle and the current profile.
 *
 * @typedef {Object} Credentials
 * @property {string} username
 * @property {string} password
 *
 * @typedef {Object} RegistrationData
 * @property {string} username
 * @property {string} password
 * @property {string} password_confirm
 * @property {string} [email]
 *
 * @typedef {Object} User
 * @property {number} id
 * @property {string} username
 * @property {string} email
 * @property {boolean} is_staff
 */

import api from '../api'
import { ENDPOINTS } from '../constants'

/**
 * @param {RegistrationData} data
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export const register = (data) => api.post(ENDPOINTS.register, data)

/**
 * @param {Credentials} credentials
 * @returns {Promise<import('axios').AxiosResponse<{access: string, refresh: string}>>}
 */
export const login = (credentials) => api.post(ENDPOINTS.login, credentials)

/**
 * @returns {Promise<import('axios').AxiosResponse<User>>}
 */
export const fetchCurrentUser = () => api.get(ENDPOINTS.me)

/**
 * @param {Partial<User>} data
 * @returns {Promise<import('axios').AxiosResponse<User>>}
 */
export const updateCurrentUser = (data) => api.patch(ENDPOINTS.me, data)

/** Unauthenticated liveness probe. */
export const checkHealth = () => api.get(ENDPOINTS.health)
