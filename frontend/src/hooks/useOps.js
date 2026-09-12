import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  deleteTenant,
  fetchOperations,
  fetchOpsOverview,
  fetchOpsSettings,
  fetchRunHistory,
  fetchTenants,
  fetchTenantsSummary,
  runOperation,
  setTenantPassword,
  updateOpsSettings,
  updateTenant,
} from '../services/opsService'

/**
 * Superuser console hooks.
 *
 * Queries are only mounted from superuser-only screens, and every endpoint behind
 * them enforces `is_superuser`, so hiding the UI is a convenience rather than the
 * security boundary.
 */

/** Everything the console landing screen needs, in one request. */
export function useOpsOverview() {
  return useQuery({
    queryKey: ['ops-overview'],
    queryFn: fetchOpsOverview,
    // These numbers are cheap but not free; no need to refetch on every focus.
    staleTime: 60_000,
  })
}

/** Registry of runnable operations. */
export function useOperations() {
  return useQuery({ queryKey: ['ops-operations'], queryFn: fetchOperations, staleTime: 300_000 })
}

/** Audit trail of past runs. */
export function useRunHistory(filters = {}) {
  return useQuery({
    queryKey: ['ops-history', filters],
    queryFn: () => fetchRunHistory(filters),
  })
}

/**
 * Run an operation and refresh everything it could have touched.
 *
 * A maintenance action can change rates, data integrity or the audit trail, so the
 * overview is invalidated either way; only a successful mutating run invalidates
 * the per-user reporting queries.
 */
export function useRunOperation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ key, args }) => runOperation(key, args),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['ops-overview'] })
      queryClient.invalidateQueries({ queryKey: ['ops-history'] })
      queryClient.invalidateQueries({ queryKey: ['ops-settings'] })

      if (run.operation === 'refresh_currencies' && run.status === 'success') {
        queryClient.invalidateQueries({ queryKey: ['currencies'] })
        queryClient.invalidateQueries({ queryKey: ['currency-summary'] })
        queryClient.invalidateQueries({ queryKey: ['net-worth'] })
      }
    },
  })
}

/** Console safety switches. */
export function useOpsSettings() {
  return useQuery({ queryKey: ['ops-settings'], queryFn: fetchOpsSettings })
}

export function useUpdateOpsSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateOpsSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ops-settings'] })
      queryClient.invalidateQueries({ queryKey: ['ops-overview'] })
    },
  })
}

/** Tenant list with their data footprint. */
export function useTenants(params = {}) {
  return useQuery({ queryKey: ['ops-tenants', params], queryFn: () => fetchTenants(params) })
}

export function useTenantsSummary() {
  return useQuery({ queryKey: ['ops-tenants-summary'], queryFn: fetchTenantsSummary })
}

export function useUpdateTenant() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => updateTenant(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ops-tenants'] })
      queryClient.invalidateQueries({ queryKey: ['ops-tenants-summary'] })
      queryClient.invalidateQueries({ queryKey: ['ops-overview'] })
    },
  })
}

export function useSetTenantPassword() {
  return useMutation({
    mutationFn: ({ id, newPassword }) => setTenantPassword(id, newPassword),
  })
}

export function useDeleteTenant() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, username }) => deleteTenant(id, username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ops-tenants'] })
      queryClient.invalidateQueries({ queryKey: ['ops-tenants-summary'] })
      queryClient.invalidateQueries({ queryKey: ['ops-overview'] })
    },
  })
}
