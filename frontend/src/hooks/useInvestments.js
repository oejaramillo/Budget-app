import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createHolding,
  createValuation,
  deleteHolding,
  deleteValuation,
  fetchHoldings,
  fetchPortfolio,
  fetchPortfolioHistory,
  updateHolding,
} from '../services/investmentsService'

/** Holdings list plus mutations. */
export function useHoldings() {
  const queryClient = useQueryClient()

  const query = useQuery({ queryKey: ['holdings'], queryFn: fetchHoldings })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['holdings'] })
    queryClient.invalidateQueries({ queryKey: ['portfolio'] })
    queryClient.invalidateQueries({ queryKey: ['portfolio-history'] })
  }

  const create = useMutation({ mutationFn: createHolding, onSuccess: refresh })
  const update = useMutation({
    mutationFn: ({ id, data }) => updateHolding(id, data),
    onSuccess: refresh,
  })
  const remove = useMutation({ mutationFn: deleteHolding, onSuccess: refresh })

  return {
    holdings: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    create,
    update,
    remove,
  }
}

/** Portfolio totals, optionally converted into `target`. */
export function usePortfolio(target) {
  return useQuery({
    queryKey: ['portfolio', target ?? 'raw'],
    queryFn: () => fetchPortfolio(target),
  })
}

/** Portfolio value over time. */
export function usePortfolioHistory() {
  return useQuery({ queryKey: ['portfolio-history'], queryFn: fetchPortfolioHistory })
}

/** Record a new valuation for a holding. */
export function useCreateValuation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createValuation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holdings'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio-history'] })
    },
  })
}

/** Delete a valuation. */
export function useDeleteValuation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteValuation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holdings'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio-history'] })
    },
  })
}
