import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createTransaction,
  deleteTransaction,
  fetchDescriptionSuggestions,
  fetchLedgerStats,
  fetchMonthlyTotals,
  fetchRecentTransactions,
  fetchTransactionSummary,
  fetchTransactions,
  fetchTransactionsPage,
  updateTransaction,
} from '../services/transactionsService'

/**
 * Transactions list plus mutations.
 *
 * Pass `{ paged: true }` to also receive the pagination envelope, which the
 * transaction screen needs because a real ledger does not fit on one page.
 *
 * Any write invalidates the derived reporting queries as well as the raw list, so
 * the dashboard never shows a stale total after logging an expense. Description
 * suggestions are invalidated too: a new description must appear in autocomplete.
 *
 * @param {import('../services/transactionsService').TransactionFilters} [filters]
 * @param {{paged?: boolean, enabled?: boolean}} [options]
 */
export function useTransactions(filters = {}, { paged = false, enabled = true } = {}) {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['transactions', paged ? 'page' : 'list', filters],
    queryFn: () => (paged ? fetchTransactionsPage(filters) : fetchTransactions(filters)),
    enabled,
    // Keep the previous page visible while the next one loads, so paging and
    // filtering do not flash an empty table.
    placeholderData: (previous) => previous,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['transaction-summary'] })
    queryClient.invalidateQueries({ queryKey: ['monthly-totals'] })
    queryClient.invalidateQueries({ queryKey: ['transaction-descriptions'] })
    queryClient.invalidateQueries({ queryKey: ['ledger-stats'] })
    queryClient.invalidateQueries({ queryKey: ['accounts'] })
    queryClient.invalidateQueries({ queryKey: ['budget-status'] })
  }

  const create = useMutation({ mutationFn: createTransaction, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, data }) => updateTransaction(id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: deleteTransaction, onSuccess: refresh })

  const page = paged ? query.data : null

  return {
    transactions: page ? (page.results ?? []) : query.data ?? [],
    count: page?.count ?? (query.data?.length ?? 0),
    hasNext: Boolean(page?.next),
    hasPrevious: Boolean(page?.previous),
    isFetching: query.isFetching,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    create,
    update,
    remove,
  }
}

/**
 * Descriptions the user has typed before, for autocomplete.
 *
 * `q` filters server-side. The response is cached per term, so repeated typing is
 * cheap; the caller debounces the keystrokes that produce `q`.
 *
 * @param {{q?: string, account?: number, limit?: number}} params
 * @param {{enabled?: boolean}} [options]
 */
export function useDescriptionSuggestions(params = {}, { enabled = true } = {}) {
  return useQuery({
    queryKey: ['transaction-descriptions', params],
    queryFn: () => fetchDescriptionSuggestions(params),
    enabled,
    staleTime: 60_000,
    placeholderData: (previous) => previous,
  })
}

/** The user's latest transactions, for one-tap repeat entry. */
export function useRecentTransactions(limit = 8) {
  return useQuery({
    queryKey: ['transactions', 'recent', limit],
    queryFn: () => fetchRecentTransactions(limit),
    staleTime: 30_000,
  })
}

/** A few facts about the ledger, shown in the logging screen header. */
export function useLedgerStats() {
  return useQuery({
    queryKey: ['ledger-stats'],
    queryFn: fetchLedgerStats,
    staleTime: 60_000,
  })
}

/** Income/expense totals for a date range. */
export function useTransactionSummary(params = {}) {
  return useQuery({
    queryKey: ['transaction-summary', params],
    queryFn: () => fetchTransactionSummary(params),
  })
}

/** Income/expense totals grouped by month. */
export function useMonthlyTotals(months = 6) {
  return useQuery({
    queryKey: ['monthly-totals', months],
    queryFn: () => fetchMonthlyTotals(months),
  })
}
