import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

import { AuthProvider, useAuthContext } from './contexts/AuthContext'
import DashboardShell from './components/dashboard/DashboardShell'
import LandingPage from './components/auth/LandingPage'
import './styles/globals.css'

/**
 * React Query defaults tuned for a single-user finance app:
 * data is small, mutations should feel instant, and re-fetching whenever the
 * window regains focus keeps two open tabs consistent.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
})

function SessionLoader() {
  return (
    <div className="app-loader">
      <div className="app-loader__spinner" />
      Loading Budget App…
    </div>
  )
}

function AppContent() {
  const { isAuthenticated, isLoading } = useAuthContext()

  if (isLoading) return <SessionLoader />
  return isAuthenticated ? <DashboardShell /> : <LandingPage />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <div className="App">
          <AppContent />
        </div>
        <ReactQueryDevtools initialIsOpen={false} />
      </AuthProvider>
    </QueryClientProvider>
  )
}
