import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import {
  fetchAnalyticsDashboard,
  fetchCategoryTrend,
  fetchPeriodAnalytics,
  fetchSpendingOutlook,
} from '../services/analyticsService'

/**
 * The whole spending dashboard in one request.
 *
 * One request rather than eight: every panel is derived from the same aggregates,
 * and the backend computes them together, so splitting them would mean eight round
 * trips over a remote database for numbers that must agree with each other anyway.
 *
 * @param {{currency?: string, months?: number}} params
 */
export function useAnalyticsDashboard(params = {}) {
  return useQuery({
    queryKey: ['analytics-dashboard', params],
    queryFn: () => fetchAnalyticsDashboard(params),
    // Analytics only change when a transaction does, and mutations already
    // invalidate this key; a minute of staleness is invisible and saves queries.
    staleTime: 60_000,
    placeholderData: (previous) => previous,
  })
}

/** A single period (month, quarter or year) with its comparison. */
export function usePeriodAnalytics(granularity, anchor, currency) {
  return useQuery({
    queryKey: ['analytics-period', granularity, anchor ?? 'latest', currency ?? 'default'],
    queryFn: () => fetchPeriodAnalytics(granularity, anchor, currency),
    staleTime: 60_000,
    placeholderData: (previous) => previous,
  })
}

/** Category trend series, fetched only when that chart is shown. */
export function useCategoryTrend(params = {}, enabled = true) {
  return useQuery({
    queryKey: ['analytics-category-trend', params],
    queryFn: () => fetchCategoryTrend(params),
    staleTime: 60_000,
    enabled,
  })
}

/** Current-month outlook. */
export function useSpendingOutlook(currency) {
  return useQuery({
    queryKey: ['analytics-outlook', currency ?? 'default'],
    queryFn: () => fetchSpendingOutlook(currency),
    staleTime: 60_000,
  })
}

/** Local UI state for the dashboard's controls. */
export function useDashboardControls(defaults = {}) {
  const [currency, setCurrency] = useState(defaults.currency ?? '')
  const [months, setMonths] = useState(defaults.months ?? 24)
  const [view, setView] = useState(defaults.view ?? 'month')
  return { currency, setCurrency, months, setMonths, view, setView }
}
