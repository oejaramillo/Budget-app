import { useEffect, useState } from 'react'

/**
 * Delay a fast-changing value.
 *
 * Used for the free-text inputs that drive server queries (transaction search,
 * description autocomplete) so a request is not fired for every keystroke. The
 * previous value stays visible while the new one settles, which keeps the UI from
 * flickering.
 *
 * @template T
 * @param {T} value
 * @param {number} [delayMs]
 * @returns {T}
 */
export function useDebouncedValue(value, delayMs = 300) {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}

export default useDebouncedValue
