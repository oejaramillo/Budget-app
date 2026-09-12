/**
 * Small factory for the "list + create + update + delete" hooks that every
 * resource needs. Writing it once keeps each `useX` hook to a few lines and makes
 * cache-invalidation behaviour identical everywhere.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

/**
 * @param {Object} options
 * @param {string} options.resource        Query-key prefix, e.g. 'accounts'
 * @param {() => Promise<any[]>} options.list
 * @param {(data: any) => Promise<any>} options.create
 * @param {(id: number, data: any) => Promise<any>} options.update
 * @param {(id: number) => Promise<any>} options.remove
 * @param {string[]} [options.invalidate]  Extra query keys to refresh on write
 * @param {(message: string) => void} [options.onError]
 */
export function createResourceHooks({
  resource,
  list,
  create,
  update,
  remove,
  invalidate = [],
  onError,
}) {
  return function useResource() {
    const queryClient = useQueryClient()

    const query = useQuery({ queryKey: [resource], queryFn: list })

    const refresh = () => {
      queryClient.invalidateQueries({ queryKey: [resource] })
      invalidate.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }))
    }

    const handleError = (error) => {
      if (onError) onError(error)
    }

    const createMutation = useMutation({ mutationFn: create, onSuccess: refresh, onError: handleError })
    const updateMutation = useMutation({
      mutationFn: ({ id, data }) => update(id, data),
      onSuccess: refresh,
      onError: handleError,
    })
    const removeMutation = useMutation({ mutationFn: remove, onSuccess: refresh, onError: handleError })

    return {
      items: query.data ?? [],
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
