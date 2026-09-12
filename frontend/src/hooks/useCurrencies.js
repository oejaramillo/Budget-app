import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createCurrency,
  deleteCurrency,
  fetchCurrencies,
  fetchCurrencySummary,
  refreshExchangeRates,
  updateCurrency,
} from '../services/currenciesService'

/** Currency catalogue (shared reference data). */
export function useCurrencies() {
  const queryClient = useQueryClient()

  const query = useQuery({ queryKey: ['currencies'], queryFn: () => fetchCurrencies() })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['currencies'] })
    queryClient.invalidateQueries({ queryKey: ['currency-summary'] })
  }

  const create = useMutation({ mutationFn: createCurrency, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, data }) => updateCurrency(id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: deleteCurrency, onSuccess: refresh })
  // Staff-only on the backend; surfaces a clear 403 for everyone else.
  const refreshRates = useMutation({ mutationFn: refreshExchangeRates, onSuccess: refresh })

  return {
    currencies: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    create,
    update,
    remove,
    refreshRates,
  }
}

/** Total balance per currency, converted into `target` when given. */
export function useCurrencySummary(target) {
  return useQuery({
    queryKey: ['currency-summary', target ?? 'raw'],
    queryFn: () => fetchCurrencySummary(target),
  })
}
