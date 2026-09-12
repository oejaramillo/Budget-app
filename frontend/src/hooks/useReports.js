import { useQuery } from '@tanstack/react-query'

import { fetchAccountBalances, fetchNetWorth } from '../services/accountsService'

/** Net worth, either per currency or converted into `target`. */
export function useNetWorth(target) {
  return useQuery({
    queryKey: ['net-worth', target ?? 'raw'],
    queryFn: () => fetchNetWorth(target),
  })
}

/** Per-account balances with an optional converted reference value. */
export function useAccountBalances(target) {
  return useQuery({
    queryKey: ['account-balances', target ?? 'raw'],
    queryFn: () => fetchAccountBalances(target),
  })
}
