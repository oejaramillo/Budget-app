import { useState } from 'react'

import { useTransactions } from '../../hooks/useTransactions'
import { useAccounts } from '../../hooks/useAccounts'
import { useCategories } from '../../hooks/useCategories'
import { useBudgets } from '../../hooks/useBudgets'
import { useForm } from '../../hooks/useForm'
import { TRANSACTION_TYPES } from '../../constants'
import { formatDate, formatMoney, today } from '../../utils/format'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import { SelectField, TextAreaField, TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

const emptyTransaction = {
  account: '',
  destination_account: '',
  transaction_type: 'expense',
  transaction_date: today(),
  amount: '',
  description: '',
  category: '',
  budget: '',
}

/**
 * Transactions CRUD.
 *
 * The form mirrors the backend rules so mistakes are caught before the request:
 * transfers need a destination account and cannot be categorised, and the
 * currency is always the account's own currency (the backend enforces this, so
 * the field is not exposed here).
 */
export default function TransactionsManager() {
  const { transactions, isLoading, create, update, remove } = useTransactions()
  const { accounts } = useAccounts()
  const { categories } = useCategories()
  const { budgets } = useBudgets()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)

  const accountOptions = accounts.map((account) => ({
    value: account.id,
    label: `${account.name} (${account.currency_detail?.code ?? '?'})`,
  }))
  const categoryOptions = categories.map((category) => ({
    value: category.id,
    label: category.name,
  }))
  const budgetOptions = budgets.map((budget) => ({ value: budget.id, label: budget.name }))

  const form = useForm({
    initialValues: emptyTransaction,
    onSubmit: async (values) => {
      const isTransfer = values.transaction_type === 'transfer'
      const payload = {
        account: Number(values.account),
        transaction_type: values.transaction_type,
        transaction_date: values.transaction_date,
        amount: values.amount,
        description: values.description.trim(),
        destination_account: isTransfer ? Number(values.destination_account) : null,
        category: isTransfer || !values.category ? null : Number(values.category),
        budget: isTransfer || !values.budget ? null : Number(values.budget),
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      return create.mutateAsync(payload)
    },
    onSuccess: () => {
      form.reset({ ...emptyTransaction, transaction_date: today() })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const startEdit = (transaction) => {
    setEditingId(transaction.id)
    setShowForm(true)
    form.reset({
      account: String(transaction.account),
      destination_account: transaction.destination_account
        ? String(transaction.destination_account)
        : '',
      transaction_type: transaction.transaction_type,
      transaction_date: transaction.transaction_date,
      amount: transaction.amount,
      description: transaction.description ?? '',
      category: transaction.category ? String(transaction.category) : '',
      budget: transaction.budget ? String(transaction.budget) : '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyTransaction, transaction_date: today() })
  }

  const handleDelete = (transaction) => {
    if (!window.confirm('Delete this transaction? The account balance will be corrected.')) return
    remove.mutate(transaction.id)
  }

  const isTransfer = form.values.transaction_type === 'transfer'
  const mutationError = create.error ?? update.error ?? remove.error

  return (
    <div>
      <FormPanel
        title="Transactions"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Log transaction"
      >
        <form onSubmit={form.handleSubmit}>
          <Alert>{form.formError}</Alert>
          {mutationError && <Alert>{mutationError.message}</Alert>}
          {accounts.length === 0 && (
            <Alert variant="info">
              Create an account first — every transaction belongs to one.
            </Alert>
          )}

          <div className="inline-fields">
            <SelectField
              label="Account *"
              name="account"
              value={form.values.account}
              onChange={form.handleChange}
              options={accountOptions}
              placeholder="Select an account"
              error={form.errors.account}
              required
            />
            <SelectField
              label="Type *"
              name="transaction_type"
              value={form.values.transaction_type}
              onChange={form.handleChange}
              options={TRANSACTION_TYPES}
              error={form.errors.transaction_type}
            />
            {isTransfer && (
              <SelectField
                label="Destination account *"
                name="destination_account"
                value={form.values.destination_account}
                onChange={form.handleChange}
                options={accountOptions.filter(
                  (option) => String(option.value) !== String(form.values.account)
                )}
                placeholder="Select an account"
                error={form.errors.destination_account}
                required
              />
            )}
            <TextField
              label="Date *"
              name="transaction_date"
              type="date"
              value={form.values.transaction_date}
              onChange={form.handleChange}
              error={form.errors.transaction_date}
              required
            />
            <TextField
              label="Amount *"
              name="amount"
              type="number"
              step="0.01"
              value={form.values.amount}
              onChange={form.handleChange}
              error={form.errors.amount}
              hint="Always positive."
              required
            />
            {!isTransfer && (
              <>
                <SelectField
                  label="Category"
                  name="category"
                  value={form.values.category}
                  onChange={form.handleChange}
                  options={categoryOptions}
                  placeholder="No category"
                  error={form.errors.category}
                />
                <SelectField
                  label="Budget"
                  name="budget"
                  value={form.values.budget}
                  onChange={form.handleChange}
                  options={budgetOptions}
                  placeholder="No budget"
                  error={form.errors.budget}
                />
              </>
            )}
          </div>

          <TextAreaField
            label="Description"
            name="description"
            value={form.values.description}
            onChange={form.handleChange}
            error={form.errors.description}
          />

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {editingId ? 'Save changes' : 'Log transaction'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {transactions.length === 0 && !isLoading ? (
        <EmptyState message="No transactions yet. Log your first movement above." />
      ) : (
        <DataTable
          columns={['Date', 'Account', 'Type', 'Amount', 'Category', 'Description', 'Actions']}
          isLoading={isLoading}
        >
          {transactions.map((transaction) => {
            const isNegative = transaction.transaction_type !== 'income'
            return (
              <tr key={transaction.id}>
                <td>{formatDate(transaction.transaction_date)}</td>
                <td>
                  {transaction.account_detail?.name ?? '—'}
                  {transaction.destination_account_detail && (
                    <span className="text-muted">
                      {' → '}
                      {transaction.destination_account_detail.name}
                    </span>
                  )}
                </td>
                <td>{transaction.transaction_type_display}</td>
                <td className={`numeric ${isNegative ? 'neg' : 'pos'}`}>
                  {formatMoney(transaction.amount, transaction.currency_detail?.code)}
                </td>
                <td>{transaction.category_detail?.name ?? '—'}</td>
                <td>{transaction.description || '—'}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => startEdit(transaction)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(transaction)}
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
