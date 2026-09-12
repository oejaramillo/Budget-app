import { useState } from 'react'

import { useCreateValuation, useHoldings, usePortfolio } from '../../hooks/useInvestments'
import { useAccounts } from '../../hooks/useAccounts'
import { useCurrencies } from '../../hooks/useCurrencies'
import { useForm } from '../../hooks/useForm'
import { describeApiError } from '../../api'
import { formatMoney, formatPercent, today } from '../../utils/format'
import { Alert, DataTable, EmptyState, StatCard } from '../ui/Feedback'
import { SelectField, TextField } from '../ui/FormFields'
import FormPanel from '../ui/FormPanel'

const HOLDING_KINDS = [
  { value: 'stock', label: 'Stock' },
  { value: 'etf', label: 'ETF' },
  { value: 'fund', label: 'Mutual fund' },
  { value: 'bond', label: 'Bond' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'real_estate', label: 'Real estate' },
  { value: 'other', label: 'Other' },
]

const emptyHolding = {
  symbol: '',
  name: '',
  kind: 'stock',
  quantity: '',
  cost_basis: '',
  currency: '',
  account: '',
  opened_date: today(),
  notes: '',
}

/**
 * Holdings and their valuations.
 *
 * Market value is either the most recent valuation or, until one is recorded, the
 * cost basis. Recording a valuation is a separate, explicit action so portfolio
 * history stays auditable.
 */
export default function HoldingsManager() {
  const { holdings, isLoading, create, update, remove } = useHoldings()
  const { accounts } = useAccounts()
  const { currencies } = useCurrencies()
  const portfolio = usePortfolio()
  const createValuation = useCreateValuation()

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [valuingHolding, setValuingHolding] = useState(null)

  const currencyOptions = currencies.map((currency) => ({
    value: currency.id,
    label: `${currency.code} — ${currency.name}`,
  }))
  const accountOptions = accounts.map((account) => ({ value: account.id, label: account.name }))

  const form = useForm({
    initialValues: emptyHolding,
    onSubmit: async (values) => {
      const payload = {
        symbol: values.symbol.trim().toUpperCase(),
        name: values.name.trim(),
        kind: values.kind,
        quantity: values.quantity,
        cost_basis: values.cost_basis,
        currency: Number(values.currency),
        account: values.account ? Number(values.account) : null,
        opened_date: values.opened_date || null,
        notes: values.notes,
      }
      if (editingId) {
        return update.mutateAsync({ id: editingId, data: payload })
      }
      return create.mutateAsync(payload)
    },
    onSuccess: () => {
      form.reset({ ...emptyHolding, opened_date: today() })
      setEditingId(null)
      setShowForm(false)
    },
  })

  const valuationForm = useForm({
    initialValues: { valued_on: today(), value: '', note: '' },
    onSubmit: async (values) =>
      createValuation.mutateAsync({
        holding: valuingHolding.id,
        valued_on: values.valued_on,
        value: values.value,
        note: values.note,
      }),
    onSuccess: () => {
      valuationForm.reset({ valued_on: today(), value: '', note: '' })
      setValuingHolding(null)
    },
  })

  const startEdit = (holding) => {
    setEditingId(holding.id)
    setShowForm(true)
    form.reset({
      symbol: holding.symbol,
      name: holding.name ?? '',
      kind: holding.kind,
      quantity: holding.quantity,
      cost_basis: holding.cost_basis,
      currency: String(holding.currency),
      account: holding.account ? String(holding.account) : '',
      opened_date: holding.opened_date ?? '',
      notes: holding.notes ?? '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setShowForm(false)
    form.reset({ ...emptyHolding, opened_date: today() })
  }

  const handleDelete = (holding) => {
    if (!window.confirm(`Delete holding ${holding.symbol} and its valuations?`)) return
    remove.mutate(holding.id)
  }

  const mutationError = create.error ?? update.error ?? remove.error
  const totals = portfolio.data

  return (
    <div>
      {totals && (
        <div className="stat-grid">
          <StatCard
            label="Portfolio value"
            value={formatMoney(totals.total_market_value, totals.target_currency ?? undefined)}
            hint={`${totals.holding_count} holding(s)`}
          />
          <StatCard
            label="Cost basis"
            value={formatMoney(totals.total_cost_basis, totals.target_currency ?? undefined)}
          />
          <StatCard
            label="Unrealised gain"
            value={formatMoney(totals.unrealised_gain, totals.target_currency ?? undefined)}
            tone={Number(totals.unrealised_gain) < 0 ? 'neg' : 'pos'}
            hint={formatPercent(totals.unrealised_gain_percent)}
          />
        </div>
      )}

      <FormPanel
        title="Investments"
        isOpen={showForm}
        onToggle={() => (showForm ? cancelEdit() : setShowForm(true))}
        openLabel="Add holding"
      >
        <form onSubmit={form.handleSubmit}>
          <Alert>{form.formError}</Alert>
          {mutationError && <Alert>{describeApiError(mutationError)}</Alert>}

          <div className="inline-fields">
            <TextField
              label="Symbol *"
              name="symbol"
              value={form.values.symbol}
              onChange={form.handleChange}
              error={form.errors.symbol}
              placeholder="VWCE"
              required
            />
            <TextField
              label="Name"
              name="name"
              value={form.values.name}
              onChange={form.handleChange}
              error={form.errors.name}
            />
            <SelectField
              label="Kind *"
              name="kind"
              value={form.values.kind}
              onChange={form.handleChange}
              options={HOLDING_KINDS}
              error={form.errors.kind}
            />
            <TextField
              label="Quantity *"
              name="quantity"
              type="number"
              step="0.0000000001"
              value={form.values.quantity}
              onChange={form.handleChange}
              error={form.errors.quantity}
              hint="Fractional amounts allowed."
              required
            />
            <TextField
              label="Cost basis *"
              name="cost_basis"
              type="number"
              step="0.01"
              value={form.values.cost_basis}
              onChange={form.handleChange}
              error={form.errors.cost_basis}
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
            <SelectField
              label="Account"
              name="account"
              value={form.values.account}
              onChange={form.handleChange}
              options={accountOptions}
              placeholder="Not linked"
              error={form.errors.account}
            />
            <TextField
              label="Opened on"
              name="opened_date"
              type="date"
              value={form.values.opened_date}
              onChange={form.handleChange}
              error={form.errors.opened_date}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={form.isSubmitting}>
              {editingId ? 'Save changes' : 'Create holding'}
            </button>
            <button type="button" className="btn btn-outline" onClick={cancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      </FormPanel>

      {valuingHolding && (
        <div className="card mb-3">
          <h3 className="mb-2">New valuation for {valuingHolding.symbol}</h3>
          <form onSubmit={valuationForm.handleSubmit}>
            <Alert>{valuationForm.formError}</Alert>
            {createValuation.error && <Alert>{describeApiError(createValuation.error)}</Alert>}
            <div className="inline-fields">
              <TextField
                label="Date *"
                name="valued_on"
                type="date"
                value={valuationForm.values.valued_on}
                onChange={valuationForm.handleChange}
                error={valuationForm.errors.valued_on}
                required
              />
              <TextField
                label="Value *"
                name="value"
                type="number"
                step="0.01"
                value={valuationForm.values.value}
                onChange={valuationForm.handleChange}
                error={valuationForm.errors.value}
                required
              />
              <TextField
                label="Note"
                name="note"
                value={valuationForm.values.note}
                onChange={valuationForm.handleChange}
                error={valuationForm.errors.note}
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button type="submit" className="btn btn-primary" disabled={valuationForm.isSubmitting}>
                Save valuation
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setValuingHolding(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {holdings.length === 0 && !isLoading ? (
        <EmptyState message="No holdings yet. Add a position to start tracking its value." />
      ) : (
        <DataTable
          columns={[
            'Symbol',
            'Kind',
            'Quantity',
            'Cost basis',
            'Market value',
            'Gain',
            'Actions',
          ]}
          isLoading={isLoading}
        >
          {holdings.map((holding) => {
            const code = holding.currency_detail?.code
            const gain = Number(holding.unrealised_gain)
            return (
              <tr key={holding.id}>
                <td>
                  {holding.symbol}
                  {holding.name && <span className="text-muted"> · {holding.name}</span>}
                </td>
                <td>{holding.kind_display}</td>
                <td className="numeric">{holding.quantity}</td>
                <td className="numeric">{formatMoney(holding.cost_basis, code)}</td>
                <td className="numeric">{formatMoney(holding.market_value, code)}</td>
                <td className={`numeric ${gain < 0 ? 'neg' : 'pos'}`}>
                  {formatMoney(holding.unrealised_gain, code)} ({formatPercent(holding.unrealised_gain_percent, 1)})
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => {
                      valuationForm.reset({ valued_on: today(), value: '', note: '' })
                      setValuingHolding(holding)
                    }}
                  >
                    Value
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => startEdit(holding)}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(holding)}
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
