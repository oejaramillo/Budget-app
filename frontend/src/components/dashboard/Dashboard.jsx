import { useState } from 'react'

import { useCurrencies } from '../../hooks/useCurrencies'
import { useNetWorth } from '../../hooks/useReports'
import { useMonthlyTotals, useTransactionSummary } from '../../hooks/useTransactions'
import { usePortfolio } from '../../hooks/useInvestments'
import { currentMonthRange, formatMoney, formatPercent } from '../../utils/format'
import { Alert, DataTable, EmptyState, StatCard } from '../ui/Feedback'

/**
 * Overview tab: net worth, period totals, monthly trend and category breakdown.
 *
 * All totals are computed by the backend so the browser never adds money, and
 * each is scoped to the authenticated user.
 *
 * @param {{targetCurrency?: string}} props
 */
export default function Dashboard({ targetCurrency }) {
  const [range] = useState(currentMonthRange())
  const [months, setMonths] = useState(6)

  const summary = useTransactionSummary({ start: range.start, end: range.end, target: targetCurrency })
  const monthly = useMonthlyTotals(months)
  const netWorth = useNetWorth(targetCurrency)
  const portfolio = usePortfolio(targetCurrency)
  const { currencies } = useCurrencies()

  const principal = currencies.find((currency) => currency.principal)
  const displayCurrency = targetCurrency ?? principal?.code

  const totals = summary.data
  const net = Number(totals?.net ?? 0)
  const worth = netWorth.data
  const investments = portfolio.data

  const convertedTotal = worth?.converted_total ?? null
  const perCurrency = worth?.per_currency ?? []

  if (summary.isError || netWorth.isError) {
    return <Alert>Could not load the dashboard. Check that the backend is reachable.</Alert>
  }

  return (
    <div>
      <div className="stat-grid">
        <StatCard
          label="Net worth"
          value={
            convertedTotal !== null && convertedTotal !== undefined
              ? formatMoney(convertedTotal, displayCurrency)
              : formatMoney(perCurrency[0]?.total, perCurrency[0]?.currency)
          }
          hint={
            convertedTotal !== null && convertedTotal !== undefined
              ? `Converted to ${displayCurrency}`
              : perCurrency.length > 1
                ? 'Multiple currencies — pick a target in Currencies'
                : undefined
          }
        />
        <StatCard
          label="Income this month"
          value={formatMoney(totals?.total_income, displayCurrency)}
          tone="pos"
        />
        <StatCard
          label="Expenses this month"
          value={formatMoney(totals?.total_expenses, displayCurrency)}
          tone="neg"
        />
        <StatCard
          label="Net this month"
          value={formatMoney(totals?.net, displayCurrency)}
          tone={net < 0 ? 'neg' : 'pos'}
          hint={`${totals?.transaction_count ?? 0} transaction(s)`}
        />
        {investments && Number(investments.total_market_value) > 0 && (
          <StatCard
            label="Investments"
            value={formatMoney(investments.total_market_value, displayCurrency)}
            tone={Number(investments.unrealised_gain) < 0 ? 'neg' : 'pos'}
            hint={`${formatPercent(investments.unrealised_gain_percent)} unrealised`}
          />
        )}
      </div>

      <div className="row-between mb-2">
        <h3 style={{ margin: 0 }}>Monthly trend</h3>
        <label>
          Window{' '}
          <select
            className="form-input"
            style={{ display: 'inline-block', width: 'auto', padding: '6px 10px' }}
            value={months}
            onChange={(event) => setMonths(Number(event.target.value))}
          >
            <option value={3}>3 months</option>
            <option value={6}>6 months</option>
            <option value={12}>12 months</option>
          </select>
        </label>
      </div>

      {monthly.data?.length ? (
        <DataTable columns={['Month', 'Income', 'Expenses', 'Net', 'Transactions']} isLoading={monthly.isLoading}>
          {monthly.data.map((row) => (
            <tr key={row.month}>
              <td>{row.month}</td>
              <td className="numeric pos">{formatMoney(row.income)}</td>
              <td className="numeric neg">{formatMoney(row.expenses)}</td>
              <td className={`numeric ${Number(row.net) < 0 ? 'neg' : 'pos'}`}>
                {formatMoney(row.net)}
              </td>
              <td className="numeric">{row.count}</td>
            </tr>
          ))}
        </DataTable>
      ) : (
        <EmptyState message="No activity yet in this window." />
      )}

      <h3 className="mt-4 mb-2">Spending by category this month</h3>
      {totals?.by_category?.length ? (
        <DataTable columns={['Category', 'Total', 'Transactions']}>
          {totals.by_category.map((row) => (
            <tr key={`${row.category_id}-${row.category_name}`}>
              <td>{row.category_name}</td>
              <td className="numeric">{formatMoney(row.total, displayCurrency)}</td>
              <td className="numeric">{row.count}</td>
            </tr>
          ))}
        </DataTable>
      ) : (
        <EmptyState message="No expenses recorded this month." />
      )}

      {perCurrency.length > 1 && (
        <>
          <h3 className="mt-4 mb-2">Balances by currency</h3>
          <DataTable columns={['Currency', 'Total']}>
            {perCurrency.map((row) => (
              <tr key={row.currency}>
                <td>{row.currency}</td>
                <td className="numeric">{formatMoney(row.total, row.currency)}</td>
              </tr>
            ))}
          </DataTable>
        </>
      )}
    </div>
  )
}
