/**
 * Helpers shared by the service modules.
 */

/**
 * DRF list endpoints are paginated, so the payload is
 * `{count, next, previous, results}`. Detail endpoints and action routes return
 * the object (or array) directly. This unwraps both shapes.
 *
 * @template T
 * @param {{ data: T | { results: T } }} response
 * @returns {T}
 */
export function unwrapList(response) {
  const data = response?.data
  if (data && !Array.isArray(data) && Array.isArray(data.results)) {
    return data.results
  }
  return data
}

/**
 * Build a querystring, dropping empty values so URLs stay readable.
 * @param {Record<string, string | number | boolean | null | undefined>} params
 * @returns {string} e.g. `?target=USD&page_size=50`, or an empty string
 */
export function buildQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, String(value))
    }
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

/**
 * Fetch every page of a paginated endpoint.
 *
 * The catalogue and the user's own data are small, so loading them in full keeps
 * the UI simple. `maxPages` is a guard against an unexpected loop.
 *
 * @param {(url: string) => Promise<any>} request
 * @param {string} url
 * @param {number} [maxPages]
 * @returns {Promise<any[]>}
 */
export async function fetchAllPages(request, url, maxPages = 20) {
  const collected = []
  let next = url
  let page = 0

  while (next && page < maxPages) {
    const response = await request(next)
    const payload = response.data
    if (Array.isArray(payload)) {
      collected.push(...payload)
      break
    }
    collected.push(...(payload.results ?? []))
    next = payload.next
    page += 1
  }
  return collected
}
