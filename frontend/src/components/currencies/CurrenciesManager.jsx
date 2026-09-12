import { useState } from 'react'

import { useAuthContext } from '../../hooks/useAuth'
import { useCurrencies } from '../../hooks/useCurrencies'
import { useForm } from '../../hooks/useForm'
import { describeApiError } from '../../api'
import { formatMoney } from '../../utils/format'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import { TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

const emptyCurrency = { code: '', name: '', symbol: '', exchange_rate: '' }

/**
 * Currency catalogue.
 *
 * Readable by every user because currencies and their rates are shared reference
 * data; editing is limited to staff accounts, which is also enforced by the API.
 * The rate refresh button therefore only appears for staff and explains a 403 if
 * the account is not allowed to use it.
 */
export default function CurrenciesManager() {
  const { user } = useAuthContext()
  const { currencies, isLoading, create, update, remove, refreshRates } = useCurrencies()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const isStaff = Boolean(user?.is_staff)

  const form = useForm({
    initialValues: emptyCurrency,
    onSubmit: async (values) => {
      const payload = {
        code: values.code.trim().toUpperCase(),
        name: values.name.trim(),
        symbol: values.symbol.trim(),
        exchange_rate: values.exchange_rate,
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      return create.mutateAsync(payload)
    },
    onSuccess: () => {
      form.reset({ ...emptyCurrency })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const startEdit = (currency) => {
    setEditingId(currency.id)
    setShowForm(true)
    form.reset({
      code: currency.code,
      name: currency.name,
      symbol: currency.symbol ?? '',
      exchange_rate: currency.exchange_rate,
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyCurrency })
  }

  const handleDelete = (currency) => {
    if (
      !window.confirm(
        `Delete ${currency.code}? This fails if any account or transaction still uses it.`
      )
    )
      return
    remove.mutate(currency.id)
  }

  const mutationError = create.error ?? update.error ?? remove.error
  const refreshError = refreshRates.error
  const refreshResult = refreshRates.data

  return (
    <div>
      <FormPanel
        title="Currencies"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Add currency"
      >
        {!isStaff && (
          <Alert variant="info">
            Rates are shared reference data, so only staff accounts can change them. Ask an
            administrator if a rate looks wrong.
          </Alert>
        )}
        <form onSubmit={form.handleSubmit}>
          <Alert>{form.formError}</Alert>
          {mutationError && <Alert>{describeApiError(mutationError)}</Alert>}

          <div className="inline-fields">
            <TextField
              label="Code *"
              name="code"
              value={form.values.code}
              onChange={form.handleChange}
              error={form.errors.code}
              placeholder="EUR"
              hint="3-letter ISO 4217 code."
              required
              disabled={!isStaff}
            />
            <TextField
              label="Name *"
              name="name"
              value={form.values.name}
              onChange={form.handleChange}
              error={form.errors.name}
              placeholder="Euro"
              required
              disabled={!isStaff}
            />
            <TextField
              label="Symbol"
              name="symbol"
              value={form.values.symbol}
              onChange={form.handleChange}
              error={form.errors.symbol}
              placeholder="€"
              disabled={!isStaff}
            />
            <TextField
              label="Exchange rate *"
              name="exchange_rate"
              type="number"
              step="0.000001"
              value={form.values.exchange_rate}
              onChange={form.handleChange}
              error={form.errors.exchange_rate}
              hint="Units of this currency per 1 USD."
              required
              disabled={!isStaff}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!isStaff || form.isSubmitting}
            >
              {editingId ? 'Save changes' : 'Create currency'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {isStaff && (
        <div className="row-between mb-3">
          <p className="text-muted" style={{ margin: 0 }}>
            Rates can be refreshed from the provider, or with{' '}
            <code>python manage.py refresh_currencies</code>.
          </p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => refreshRates.mutate()}
            disabled={refreshRates.isPending}
          >
            {refreshRates.isPending ? 'Refreshing…' : 'Refresh rates'}
          </button>
        </div>
      )}

      {refreshError && <Alert>{describeApiError(refreshError)}</Alert>}
      {refreshResult && <Alert variant="success">{refreshResult.message}</Alert>}

      {currencies.length === 0 && !isLoading ? (
        <EmptyState message="No currencies yet. Run `manage.py refresh_currencies` or add one manually." />
      ) : (
        <DataTable
          columns={['Code', 'Name', 'Symbol', 'Rate (per USD)', 'Principal', 'Active', 'Actions']}
          isLoading={isLoading}
        >
          {currencies.map((currency) => (
            <tr key={currency.id}>
              <td>{currency.code}</td>
              <td>{currency.name}</td>
              <td>{currency.symbol || '—'}</td>
              <td className="numeric">{formatMoney(currency.exchange_rate)}</td>
              <td>{currency.principal ? '★' : '—'}</td>
              <td>{currency.is_active ? 'Yes' : 'No'}</td>
              <td>
                {isStaff && (
                  <>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => startEdit(currency)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(currency)}
                    >
                      Delete
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  )
}
