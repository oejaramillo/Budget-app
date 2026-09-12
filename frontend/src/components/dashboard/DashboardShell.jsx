import { useState } from 'react'

import { useAuthContext } from '../../hooks/useAuth'
import { useCurrencies } from '../../hooks/useCurrencies'
import AccountsManager from '../accounts/AccountsManager'
import BudgetsManager from '../budgets/BudgetsManager'
import CategoriesManager from '../categories/CategoriesManager'
import CurrenciesManager from '../currencies/CurrenciesManager'
import Dashboard from '../dashboard/Dashboard'
import HoldingsManager from '../investments/HoldingsManager'
import TransactionsManager from '../transactions/TransactionsManager'

/** Tabs of the authenticated area. */
const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'accounts', label: 'Accounts' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'categories', label: 'Categories' },
  { id: 'budgets', label: 'Budgets' },
  { id: 'investments', label: 'Investments' },
  { id: 'currencies', label: 'Currencies' },
]

/**
 * Authenticated shell: header, tab navigation and the active tab.
 *
 * The reporting currency selector here is what makes multi-currency reporting
 * usable: choosing a target makes the overview convert every balance and total
 * into that currency using the stored rates.
 */
export default function DashboardShell() {
  const { user, logout } = useAuthContext()
  const { currencies } = useCurrencies()
  const [activeTab, setActiveTab] = useState('overview')
  const [targetCurrency, setTargetCurrency] = useState('')

  const principal = currencies.find((currency) => currency.principal)
  const activeCurrencies = currencies.filter((currency) => currency.is_active)

  const renderTab = () => {
    switch (activeTab) {
      case 'accounts':
        return <AccountsManager />
      case 'transactions':
        return <TransactionsManager />
      case 'categories':
        return <CategoriesManager />
      case 'budgets':
        return <BudgetsManager />
      case 'investments':
        return <HoldingsManager />
      case 'currencies':
        return <CurrenciesManager />
      case 'overview':
      default:
        return <Dashboard targetCurrency={targetCurrency || undefined} />
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--light-gray)' }}>
      <header
        style={{
          background: 'var(--white)',
          boxShadow: 'var(--shadow-soft)',
          padding: '1rem 2rem',
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                background: 'var(--deep-orange)',
                borderRadius: 'var(--border-radius)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--white)',
                fontSize: '1.2rem',
              }}
              aria-hidden="true"
            >
              💰
            </div>
            <h1 style={{ fontSize: '1.4rem', margin: 0 }}>Budget App</h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
            <label className="text-muted" style={{ fontSize: '0.9rem' }}>
              Reporting currency{' '}
              <select
                className="form-input"
                style={{ display: 'inline-block', width: 'auto', padding: '6px 10px' }}
                value={targetCurrency}
                onChange={(event) => setTargetCurrency(event.target.value)}
              >
                <option value="">
                  {principal ? `Native (${principal.code})` : 'Native'}
                </option>
                {activeCurrencies
                  .filter((currency) => currency.code !== principal?.code)
                  .map((currency) => (
                    <option key={currency.id} value={currency.code}>
                      {currency.code}
                    </option>
                  ))}
              </select>
            </label>
            <span className="text-muted">Hi, {user?.username}</span>
            <button type="button" className="btn btn-outline btn-sm" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main style={{ padding: '2rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div className="tabs mb-3" role="tablist">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                className="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="card">{renderTab()}</div>
        </div>
      </main>
    </div>
  )
}
