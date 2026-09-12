/**
 * Axios instance shared by every service.
 *
 * Responsibilities:
 *  - prefix requests with `VITE_API_URL`;
 *  - attach the JWT access token;
 *  - transparently refresh an expired access token once, then replay the request;
 *  - redirect to the login screen when the session is genuinely over.
 *
 * Keeping the refresh logic here means no component ever has to think about
 * token lifetime.
 */

import axios from 'axios'
import { ACCESS_TOKEN, ENDPOINTS, REFRESH_TOKEN } from './constants'

const baseURL = import.meta.env.VITE_API_URL

if (!baseURL) {
  // Surfacing this early beats a confusing 404 in the console.
  console.warn(
    '[api] VITE_API_URL is not set. Copy frontend/.env.example to frontend/.env.'
  )
}

const api = axios.create({ baseURL })

/** Handlers invoked when the session cannot be recovered. */
const sessionExpiredListeners = new Set()

/**
 * Register a callback fired when the refresh token is rejected.
 * @param {() => void} listener
 * @returns {() => void} unsubscribe function
 */
export function onSessionExpired(listener) {
  sessionExpiredListeners.add(listener)
  return () => sessionExpiredListeners.delete(listener)
}

function notifySessionExpired() {
  clearStoredTokens()
  sessionExpiredListeners.forEach((listener) => listener())
}

/** @returns {string | null} */
export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN)
}

/** @returns {string | null} */
export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN)
}

/**
 * Persist a JWT pair.
 * @param {{ access?: string, refresh?: string }} tokens
 */
export function storeTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_TOKEN, access)
  if (refresh) localStorage.setItem(REFRESH_TOKEN, refresh)
}

export function clearStoredTokens() {
  localStorage.removeItem(ACCESS_TOKEN)
  localStorage.removeItem(REFRESH_TOKEN)
}

// --- Request: attach the access token ---------------------------------------
api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Response: refresh once on 401, then replay ------------------------------
let refreshInFlight = null

function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return Promise.reject(new Error('No refresh token stored.'))

  // Share a single refresh call between concurrent 401s.
  if (!refreshInFlight) {
    refreshInFlight = axios
      .post(`${baseURL}${ENDPOINTS.refresh}`, { refresh })
      .then((response) => {
        storeTokens(response.data)
        return response.data.access
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error
    const isAuthEndpoint =
      config?.url?.includes('/auth/login/') || config?.url?.includes('/auth/refresh/')

    if (response?.status === 401 && config && !config.__isRetry && !isAuthEndpoint) {
      try {
        const access = await refreshAccessToken()
        config.__isRetry = true
        config.headers.Authorization = `Bearer ${access}`
        return api(config)
      } catch {
        notifySessionExpired()
      }
    }

    return Promise.reject(error)
  }
)

/**
 * Turn any axios error into a message worth showing a human.
 * @param {unknown} error
 * @returns {string}
 */
export function describeApiError(error) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Unexpected error.'
  }
  if (error.code === 'ERR_NETWORK') {
    return 'Cannot reach the server. Is the backend running?'
  }

  const data = error.response?.data
  if (!data) return `Request failed (${error.response?.status ?? 'no response'}).`
  if (typeof data === 'string') return data

  // DRF returns {field: ["message"], ...} or {detail: "..."}.
  const parts = Object.entries(data).map(([field, value]) => {
    const text = Array.isArray(value) ? value.join(' ') : String(value)
    return field === 'detail' || field === 'non_field_errors' ? text : `${field}: ${text}`
  })
  return parts.join('\n') || 'Request failed.'
}

export default api
