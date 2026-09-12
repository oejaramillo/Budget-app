import { useState } from 'react'

import {
  useDeleteTenant,
  useSetTenantPassword,
  useTenants,
  useTenantsSummary,
  useUpdateTenant,
} from '../../hooks/useOps'
import { describeApiError } from '../../api'
import { useAuthContext } from '../../hooks/useAuth'
import { formatDate } from '../../utils/format'
import { Alert, DataTable, EmptyState, StatCard } from '../ui/Feedback'
import { TextField } from '../ui/FormFields'

/**
 * Tenant administration: flags, password reset and deletion.
 *
 * Safety rails mirrored from the API (the API is the authority):
 *  - you cannot deactivate, demote or delete your own account;
 *  - the last active superuser cannot be demoted, disabled or deleted;
 *  - deletion requires typing the username back.
 */
export default function UsersAdmin() {
  const { user: currentUser } = useAuthContext()
  const [search, setSearch] = useState('')
  const [passwordFor, setPasswordFor] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [deleting, setDeleting] = useState(null)
  const [confirmText, setConfirmText] = useState('')

  const tenants = useTenants({ search: search || undefined })
  const summary = useTenantsSummary()
  const updateTenant = useUpdateTenant()
  const setPassword = useSetTenantPassword()
  const deleteTenant = useDeleteTenant()

  const rows = tenants.data ?? []
  const error = updateTenant.error ?? setPassword.error ?? deleteTenant.error

  const toggle = (tenant, field) => {
    updateTenant.mutate({ id: tenant.id, data: { [field]: !tenant[field] } })
  }

  const submitPassword = (event) => {
    event.preventDefault()
    setPassword.mutate(
      { id: passwordFor.id, newPassword },
      {
        onSuccess: () => {
          setPasswordFor(null)
          setNewPassword('')
        },
      }
    )
  }

  const submitDelete = (event) => {
    event.preventDefault()
    deleteTenant.mutate(
      { id: deleting.id, username: deleting.username },
      {
        onSuccess: () => {
          setDeleting(null)
          setConfirmText('')
        },
      }
    )
  }

  return (
    <div>
      {summary.data && (
        <div className="stat-grid">
          <StatCard label="Tenants" value={summary.data.total} />
          <StatCard label="Active" value={summary.data.active} />
          <StatCard label="Staff" value={summary.data.staff} />
          <StatCard label="Superusers" value={summary.data.superusers} />
        </div>
      )}

      <div className="row-between mb-3">
        <h3 style={{ margin: 0 }}>Tenants</h3>
        <input
          className="form-input"
          style={{ maxWidth: '260px' }}
          placeholder="Search username or email…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <Alert>{error && describeApiError(error)}</Alert>
      {setPassword.isSuccess && !passwordFor && (
        <Alert variant="success">Password updated.</Alert>
      )}
      {deleteTenant.isSuccess && !deleting && (
        <Alert variant="success">Tenant deleted.</Alert>
      )}

      {passwordFor && (
        <div className="card mb-3">
          <h4 className="mb-2">Set a new password for {passwordFor.username}</h4>
          <form onSubmit={submitPassword}>
            {setPassword.isError && <Alert>{describeApiError(setPassword.error)}</Alert>}
            <TextField
              label="New password *"
              name="new_password"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              hint="Validated against Django's password rules. Existing sessions stay valid until their tokens expire."
              required
            />
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button type="submit" className="btn btn-primary" disabled={setPassword.isPending}>
                Set password
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  setPasswordFor(null)
                  setNewPassword('')
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {deleting && (
        <div className="card mb-3" style={{ borderLeft: '4px solid var(--alert-red)' }}>
          <h4 className="mb-2">Delete {deleting.username}?</h4>
          <p className="text-muted">
            This permanently removes the account and every row it owns: {deleting.account_count}{' '}
            account(s), {deleting.transaction_count} transaction(s) and {deleting.holding_count}{' '}
            holding(s). It cannot be undone.
          </p>
          <form onSubmit={submitDelete}>
            {deleteTenant.isError && <Alert>{describeApiError(deleteTenant.error)}</Alert>}
            <TextField
              label={`Type "${deleting.username}" to confirm *`}
              name="confirm_username"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              required
            />
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                type="submit"
                className="btn btn-danger"
                disabled={deleteTenant.isPending || confirmText !== deleting.username}
              >
                Delete permanently
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  setDeleting(null)
                  setConfirmText('')
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {rows.length === 0 && !tenants.isLoading ? (
        <EmptyState message="No tenants match this search." />
      ) : (
        <DataTable
          columns={['Username', 'Email', 'Flags', 'Data', 'Joined', 'Last login', 'Actions']}
          isLoading={tenants.isLoading}
        >
          {rows.map((tenant) => {
            const isSelf = tenant.id === currentUser?.id
            return (
              <tr key={tenant.id}>
                <td>
                  {tenant.username}
                  {isSelf && <span className="text-muted"> (you)</span>}
                </td>
                <td>{tenant.email || '—'}</td>
                <td>
                  {tenant.is_superuser && <span title="Superuser">★ </span>}
                  {tenant.is_staff && <span title="Staff">⚙ </span>}
                  {!tenant.is_active && <span className="neg">inactive</span>}
                  {tenant.is_active && !tenant.is_staff && !tenant.is_superuser && (
                    <span className="text-muted">user</span>
                  )}
                </td>
                <td className="numeric">
                  {tenant.account_count} acct · {tenant.transaction_count} tx
                </td>
                <td>{formatDate(tenant.date_joined)}</td>
                <td>{tenant.last_login ? formatDate(tenant.last_login) : 'never'}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => toggle(tenant, 'is_active')}
                    disabled={isSelf || updateTenant.isPending}
                    title={isSelf ? 'You cannot deactivate your own account' : undefined}
                  >
                    {tenant.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => toggle(tenant, 'is_staff')}
                    disabled={isSelf || updateTenant.isPending}
                  >
                    {tenant.is_staff ? 'Revoke staff' : 'Make staff'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => toggle(tenant, 'is_superuser')}
                    disabled={isSelf || updateTenant.isPending}
                  >
                    {tenant.is_superuser ? 'Revoke superuser' : 'Make superuser'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => {
                      setPasswordFor(tenant)
                      setNewPassword('')
                    }}
                  >
                    Password
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      setDeleting(tenant)
                      setConfirmText('')
                    }}
                    disabled={isSelf}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            )
          })}
        </DataTable>
      )}
    </div>
  )
}
