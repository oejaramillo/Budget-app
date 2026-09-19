/**
 * Small factory for the "list + create + update + delete" hooks that every
 * resource needs. Writing it once keeps each `useX` hook to a few lines and makes
 * cache-invalidation behaviour identical everywhere.
 *
 * The returned object exposes the rows under the pluralised resource name
 * (`accounts`, `budgets`, `categories`, ...) rather than a generic `items`, so a
 * consumer reads `const { accounts } = useAccounts()` and the component cannot
 * disagree with the hook about what the list is called.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

/** `budget` -> `budgets`, `category` -> `categories`. */
export function pluralize(name) {
  if (name.endsWith('y') && !/[aeiou]y$/.test(name)) return `${name.slice(0, -1)}ies`
  if (/(s|x|z|ch|sh)$/.test(name)) return `${name}es`
  return `${name}s`
}

/**
 * @param {Object} options
 * @param {string} options.resource        Query-key prefix and list property, e.g. 'accounts'
 * @param {() => Promise<any[]>} options.list
 * @param {(data: any) => Promise<any>} options.create
 * @param {(id: number, data: any) => Promise<any>} options.update
 * @param {(id: number) => Promise<any>} options.remove
 * @param {string[]} [options.invalidate]  Extra query keys to refresh on write
 */
export function createResourceHooks({ resource, list, create, update, remove, invalidate = [] }) {
  // Pluralised so `useAccounts()` yields `accounts`, `useBudgets()` yields `budgets`.
  const listKey = resource.endsWith('s') ? resource : pluralize(resource)

  return function useResource() {
    const queryClient = useQueryClient()

    const query = useQuery({ queryKey: [resource], queryFn: list })

    const refresh = () => {
      queryClient.invalidateQueries({ queryKey: [resource] })
      invalidate.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }))
    }

    const createMutation = useMutation({ mutationFn: create, onSuccess: refresh })
    const updateMutation = useMutation({
      mutationFn: ({ id, data }) => update(id, data),
      onSuccess: refresh,
    })
    const removeMutation = useMutation({ mutationFn: remove, onSuccess: refresh })

    return {
      [listKey]: query.data ?? [],
      isLoading: query.isLoading,
      isError: query.isError,
      error: query.error,
      refetch: query.refetch,
      create: createMutation,
      update: updateMutation,
      remove: removeMutation,
    }
  }
}
