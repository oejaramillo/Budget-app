import { useMemo, useState } from 'react'

import { useAnalyticsDashboard } from '../../hooks/useAnalytics'
import { describeApiError } from '../../api'
import { formatMoney, formatPercent } from '../../utils/format'
import { Alert, EmptyState } from '../ui/Feedback'
import CategoryDonut from '../charts/CategoryDonut'
import CategoryBars from '../charts/CategoryBars'
import CategoryTrendChart from '../charts/CategoryTrendChart'
import TrendChart from '../charts/TrendChart'
import { MiniStat, OutlookMeter, WeekdayChart } from '../charts/BehaviorCharts'

const RANGES = [
  { value: 12, label: '12 months' },
  { value: 24, label: '24 months' },
  { value: 60, label: '5 years' },
  { value: 120, label: 'All' },
]

/** A KPI tile with its comparison to the previous period. */
function Kpi({ label, value, comparison, tone = '', hint, invert = false }) {
  let delta = null
  if (comparison?.change_percent !== null && comparison?.change_percent !== undefined) {
    const rising = comparison.change > 0
    // For spending, rising is bad; for income and net, rising is good.
    const good = invert ? !rising : rising
    delta = {
      text: `${rising ? '▲' : '▼'} ${formatPercent(Math.abs(comparison.change_percent), 0)}`,
      className: good ? 'pos' : 'neg',
      title: `Previous period: ${formatMoney(comparison.previous)}`,
    }
  }

  return (
    <div className="kpi">
      <span className="kpi__label">{label}</span>
      <strong className={`kpi__value ${tone}`}>{value}</strong>
      <span className="kpi__foot">
        {delta && (
          <span className={delta.className} title={delta.title}>
            {delta.text}
          </span>
        )}
        {hint && <span className="text-muted">{hint}</span>}
      </span>
    </div>
  )
}

/** One insight card. */
function InsightCard({ insight }) {
  const icon = { warning: '▲', good: '▼', neutral: '•' }[insight.tone] ?? '•'
  return (
    <div className={`insight insight--${insight.tone}`}>
      <span className="insight__icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <strong>{insight.title}</strong>
        <p>{insight.detail}</p>
      </div>
    </div>
  )
}

/**
 * Spending dashboard.
 *
 * The point is to answer four questions in order: how much am I spending, is that
 * normal for me, where is it going, and what is changing. Everything is compared
 * against the user's own history rather than a generic target, because "too much"
 * only means anything relative to what a person normally does.
 *
 * Consumption and money movement are kept apart throughout. In this ledger
 * transfers, loan repayments and currency exchange are just over 47% of recorded
 * expenses, so adding them to groceries would make every number on the page wrong.
 */
export default function SpendingDashboard() {
  const [months, setMonths] = useState(24)
  const [showMovement, setShowMovement] = useState(false)

  const { data, isLoading, isError, error, isFetching } = useAnalyticsDashboard({ months })

  const currency = data?.currency

  const consumptionCategories = useMemo(
    () => (data?.top_categories ?? []).filter((row) => !row.is_money_movement),
    [data]
  )
  const movementCategories = useMemo(
    () => (data?.all_categories ?? []).filter((row) => row.is_money_movement),
    [data]
  )

  if (isError) {
    return <Alert>{describeApiError(error)}</Alert>
  }

  if (isLoading && !data) {
    return <p className="text-muted">Building your dashboard…</p>
  }

  if (!data) return <EmptyState message="No analytics available yet." />

  const { totals, comparisons, outlook, monthly, category_trend: categoryTrend } = data
  const current = totals.current
  const movement = current.money_movement

  return (
    <div className="spending">
      {/* -- Controls ------------------------------------------------------- */}
      <div className="row-between mb-3" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Spending dashboard</h2>
          <small className="text-muted">
            {data.period.label} · compared with {data.period.compared_with.label}
            {isFetching ? ' · updating…' : ''}
          </small>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <div className="tabs" role="tablist">
            {RANGES.map((range) => (
              <button
                key={range.value}
                type="button"
                role="tab"
                className="tab"
                aria-selected={months === range.value}
                onClick={() => setMonths(range.value)}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {movement > 0 && (
        <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '-0.5rem' }}>
          Reporting in <strong>{currency}</strong>. Money movement (transfers, loans, currency
          exchange) is tracked separately and excluded from spending figures.
        </p>
      )}

      {/* -- KPIs ----------------------------------------------------------- */}
      <div className="kpi-grid">
        <Kpi
          label="Spent this month"
          value={formatMoney(current.consumption, currency)}
          comparison={comparisons.consumption}
          invert
          hint={`${current.transaction_count} transactions`}
        />
        <Kpi
          label="Income"
          value={formatMoney(current.income, currency)}
          comparison={comparisons.income}
        />
        <Kpi
          label="Net saved"
          value={formatMoney(current.net_consumption, currency)}
          comparison={comparisons.net}
          tone={current.net_consumption >= 0 ? 'pos' : 'neg'}
          hint={
            current.savings_rate !== null
              ? `${formatPercent(current.savings_rate, 0)} of income`
              : undefined
          }
        />
        <Kpi
          label="Average per day"
          value={formatMoney(outlook.daily_pace, currency)}
          hint={`over ${outlook.days_elapsed} days`}
        />
      </div>

      {/* -- Pace and projection -------------------------------------------- */}
      <section className="card mb-3">
        <h3 className="section-title">Where this month is heading</h3>
        <OutlookMeter outlook={outlook} currency={currency} />
      </section>

      {/* -- Insights ------------------------------------------------------- */}
      {data.insights?.length > 0 && (
        <section className="mb-3">
          <h3 className="section-title">What stands out</h3>
          <div className="insight-grid">
            {data.insights.map((insight) => (
              <InsightCard key={`${insight.title}-${insight.value}`} insight={insight} />
            ))}
          </div>
        </section>
      )}

      {/* -- Trend ---------------------------------------------------------- */}
      <section className="card mb-3">
        <div className="row-between">
          <h3 className="section-title" style={{ margin: 0 }}>
            Income and spending, month by month
          </h3>
          <small className="text-muted">hover a month for the detail</small>
        </div>
        <TrendChart data={monthly} currency={currency} />
      </section>

      {/* -- Categories ----------------------------------------------------- */}
      <section className="grid-2 mb-3">
        <div className="card">
          <h3 className="section-title">Where the money went</h3>
          <CategoryDonut data={consumptionCategories} currency={currency} />
        </div>
        <div className="card">
          <h3 className="section-title">
            Against last period
            {showMovement ? ' (including movement)' : ''}
          </h3>
          <CategoryBars
            current={showMovement ? data.all_categories : consumptionCategories}
            previous={data.previous_categories ?? []}
            currency={currency}
            limit={9}
            includeMoneyMovement={showMovement}
          />
          {movementCategories.length > 0 && (
            <label className="text-muted" style={{ fontSize: '0.8rem' }}>
              <input
                type="checkbox"
                checked={showMovement}
                onChange={(event) => setShowMovement(event.target.checked)}
              />{' '}
              include money movement
            </label>
          )}
        </div>
      </section>

      {/* -- Category trend ------------------------------------------------- */}
      <section className="card mb-3">
        <h3 className="section-title">Category mix over time</h3>
        <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '-0.35rem' }}>
          Is the total rising because everything rises, or because of one thing? Click a
          category to isolate it.
        </p>
        <CategoryTrendChart data={categoryTrend} currency={currency} />
      </section>

      {/* -- Behaviour ------------------------------------------------------ */}
      <section className="grid-2 mb-3">
        <div className="card">
          <h3 className="section-title">When you spend</h3>
          <WeekdayChart data={data.weekday} currency={currency} />
          <p className="text-muted" style={{ fontSize: '0.78rem' }}>
            Last 12 months of spending, money movement excluded.
          </p>
        </div>

        <div className="card">
          <h3 className="section-title">Committed costs</h3>
          {data.recurring?.length ? (
            <>
              <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '-0.35rem' }}>
                Categories that appear nearly every month with little variation — the
                first place to look when spending needs to come down.
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th className="numeric">Per month</th>
                    <th className="numeric">Range</th>
                    <th className="numeric">Variation</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recurring.slice(0, 8).map((row) => (
                    <tr key={row.category}>
                      <td>
                        {row.category}
                        <br />
                        <small className="text-muted">
                          {row.months_present}/{row.months_considered} months
                        </small>
                      </td>
                      <td className="numeric">{formatMoney(row.monthly_average, currency)}</td>
                      <td className="numeric text-muted">
                        {formatMoney(row.monthly_min, currency)} – {formatMoney(row.monthly_max, currency)}
                      </td>
                      <td className="numeric">
                        {row.variability_percent !== null
                          ? `±${formatPercent(row.variability_percent, 0)}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <EmptyState message="No repeating costs detected yet." />
          )}
        </div>
      </section>

      {/* -- Top descriptions ----------------------------------------------- */}
      <section className="card mb-3">
        <h3 className="section-title">Largest individual payees</h3>
        <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '-0.35rem' }}>
          Built from transaction descriptions over the last 12 months.
        </p>
        {data.top_descriptions?.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Description</th>
                <th className="numeric">Total</th>
                <th className="numeric">Times</th>
                <th className="numeric">Average</th>
                <th>Last</th>
              </tr>
            </thead>
            <tbody>
              {data.top_descriptions.map((row) => (
                <tr key={row.description}>
                  <td>{row.description}</td>
                  <td className="numeric">{formatMoney(row.total, currency)}</td>
                  <td className="numeric">{row.count}</td>
                  <td className="numeric">{formatMoney(row.average, currency)}</td>
                  <td className="text-muted">{row.last}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState message="No described transactions in this window." />
        )}
      </section>

      {/* -- Money movement ------------------------------------------------- */}
      {movement > 0 && (
        <section className="card mb-3">
          <h3 className="section-title">Money movement, kept separate</h3>
          <p className="text-muted" style={{ fontSize: '0.85rem', marginTop: '-0.35rem' }}>
            These outflows do not consume wealth — they move it to another account, to a
            lender, or into an asset. They are excluded from every spending figure above.
          </p>
          <div className="kpi-grid">
            <MiniStat label="This period" value={formatMoney(movement, currency)} />
            <MiniStat
              label="Share of all outflows"
              value={formatPercent(
                current.expenses ? (movement / current.expenses) * 100 : 0,
                0
              )}
            />
            <MiniStat
              label="Consumption"
              value={formatMoney(current.consumption, currency)}
            />
          </div>
          <CategoryBars
            current={movementCategories}
            previous={[]}
            currency={currency}
            limit={6}
            includeMoneyMovement
          />
        </section>
      )}

      <p className="text-muted" style={{ fontSize: '0.78rem' }}>
        Data from {data.data_range?.first} to {data.data_range?.last}, where transactions were
        recorded in {currency}. Amounts in other currencies are excluded rather than converted,
        because the stored exchange rates are single historical snapshots.
      </p>
    </div>
  )
}
