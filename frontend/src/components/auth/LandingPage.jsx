import { useState } from 'react'

import AuthPanel from './AuthPanel'

const FEATURES = [
  {
    title: 'Every account in one place',
    body: 'Bank, cash, credit card and investment accounts, each in its own currency.',
  },
  {
    title: 'Fast daily logging',
    body: 'Log income, expenses and transfers in seconds, with categories and budgets attached.',
  },
  {
    title: 'Multi-currency reporting',
    body: 'Balances, budgets and investments converted into the currency you think in.',
  },
  {
    title: 'Investments tracked properly',
    body: 'Holdings with quantity, cost basis and dated valuations, so gains are honest.',
  },
]

/**
 * Unauthenticated landing page: a short pitch on the left, the auth panel on the
 * right. Below `900px` the grid collapses to a single column (see the inline
 * `gridTemplateColumns` fallback).
 */
export default function LandingPage() {
  const [showAuth, setShowAuth] = useState(false)

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #8ecae6 0%, #219ebc 100%)' }}>
      <header style={{ padding: '1rem 2rem', background: 'rgba(255, 255, 255, 0.12)' }}>
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
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
          <h1 style={{ color: 'var(--white)', fontSize: '1.4rem', margin: 0 }}>Budget App</h1>
        </div>
      </header>

      <main style={{ padding: '3rem 2rem' }}>
        <div
          style={{
            maxWidth: '1100px',
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '3rem',
            alignItems: 'center',
          }}
        >
          <div style={{ color: 'var(--white)' }}>
            <h2 style={{ color: 'var(--white)', fontSize: '2.6rem', lineHeight: 1.2, marginBottom: '1rem' }}>
              Take control of your <span style={{ color: 'var(--sunshine-yellow)' }}>money</span>
            </h2>
            <p style={{ fontSize: '1.1rem', opacity: 0.95, marginBottom: '2rem' }}>
              A private, multi-currency finance tracker. Log what you spend, keep an eye on
              your budgets and watch your investments — without a spreadsheet.
            </p>

            <div style={{ display: 'grid', gap: '1rem' }}>
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  style={{
                    background: 'rgba(255, 255, 255, 0.14)',
                    borderRadius: 'var(--border-radius)',
                    padding: '1rem 1.25rem',
                  }}
                >
                  <strong>{feature.title}</strong>
                  <p style={{ margin: 0, opacity: 0.9, fontSize: '0.95rem' }}>{feature.body}</p>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            {showAuth ? (
              <AuthPanel />
            ) : (
              <div className="card" style={{ maxWidth: '420px', width: '100%', textAlign: 'center' }}>
                <h3 className="mb-2">Get started</h3>
                <p className="text-muted mb-3">
                  Sign in to an existing account or create a new one. Your data is private to
                  your account.
                </p>
                <button type="button" className="btn btn-primary" onClick={() => setShowAuth(true)}>
                  Sign in / Create account
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
