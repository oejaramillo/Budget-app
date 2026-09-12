import { useState } from 'react'

import { useAccounts } from '../../hooks/useAccounts'
import { useCurrencies } from '../../hooks/useCurrencies'
import { useForm } from '../../hooks/useForm'
import { adjustAccountBalance } from '../../services/accountsService'
import { ACCOUNT_TYPES } from '../../constants'
import { formatDate, formatMoney } from '../../utils/format'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import { SelectField, TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

const emptyAccount = {
  name: '',
  account_type: 'checking',
  currency: '',
  institution: '',
  official_number: '',
  initial_balance: '0.00',
}

/**
 * Accounts CRUD.
 *
 * `balance` is intentionally absent from the create/update payload: the backend
 * derives it from transactions and exposes a dedicated endpoint for setting an
 * opening balance. The form implements that two-step flow explicitly so the
 * balance can never drift out of sync with the ledger.
 */
export default function AccountsManager() {
  const { accounts, isLoading, create, update, remove } = useAccounts()
  const { currencies } = useCurrencies()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const currencyOptions = currencies.map((currency) => ({
    value: currency.id,
    label: `${currency.code} — ${currency.name}${currency.principal ? ' (principal)' : ''}`,
  }))

  const form = useForm({
    initialValues: emptyAccount,
    onSubmit: async (values) => {
      const payload = {
        name: values.name.trim(),
        account_type: values.account_type,
        currency: Number(values.currency),
        institution: values.institution.trim(),
        official_number: values.official_number.trim(),
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      const account = await create.mutateAsync(payload)
      // Second step: apply the opening balance through the sanctioned endpoint.
      if (values.initial_balance && Number(values.initial_balance) !== 0) {
        await adjustAccountBalance(account.id, values.initial_balance)
      }
      return account
    },
    onSuccess: () => {
      form.reset({ ...emptyAccount })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const startEdit = (account) => {
    setEditingId(account.id)
    setShowForm(true)
    form.reset({
      name: account.name,
      account_type: account.account_type,
      currency: String(account.currency),
      institution: account.institution ?? '',
      official_number: account.official_number ?? '',
      initial_balance: account.balance,
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyAccount })
  }

  const handleDelete = (account) => {
    if (!window.confirm(`Delete "${account.name}"? Its transactions are deleted too.`)) return
    remove.mutate(account.id)
  }

  const mutationError = create.error ?? update.error ?? remove.error

  return (
    <div>
      <FormPanel
        title="Accounts"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Add account"
      >
        <form onSubmit={form.handleSubmit}>
          <Alert>{form.formError}</Alert>
          {mutationError && <Alert>{mutationError.message}</Alert>}

          <div className="inline-fields">
            <TextField
              label="Name *"
              name="name"
              value={form.values.name}
              onChange={form.handleChange}
              error={form.errors.name}
              required
            />
            <SelectField
              label="Type *"
              name="account_type"
              value={form.values.account_type}
              onChange={form.handleChange}
              options={ACCOUNT_TYPES}
              error={form.errors.account_type}
            />
            <SelectField
              label="Currency *"
              name="currency"
              value={form.values.currency}
              onChange={form.handleChange}
              options={currencyOptions}
              placeholder="Select a currency"
              error={form.errors.currency}
              required
            />
            <TextField
              label={editingId ? 'Current balance (read-only)' : 'Opening balance'}
              name="initial_balance"
              type="number"
              step="0.01"
              value={form.values.initial_balance}
              onChange={form.handleChange}
              error={form.errors.initial_balance}
              disabled={Boolean(editingId)}
              hint={
                editingId
                  ? 'Balances change through transactions.'
                  : 'Applied to the account right after it is created.'
              }
            />
            <TextField
              label="Institution"
              name="institution"
              value={form.values.institution}
              onChange={form.handleChange}
              error={form.errors.institution}
            />
            <TextField
              label="Account number"
              name="official_number"
              value={form.values.official_number}
              onChange={form.handleChange}
              error={form.errors.official_number}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {editingId ? 'Save changes' : 'Create account'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {accounts.length === 0 && !isLoading ? (
        <EmptyState message="No accounts yet. Add your first account to start logging transactions." />
      ) : (
        <DataTable
          columns={['Name', 'Type', 'Balance', 'Currency', 'Institution', 'Created', 'Actions']}
          isLoading={isLoading}
        >
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>
                {account.name}
                {!account.is_active && <em className="text-muted"> (inactive)</em>}
              </td>
              <td>{account.account_type_display}</td>
              <td className="numeric">
                {formatMoney(account.balance, account.currency_detail?.code)}
              </td>
              <td>{account.currency_detail?.code ?? account.currency}</td>
              <td>{account.institution || '—'}</td>
              <td>{formatDate(account.created_date)}</td>
              <td>
                <button type="button" className="btn btn-ghost" onClick={() => startEdit(account)}>
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDelete(account)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </div>
  )
}
