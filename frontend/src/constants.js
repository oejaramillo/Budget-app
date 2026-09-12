/**
 * All API path segments and localStorage keys in one place.
 *
 * The backend is versioned (`/api/v1`), so a future `/api/v2` only needs to
 * change `API_PREFIX` here instead of every service file.
 */

/** Base path of the REST API. */
export const API_PREFIX = '/api/v1'

/** localStorage keys used to persist the JWT pair. */
export const ACCESS_TOKEN = 'access'
export const REFRESH_TOKEN = 'refresh'

/** Endpoints consumed by the app. */
export const ENDPOINTS = {
  register: `${API_PREFIX}/auth/register/`,
  login: `${API_PREFIX}/auth/login/`,
  refresh: `${API_PREFIX}/auth/refresh/`,
  me: `${API_PREFIX}/auth/me/`,
  health: `${API_PREFIX}/health/`,

  currencies: `${API_PREFIX}/currencies/`,
  accounts: `${API_PREFIX}/accounts/`,
  budgets: `${API_PREFIX}/budgets/`,
  categories: `${API_PREFIX}/categories/`,
  transactions: `${API_PREFIX}/transactions/`,
  holdings: `${API_PREFIX}/holdings/`,
  valuations: `${API_PREFIX}/valuations/`,
}

/** Account types accepted by the backend, used to drive form selects. */
export const ACCOUNT_TYPES = [
  { value: 'checking', label: 'Checking' },
  { value: 'savings', label: 'Savings' },
  { value: 'credit', label: 'Credit card' },
  { value: 'cash', label: 'Cash' },
  { value: 'investment', label: 'Investment' },
  { value: 'loan', label: 'Loan' },
  { value: 'other', label: 'Other' },
]

/** Transaction types accepted by the backend. */
export const TRANSACTION_TYPES = [
  { value: 'income', label: 'Income' },
  { value: 'expense', label: 'Expense' },
  { value: 'transfer', label: 'Transfer' },
]

/** Default page size requested from paginated list endpoints. */
export const PAGE_SIZE = 100
