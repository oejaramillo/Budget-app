import { useMemo, useState } from 'react'

import {
  useDescriptionSuggestions,
  useLedgerStats,
  useTransactions,
} from '../../hooks/useTransactions'
import { useAccounts } from '../../hooks/useAccounts'
import { useCategories } from '../../hooks/useCategories'
import { useBudgets } from '../../hooks/useBudgets'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useForm } from '../../hooks/useForm'
import { describeApiError } from '../../api'
import { TRANSACTION_TYPES } from '../../constants'
import { formatDate, formatMoney, toDateInput, toIsoDate, today } from '../../utils/format'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import DescriptionInput from '../ui/DescriptionInput'
import { SelectField, TextField } from '../ui/FormFields'

/** Amounts offered as one-tap buttons: small, common, and easy to overwrite. */
const QUICK_AMOUNTS = ['1', '5', '10', '20', '50']

/** Period presets, because "show me March" is the common question. */
const PERIODS = [
  { value: 'last-90', label: 'Last 3 months' },
  { value: 'this-month', label: 'This month' },
  { value: 'last-month', label: 'Last month' },
  { value: 'this-year', label: 'This year' },
  { value: 'all', label: 'All time' },
]

/**
 * Date bounds for a preset. `all` returns no bounds at all.
 * @param {string} preset
 */
function periodRange(preset) {
  const now = new Date()
  const monthStart = (date) => new Date(date.getFullYear(), date.getMonth(), 1)
  const monthEnd = (date) => new Date(date.getFullYear(), date.getMonth() + 1, 0)

  switch (preset) {
    case 'this-month':
      return { date_from: toIsoDate(monthStart(now)), date_to: toIsoDate(monthEnd(now)) }
    case 'last-month': {
      const previous = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return {
        date_from: toIsoDate(monthStart(previous)),
        date_to: toIsoDate(monthEnd(previous)),
      }
    }
    case 'last-90':
      return {
        date_from: toIsoDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 89)),
        date_to: toIsoDate(now),
      }
    case 'this-year':
      return { date_from: `${now.getFullYear()}-01-01`, date_to: `${now.getFullYear()}-12-31` }
    case 'all':
    default:
      return {}
  }
}

/**
 * Sort orders.
 *
 * `date` is the default and is what a ledger means by "ordered": newest month
 * first, and *within a month* the most recently entered row first. The backend
 * implements that (see `TransactionOrderingFilter`); the value sent here just asks
 * for it. Keeping the month primary means the historical record stays
 * chronological, while the insertion tie-break means an entry you just added leads
 * a batch imported earlier for the same month.
 *
 * `added` ignores the transaction date entirely — useful to review a logging
 * session that spanned several dates.
 */
const SORTS = [
  { value: 'date', label: 'Date (newest first)', ordering: '-transaction_date' },
  { value: 'added', label: 'Recently added', ordering: '-created_date,-id' },
  { value: '-amount', label: 'Largest first', ordering: '-amount' },
  { value: 'amount', label: 'Smallest first', ordering: 'amount' },
]

/** True when a row was entered recently enough to deserve a marker. */
function isRecentlyAdded(createdDate) {
  if (!createdDate) return false
  const age = Date.now() - new Date(createdDate).getTime()
  return age >= 0 && age < 24 * 60 * 60 * 1000
}

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
 * Log and review transactions — the screen the app exists for.
 *
 * Layout decisions, all in service of speed:
 *
 * * **Keyboard first.** The whole quick-entry block is one form, so Enter submits
 *   from any field.
 * * **The account and date persist** between entries; only amount and description
 *   reset, because several entries for one account on one day is the common case.
 * * **Descriptions autocomplete** from the user's own history, ranked by how often
 *   they have used them.
 * * **Filters run on the server** and the list is paginated, so a ledger of any size
 *   stays responsive.
 * * **Any row can be edited in place**, which is what you need when an amount or
 *   description was entered wrong.
 */
export default function TransactionsManager() {
  const [filters, setFilters] = useState({
    period: 'last-90',
    account: '',
    type: '',
  })
  const [sortBy, setSortBy] = useState('date')
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const debouncedSearch = useDebouncedValue(searchInput, 350)

  const [lastAdded, setLastAdded] = useState(null)
  const [editing, setEditing] = useState(null)
  const [editValues, setEditValues] = useState({})
  const [editError, setEditError] = useState('')

  const accountFilter = filters.account ? Number(filters.account) : undefined

  const query = useMemo(
    () => ({
      ...periodRange(filters.period),
      ...(accountFilter ? { account: accountFilter } : {}),
      ...(filters.type ? { transaction_type: filters.type } : {}),
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
      ordering: (SORTS.find((option) => option.value === sortBy) ?? SORTS[0]).ordering,
      page,
    }),
    [filters.period, accountFilter, filters.type, debouncedSearch, page, sortBy]
  )

  const {
    transactions,
    count,
    hasNext,
    hasPrevious,
    isLoading,
    isFetching,
    error,
    create,
    update,
    remove,
  } = useTransactions(query, { paged: true })

  const { accounts } = useAccounts()
  const { categories } = useCategories()
  const { budgets } = useBudgets()
  const stats = useLedgerStats()

  // Suggestions are scoped to the account being logged to, which keeps them relevant
  // without a separate round trip per keystroke.
  const suggestions = useDescriptionSuggestions({
    ...(accountFilter ? { account: accountFilter } : {}),
    limit: 100,
  })

  const suggestionList = suggestions.data ?? []

  const accountOptions = accounts.map((item) => ({
    value: item.id,
    label: `${item.name} (${item.currency_detail?.code ?? '?'})`,
  }))
  const categoryOptions = categories.map((item) => ({ value: item.id, label: item.name }))
  const budgetOptions = budgets.map((item) => ({ value: item.id, label: item.name }))

  // Default to the newest account seen in the list; it is almost always the right one.
  const defaultAccount = useMemo(() => {
    const recent = transactions.find((row) => row.account)
    if (recent) return String(recent.account)
    return accounts[0] ? String(accounts[0].id) : ''
  }, [transactions, accounts])

  const form = useForm({
    initialValues: emptyTransaction,
    onSubmit: async (values) => {
      const target = values.account || defaultAccount
      if (!target) throw new Error('Create an account before logging transactions.')
      const transfer = values.transaction_type === 'transfer'

      return create.mutateAsync({
        account: Number(target),
        transaction_type: values.transaction_type,
        transaction_date: values.transaction_date,
        amount: values.amount,
        description: values.description.trim(),
        destination_account: transfer ? Number(values.destination_account) : null,
        category: transfer || !values.category ? null : Number(values.category),
        budget: transfer || !values.budget ? null : Number(values.budget),
      })
    },
    onSuccess: (created) => {
      // Confirm what was saved. Without this it is impossible to tell whether an
      // entry that is not on screen was rejected or merely filtered out.
      const range = periodRange(filters.period)
      const outsideRange =
        Boolean(range.date_from && created.transaction_date < range.date_from) ||
        Boolean(range.date_to && created.transaction_date > range.date_to)

      setLastAdded({ ...created, outsideRange })

      // Keep account, date, type, category and budget; clear what changes per entry.
      form.setValues((previous) => ({
        ...previous,
        amount: '',
        description: '',
        destination_account: '',
      }))
      form.setErrors({})
      form.setFormError('')
      setPage(1)
    },
  })

  const effectiveAccount = form.values.account || defaultAccount
  const formIsTransfer = form.values.transaction_type === 'transfer'
  const mutationError = create.error ?? update.error ?? remove.error

  const startEdit = (transaction) => {
    setEditError('')
    setEditing(transaction.id)
    setEditValues({
      transaction_date: toDateInput(transaction.transaction_date),
      amount: transaction.amount,
      description: transaction.description ?? '',
      category: transaction.category ? String(transaction.category) : '',
      budget: transaction.budget ? String(transaction.budget) : '',
    })
  }

  const cancelEdit = () => {
    setEditing(null)
    setEditError('')
    setEditValues({})
  }

  const saveEdit = async (transaction) => {
    setEditError('')
    const isTransfer = transaction.transaction_type === 'transfer'
    try {
      await update.mutateAsync({
        id: transaction.id,
        data: {
          transaction_date: editValues.transaction_date,
          amount: editValues.amount,
          description: editValues.description.trim(),
          category: isTransfer || !editValues.category ? null : Number(editValues.category),
          budget: isTransfer || !editValues.budget ? null : Number(editValues.budget),
        },
      })
      cancelEdit()
    } catch (mutationFailure) {
      setEditError(describeApiError(mutationFailure))
    }
  }

  const handleDelete = (transaction) => {
    const label = `${formatMoney(transaction.amount)} on ${formatDate(transaction.transaction_date)}`
    if (!window.confirm(`Delete ${label}? The account balance will be corrected.`)) return
    remove.mutate(transaction.id)
  }

  const resetFilters = () => {
    setFilters({ period: 'all', account: '', type: '' })
    setSearchInput('')
    setPage(1)
  }

  const pageSize = query.page_size ?? 100
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const filtered = Boolean(debouncedSearch || filters.account || filters.type || filters.period !== 'all')

  return (
    <div>
      {/* -- Quick entry ------------------------------------------------------ */}
      <form onSubmit={form.handleSubmit}>
        <div className="row-between mb-2">
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Log a transaction</h2>
          {stats.data && (
            <small className="text-muted">
              {stats.data.count.toLocaleString()} entries
              {stats.data.first_date ? ` since ${formatDate(stats.data.first_date)}` : ''}
              {stats.data.uncategorised > 0 ? ` · ${stats.data.uncategorised} uncategorised` : ''}
            </small>
          )}
        </div>

        <Alert>{form.formError}</Alert>
        {mutationError && <Alert>{describeApiError(mutationError)}</Alert>}

        <div className="inline-fields">
          <TextField
            label="Amount *"
            name="amount"
            type="number"
            step="0.01"
            value={form.values.amount}
            onChange={form.handleChange}
            error={form.errors.amount}
            placeholder="0.00"
            autoFocus
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
          <SelectField
            label="Account *"
            name="account"
            value={effectiveAccount}
            onChange={form.handleChange}
            options={accountOptions}
            placeholder={accountOptions.length ? 'Select an account' : 'No accounts yet'}
            error={form.errors.account}
            required
          />
          <TextField
            label="Date * (DD/MM/YYYY)"
            name="transaction_date"
            type="date"
            value={form.values.transaction_date}
            onChange={form.handleChange}
            error={form.errors.transaction_date}
            hint={
              form.values.transaction_date
                ? formatDate(form.values.transaction_date)
                : undefined
            }
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="description">
            Description
          </label>
          <DescriptionInput
            id="description"
            value={form.values.description}
            onChange={(next) => form.setField('description', next)}
            suggestions={suggestionList}
            isLoading={suggestions.isLoading}
            placeholder="Type to reuse a description you have used before"
          />
        </div>

        <div className="inline-fields">
          {formIsTransfer ? (
            <SelectField
              label="Destination account *"
              name="destination_account"
              value={form.values.destination_account}
              onChange={form.handleChange}
              options={accountOptions.filter(
                (option) => String(option.value) !== String(effectiveAccount)
              )}
              placeholder="Select an account"
              error={form.errors.destination_account}
              required
            />
          ) : (
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

        <div className="row-between" style={{ gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            {QUICK_AMOUNTS.map((amount) => (
              <button
                key={amount}
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => form.setField('amount', amount)}
              >
                {amount}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <small className="text-muted">Enter saves</small>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {form.isSubmitting ? 'Saving…' : 'Add entry'}
            </button>
          </div>
        </div>
      </form>

      {lastAdded && (
        <div className="alert alert-success mt-3" role="status">
          <div className="row-between" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
            <span>
              Saved <strong>{lastAdded.description || '(no description)'}</strong> —{' '}
              {formatMoney(lastAdded.amount, lastAdded.currency_detail?.code)} on{' '}
              {formatDate(lastAdded.transaction_date)}.
              {lastAdded.outsideRange
                ? ' The current period excludes that date, so it is pinned above the list.'
                : ''}
            </span>
            <span style={{ display: 'flex', gap: '0.5rem' }}>
              {lastAdded.outsideRange && (
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => {
                    setFilters((previous) => ({ ...previous, period: 'all' }))
                    setPage(1)
                  }}
                >
                  Show all time
                </button>
              )}
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setLastAdded(null)}
              >
                Dismiss
              </button>
            </span>
          </div>
        </div>
      )}

      {/* -- Filters ---------------------------------------------------------- */}
      <div className="tabs mt-4 mb-2" role="tablist">
        {PERIODS.map((period) => (
          <button
            key={period.value}
            type="button"
            role="tab"
            className="tab"
            aria-selected={filters.period === period.value}
            onClick={() => {
              setFilters((previous) => ({ ...previous, period: period.value }))
              setPage(1)
            }}
          >
            {period.label}
          </button>
        ))}
      </div>

      <div className="inline-fields mb-3">
        <TextField
          label="Search"
          name="search"
          value={searchInput}
          onChange={(event) => {
            setSearchInput(event.target.value)
            setPage(1)
          }}
          placeholder="description, account or category"
          hint={isFetching ? 'Searching…' : undefined}
        />
        <SelectField
          label="Account"
          name="filter_account"
          value={filters.account}
          onChange={(event) => {
            setFilters((previous) => ({ ...previous, account: event.target.value }))
            setPage(1)
          }}
          options={accountOptions}
          placeholder="All accounts"
        />
        <SelectField
          label="Type"
          name="filter_type"
          value={filters.type}
          onChange={(event) => {
            setFilters((previous) => ({ ...previous, type: event.target.value }))
            setPage(1)
          }}
          options={TRANSACTION_TYPES}
          placeholder="All types"
        />
        <SelectField
          label="Sort"
          name="filter_sort"
          value={sortBy}
          onChange={(event) => {
            setSortBy(event.target.value)
            setPage(1)
          }}
          options={SORTS.map((option) => ({ value: option.value, label: option.label }))}
        />
      </div>

      <div className="row-between mb-2" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <span className="text-muted">
          {count.toLocaleString()} {count === 1 ? 'entry' : 'entries'}
          {isFetching ? ' · updating…' : ''}
        </span>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={!hasPrevious}
          >
            ← Newer
          </button>
          <span className="text-muted">
            page {page} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={() => setPage((current) => current + 1)}
            disabled={!hasNext}
          >
            Older →
          </button>
          {filtered && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      {error && <Alert>{describeApiError(error)}</Alert>}
      {editError && <Alert>{editError}</Alert>}

      {/* -- Table ------------------------------------------------------------ */}
      {transactions.length === 0 && !isLoading ? (
        <EmptyState
          message={
            filtered
              ? 'No entries match these filters.'
              : 'No transactions yet. Log your first one above.'
          }
        />
      ) : (
        <DataTable
          columns={['Date', 'Account', 'Type', 'Amount', 'Category', 'Description', '']}
          isLoading={isLoading}
        >
          {lastAdded && (
            <tr
              key={`just-added-${lastAdded.id}`}
              className="row-just-added"
              title="This is the entry you just saved"
            >
              <td>{formatDate(lastAdded.transaction_date)}</td>
              <td>{lastAdded.account_detail?.name ?? '—'}</td>
              <td>{lastAdded.transaction_type_display}</td>
              <td
                className={`numeric ${
                  lastAdded.transaction_type === 'income' ? 'pos' : 'neg'
                }`}
              >
                {formatMoney(lastAdded.amount, lastAdded.currency_detail?.code)}
              </td>
              <td>{lastAdded.category_detail?.name ?? '—'}</td>
              <td>{lastAdded.description || '—'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <span className="text-muted">just added</span>
              </td>
            </tr>
          )}

          {transactions.map((transaction) => {
            const isTransfer = transaction.transaction_type === 'transfer'
            const isNegative = transaction.transaction_type !== 'income'

            if (editing === transaction.id) {
              return (
                <tr key={transaction.id} style={{ background: 'var(--light-gray)' }}>
                  <td>
                    <input
                      className="form-input"
                      type="date"
                      aria-label="Date"
                      style={{ padding: '4px 8px' }}
                      value={toDateInput(editValues.transaction_date)}
                      onChange={(event) =>
                        setEditValues((previous) => ({
                          ...previous,
                          transaction_date: event.target.value,
                        }))
                      }
                    />
                  </td>
                  <td>{transaction.account_detail?.name ?? '—'}</td>
                  <td>{transaction.transaction_type_display}</td>
                  <td>
                    <input
                      className="form-input"
                      type="number"
                      step="0.01"
                      aria-label="Amount"
                      style={{ padding: '4px 8px', minWidth: '90px' }}
                      value={editValues.amount}
                      onChange={(event) =>
                        setEditValues((previous) => ({ ...previous, amount: event.target.value }))
                      }
                    />
                  </td>
                  <td>
                    <select
                      className="form-input"
                      aria-label="Category"
                      style={{ padding: '4px 8px' }}
                      value={editValues.category}
                      disabled={isTransfer}
                      onChange={(event) =>
                        setEditValues((previous) => ({ ...previous, category: event.target.value }))
                      }
                    >
                      <option value="">No category</option>
                      {categoryOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      className="form-input"
                      aria-label="Description"
                      title="Edit the description"
                      style={{ padding: '4px 8px', minWidth: '160px' }}
                      value={editValues.description}
                      onChange={(event) =>
                        setEditValues((previous) => ({
                          ...previous,
                          description: event.target.value,
                        }))
                      }
                      onKeyDown={(event) => {
                        if (event.key === 'Escape') cancelEdit()
                      }}
                    />
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => saveEdit(transaction)}
                      disabled={update.isPending}
                    >
                      Save
                    </button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={cancelEdit}>
                      Cancel
                    </button>
                  </td>
                </tr>
              )
            }

            return (
              <tr key={transaction.id}>
                <td>{formatDate(transaction.transaction_date)}</td>
                <td>
                  {isRecentlyAdded(transaction.created_date) && (
                    <span className="badge-new" title="Added in the last 24 hours">
                      new
                    </span>
                  )}
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
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => startEdit(transaction)}
                    title="Edit this entry"
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
