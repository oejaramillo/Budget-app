import { useState } from 'react'

import { useBudgets } from '../../hooks/useBudgets'
import { useAccounts } from '../../hooks/useAccounts'
import { useCurrencies } from '../../hooks/useCurrencies'
import { useForm } from '../../hooks/useForm'
import { currentMonthRange, formatMoney, formatPercent } from '../../utils/format'
import { Alert, DataTable, EmptyState, StatCard } from '../ui/Feedback'
import { SelectField, TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

/**
 * Budgets CRUD plus a progress view.
 *
 * `spent_amount` and `remaining_amount` come from the backend (annotated in the
 * list query), so the client never sums money itself.
 */
export default function BudgetsManager() {
  const { budgets, isLoading, create, update, remove } = useBudgets()
  const { accounts } = useAccounts()
  const { currencies } = useCurrencies()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const period = currentMonthRange()
  const currencyOptions = currencies.map((currency) => ({
    value: currency.id,
    label: `${currency.code} — ${currency.name}`,
  }))

  const emptyBudget = {
    name: '',
    min_amount: '0.00',
    max_amount: '',
    currency: '',
    start_date: period.start,
    end_date: period.end,
    accounts: [],
  }

  const form = useForm({
    initialValues: emptyBudget,
    onSubmit: async (values) => {
      const payload = {
        name: values.name.trim(),
        min_amount: values.min_amount || '0.00',
        max_amount: values.max_amount,
        currency: Number(values.currency),
        start_date: values.start_date,
        end_date: values.end_date,
        accounts: (values.accounts ?? []).map(Number),
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      return create.mutateAsync(payload)
    },
    onSuccess: () => {
      form.reset({ ...emptyBudget })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const startEdit = (budget) => {
    setEditingId(budget.id)
    setShowForm(true)
    form.reset({
      name: budget.name,
      min_amount: budget.min_amount,
      max_amount: budget.max_amount,
      currency: String(budget.currency),
      start_date: budget.start_date,
      end_date: budget.end_date,
      accounts: (budget.accounts ?? []).map(String),
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyBudget })
  }

  const handleDelete = (budget) => {
    if (!window.confirm(`Delete budget "${budget.name}"?`)) return
    remove.mutate(budget.id)
  }

  const toggleAccount = (accountId) => {
    const current = (form.values.accounts ?? []).map(String)
    const id = String(accountId)
    form.setField(
      'accounts',
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id]
    )
  }

  const mutationError = create.error ?? update.error ?? remove.error

  return (
    <div>
      <FormPanel
        title="Budgets"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Add budget"
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
              label="Minimum *"
              name="min_amount"
              type="number"
              step="0.01"
              value={form.values.min_amount}
              onChange={form.handleChange}
              error={form.errors.min_amount}
              required
            />
            <TextField
              label="Limit (maximum) *"
              name="max_amount"
              type="number"
              step="0.01"
              value={form.values.max_amount}
              onChange={form.handleChange}
              error={form.errors.max_amount}
              required
            />
            <TextField
              label="Start date *"
              name="start_date"
              type="date"
              value={form.values.start_date}
              onChange={form.handleChange}
              error={form.errors.start_date}
              required
            />
            <TextField
              label="End date *"
              name="end_date"
              type="date"
              value={form.values.end_date}
              onChange={form.handleChange}
              error={form.errors.end_date}
              required
            />
          </div>

          {accounts.length > 0 && (
            <div className="form-group">
              <span className="form-label">Accounts covered</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                {accounts.map((account) => (
                  <label key={account.id} style={{ display: 'flex', gap: '0.4rem' }}>
                    <input
                      type="checkbox"
                      checked={(form.values.accounts ?? [])
                        .map(String)
                        .includes(String(account.id))}
                      onChange={() => toggleAccount(account.id)}
                    />
                    {account.name}
                  </label>
                ))}
              </div>
              {form.errors.accounts && <Alert>{form.errors.accounts}</Alert>}
            </div>
          )}

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {editingId ? 'Save changes' : 'Create budget'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {budgets.length === 0 && !isLoading ? (
        <EmptyState message="No budgets yet. Set a spending limit to track it here." />
      ) : (
        <>
          <div className="stat-grid">
            {budgets.slice(0, 4).map((budget) => {
              const spent = Number(budget.spent_amount ?? 0)
              const limit = Number(budget.max_amount)
              const percent = limit > 0 ? (spent / limit) * 100 : 0
              return (
                <StatCard
                  key={budget.id}
                  label={budget.name}
                  value={formatMoney(spent, budget.currency_detail?.code)}
                  tone={spent > limit ? 'neg' : undefined}
                  hint={`of ${formatMoney(limit, budget.currency_detail?.code)} · ${formatPercent(
                    percent,
                    1
                  )} used`}
                />
              )
            })}
          </div>

          <DataTable
            columns={['Name', 'Period', 'Limit', 'Spent', 'Remaining', 'Actions']}
            isLoading={isLoading}
          >
            {budgets.map((budget) => {
              const code = budget.currency_detail?.code
              const spent = Number(budget.spent_amount ?? 0)
              const remaining = Number(budget.max_amount) - spent
              return (
                <tr key={budget.id}>
                  <td>{budget.name}</td>
                  <td>
                    {budget.start_date} → {budget.end_date}
                  </td>
                  <td className="numeric">{formatMoney(budget.max_amount, code)}</td>
                  <td className="numeric">{formatMoney(spent, code)}</td>
                  <td className={`numeric ${remaining < 0 ? 'neg' : 'pos'}`}>
                    {formatMoney(remaining, code)}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => startEdit(budget)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(budget)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              )
            })}
          </DataTable>
        </>
      )}
    </div>
  )
}
