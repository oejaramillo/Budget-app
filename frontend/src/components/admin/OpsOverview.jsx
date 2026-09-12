import { useState } from 'react'

import { useOpsOverview, useOpsSettings, useUpdateOpsSettings } from '../../hooks/useOps'
import { describeApiError } from '../../api'
import { formatDate } from '../../utils/format'
import { Alert, DataTable, EmptyState, StatCard } from '../ui/Feedback'

function severityClass(severity) {
  if (severity === 'error') return 'neg'
  if (severity === 'warning') return 'text-accent'
  return 'text-muted'
}

/** Safety switches for the console. */
function SafetySettings() {
  const settings = useOpsSettings()
  const update = useUpdateOpsSettings()

  if (settings.isLoading) return <p className="text-muted">Loading settings…</p>
  if (settings.isError) return <Alert>{describeApiError(settings.error)}</Alert>

  const toggles = [
    {
      name: 'allow_mutating_operations',
      label: 'Allow operations that change data',
      hint: 'Turning this off leaves only the read-only checks available.',
    },
    {
      name: 'allow_destructive_operations',
      label: 'Allow destructive operations',
      hint:
        'Required for schema changes such as applying migrations from the console. ' +
        'Prefer `manage.py migrate` on the server.',
    },
  ]

  return (
    <div className="card">
      <h4 className="mb-2">Operations settings</h4>
      {update.isError && <Alert>{describeApiError(update.error)}</Alert>}
      {toggles.map((toggle) => (
        <label
          key={toggle.name}
          style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', marginBottom: '0.75rem' }}
        >
          <input
            type="checkbox"
            checked={Boolean(settings.data?.[toggle.name])}
            onChange={(event) => update.mutate({ [toggle.name]: event.target.checked })}
            disabled={update.isPending}
          />
          <span>
            {toggle.label}
            <br />
            <small className="text-muted">{toggle.hint}</small>
          </span>
        </label>
      ))}
      <small className="text-muted">
        Last changed {formatDate(settings.data?.updated_at)}.
      </small>
    </div>
  )
}

/**
 * Console landing screen: service-wide counts, data integrity, rate freshness and
 * the safety switches. All of it is superuser-only data.
 */
export default function OpsOverview() {
  const overview = useOpsOverview()
  const [expanded, setExpanded] = useState(null)

  if (overview.isLoading) return <p className="text-muted">Loading overview…</p>
  if (overview.isError) return <Alert>{describeApiError(overview.error)}</Alert>

  const { stats, integrity, rates, apps } = overview.data
  const totals = stats.totals
  const db = stats.database

  return (
    <div>
      <div className="stat-grid">
        <StatCard label="Tenants" value={totals.users} hint={`${totals.active_users} active`} />
        <StatCard label="Accounts" value={totals.accounts} />
        <StatCard label="Transactions" value={totals.transactions} />
        <StatCard
          label="Currencies"
          value={totals.currencies}
          hint={`${totals.active_currencies} active`}
        />
        <StatCard label="Budgets" value={totals.budgets} />
        <StatCard label="Holdings" value={totals.holdings} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        <div className="card">
          <h4 className="mb-2">Exchange rates</h4>
          {rates.is_stale && (
            <Alert variant="info">
              {rates.last_refresh_at
                ? `Rates are ${rates.age_hours}h old.`
                : 'Rates have never been refreshed.'}
            </Alert>
          )}
          <p className="mb-1">
            Last refresh:{' '}
            <strong>{rates.last_refresh_at ? formatDate(rates.last_refresh_at) : 'never'}</strong>
          </p>
          <p className="mb-1">
            Currencies older than {rates.max_age_hours}h: <strong>{rates.stale_count}</strong>
          </p>
          <p className="mb-1">
            Failed refreshes recorded: <strong>{stats.rates.failed_refreshes}</strong>
          </p>
          {rates.stale_codes?.length > 0 && (
            <small className="text-muted">{rates.stale_codes.join(', ')}</small>
          )}
        </div>

        <div className="card">
          <h4 className="mb-2">Database</h4>
          <p className="mb-1">
            Backend: <strong>{db.vendor}</strong>
          </p>
          <p className="mb-1">
            Version: <strong>{db.version ?? '—'}</strong>
          </p>
          <p className="mb-1">
            Size: <strong>{db.size_pretty ?? '—'}</strong>
          </p>
          <small className="text-muted">{db.name}</small>
        </div>

        <SafetySettings />
      </div>

      <h3 className="mt-4 mb-2">
        Data integrity
        {integrity.error_count + integrity.warning_count > 0 && (
          <span className="neg"> — {integrity.message}</span>
        )}
      </h3>
      {integrity.findings.length === 0 ? (
        <Alert variant="success">No issues found in the last check.</Alert>
      ) : (
        <DataTable columns={['Severity', 'Check', 'Count', 'Details']}>
          {integrity.findings.map((finding) => (
            <tr key={finding.code}>
              <td className={severityClass(finding.severity)}>{finding.severity}</td>
              <td>{finding.code}</td>
              <td className="numeric">{finding.count}</td>
              <td>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setExpanded(expanded === finding.code ? null : finding.code)}
                >
                  {expanded === finding.code ? 'Hide' : 'Show'}
                </button>
                {expanded === finding.code && (
                  <>
                    <div className="text-muted">{finding.summary}</div>
                    <pre style={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(finding.samples, null, 2)}
                    </pre>
                  </>
                )}
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      <h3 className="mt-4 mb-2">Busiest tenants</h3>
      {stats.busiest_users.length === 0 ? (
        <EmptyState message="No tenant has created data yet." />
      ) : (
        <DataTable columns={['Username', 'Accounts', 'Transactions']}>
          {stats.busiest_users.map((row) => (
            <tr key={row.id}>
              <td>{row.username}</td>
              <td className="numeric">{row.account_count}</td>
              <td className="numeric">{row.transaction_count}</td>
            </tr>
          ))}
        </DataTable>
      )}

      <h3 className="mt-4 mb-2">Installed applications</h3>
      <DataTable columns={['App', 'Models']}>
        {apps.map((app) => (
          <tr key={app.name}>
            <td>
              {app.label}
              <br />
              <small className="text-muted">{app.name}</small>
            </td>
            <td>{app.models.join(', ')}</td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}
