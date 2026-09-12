import { useMutation, useQueryClient } from '@tanstack/react-query'

import { useAuthContext } from '../contexts/AuthContext'

/**
 * Convenience hook exposing the auth actions as React Query mutations, so callers
 * get `isPending` / `error` handling for free.
 *
 * The session state itself lives in `AuthProvider`
 * (`src/contexts/AuthContext.jsx`); re-exported here so components have a single
 * import path.
 */
export function useAuth() {
  const queryClient = useQueryClient()
  const { login: loginFn, register: registerFn, logout: logoutFn } = useAuthContext()

  const login = useMutation({
    mutationFn: loginFn,
    onSuccess: () => queryClient.invalidateQueries(),
  })

  const register = useMutation({
    mutationFn: registerFn,
    onSuccess: () => queryClient.invalidateQueries(),
  })

  const logout = useMutation({
    mutationFn: async () => logoutFn(),
    onSuccess: () => queryClient.clear(),
  })

  return { login, register, logout }
}

export { useAuthContext }
