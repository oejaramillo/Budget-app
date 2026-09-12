/* eslint-disable react-refresh/only-export-components --
   The context, its provider and its consumer hook belong together; splitting them
   across files would only add indirection. Fast Refresh still works, a full
   reload is just triggered when this file changes. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { clearStoredTokens, getAccessToken, onSessionExpired, storeTokens } from '../api'
import { fetchCurrentUser, login as loginRequest, register as registerRequest } from '../services/authService'

/**
 * @typedef {Object} AuthUser
 * @property {number} id
 * @property {string} username
 * @property {string} email
 * @property {boolean} is_staff
 *
 * @typedef {Object} AuthContextValue
 * @property {AuthUser|null} user
 * @property {boolean} isAuthenticated
 * @property {boolean} isLoading
 * @property {(credentials: {username: string, password: string}) => Promise<any>} login
 * @property {(data: {username: string, password: string, password_confirm: string, email?: string}) => Promise<any>} register
 * @property {() => void} logout
 */

/** @type {React.Context<AuthContextValue|undefined>} */
const AuthContext = createContext(undefined)

/**
 * Access the auth context. Throws when used outside `AuthProvider`, which turns a
 * confusing "undefined is not a function" into an obvious error.
 * @returns {AuthContextValue}
 */
export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used inside <AuthProvider>')
  }
  return context
}

/**
 * Holds the session.
 *
 * On mount it restores the session from a stored token and verifies it against
 * `/auth/me/`. If the access token expired, the axios interceptor refreshes it
 * transparently; if that fails, the user is signed out.
 *
 * @param {{children: React.ReactNode}} props
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(/** @type {AuthUser|null} */ (null))
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    clearStoredTokens()
    setUser(null)
  }, [])

  // Restore the session once, then let the interceptor handle later refreshes.
  useEffect(() => {
    let cancelled = false

    async function restore() {
      if (!getAccessToken()) {
        if (!cancelled) setIsLoading(false)
        return
      }
      try {
        const response = await fetchCurrentUser()
        if (!cancelled) setUser(response.data)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  // The interceptor tells us when a refresh finally failed.
  useEffect(() => onSessionExpired(clearSession), [clearSession])

  const login = useCallback(async (credentials) => {
    const response = await loginRequest(credentials)
    storeTokens(response.data)
    const me = await fetchCurrentUser()
    setUser(me.data)
    return me.data
  }, [])

  const register = useCallback(
    async ({ username, password, password_confirm, email }) => {
      await registerRequest({ username, password, password_confirm, email })
      // Log the new tenant straight in so registration is one step.
      return login({ username, password })
    },
    [login]
  )

  const logout = useCallback(() => {
    clearSession()
  }, [clearSession])

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
