/** Shared presentational components: alert, stat card, empty state, table shell. */

/**
 * @param {Object} props
 * @param {'error'|'success'|'info'} [props.variant]
 * @param {React.ReactNode} props.children
 */
export function Alert({ variant = 'error', children }) {
  if (!children) return null
  return <div className={`alert alert-${variant}`}>{children}</div>
}

/**
 * @param {Object} props
 * @param {string} props.label
 * @param {React.ReactNode} props.value
 * @param {'pos'|'neg'|undefined} [props.tone]
 * @param {string} [props.hint]
 */
export function StatCard({ label, value, tone, hint }) {
  return (
    <div className="stat-card">
      <div className="stat-card__label">{label}</div>
      <div className={`stat-card__value ${tone ?? ''}`}>{value}</div>
      {hint && <small className="text-muted">{hint}</small>}
    </div>
  )
}

/**
 * @param {Object} props
 * @param {string} props.message
 * @param {React.ReactNode} [props.action]
 */
export function EmptyState({ message, action }) {
  return (
    <div className="text-center text-muted" style={{ padding: '2rem 1rem' }}>
      <p className="mb-2">{message}</p>
      {action}
    </div>
  )
}

/**
 * @param {Object} props
 * @param {string[]} props.columns
 * @param {React.ReactNode} props.children
 * @param {boolean} [props.isLoading]
 * @param {number} [props.colSpan]
 */
export function DataTable({ columns, children, isLoading, colSpan }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td colSpan={colSpan ?? columns.length} className="text-center text-muted">
                Loading…
              </td>
            </tr>
          ) : (
            children
          )}
        </tbody>
      </table>
    </div>
  )
}
