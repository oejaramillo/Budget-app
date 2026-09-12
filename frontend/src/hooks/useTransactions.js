import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createTransaction,
  deleteTransaction,
  fetchMonthlyTotals,
  fetchTransactionSummary,
  fetchTransactions,
  updateTransaction,
} from '../services/transactionsService'

/**
 * Transactions list plus mutations.
 *
 * Any write invalidates the derived reporting queries as well as the raw list, so
 * the dashboard never shows a stale total after logging an expense.
 */
export function useTransactions(filters = {}) {
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => fetchTransactions(filters),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['transaction-summary'] })
    queryClient.invalidateQueries({ queryKey: ['monthly-totals'] })
    queryClient.invalidateQueries({ queryKey: ['accounts'] })
    queryClient.invalidateQueries({ queryKey: ['budget-status'] })
  }

  const create = useMutation({ mutationFn: createTransaction, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, data }) => updateTransaction(id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: deleteTransaction, onSuccess: refresh })

  return {
    transactions: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    create,
    update,
    remove,
  }
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
