import { useMemo, useState } from 'react'

import { useOperations, useRunHistory, useRunOperation } from '../../hooks/useOps'
import { describeApiError } from '../../api'
import { OPERATION_SAFETY } from '../../constants'
import { formatDate } from '../../utils/format'
import { Alert, DataTable, EmptyState } from '../ui/Feedback'
import { SelectField, TextField } from '../ui/FormFields'

/** Map an operation's declared fields onto initial form values. */
function initialArguments(operation) {
  const values = {}
  operation.fields.forEach((field) => {
    if (field.type === 'boolean') values[field.name] = field.default ?? false
    else values[field.name] = field.default ?? ''
  })
  return values
}

function statusTone(status) {
  if (status === 'success') return 'pos'
  if (status === 'failed') return 'neg'
  return 'text-muted'
}

/**
 * Render one declared field as the right control.
 *
 * The backend owns the input schema (`fields`), so adding a new operation with new
 * options needs no frontend change.
 */
function OperationField({ field, value, onChange, disabled }) {
  if (field.type === 'boolean') {
    return (
      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(field.name, event.target.checked)}
          disabled={disabled}
        />
        <span>
          {field.label}
          {field.help_text && (
            <>
              <br />
              <small className="text-muted">{field.help_text}</small>
            </>
          )}
        </span>
      </label>
    )
  }

  if (field.type === 'select') {
    return (
      <SelectField
        label={field.label}
        name={field.name}
        value={value}
        onChange={(event) => onChange(field.name, event.target.value)}
        options={field.choices}
        placeholder="Default"
        hint={field.help_text}
      />
    )
  }

  return (
    <TextField
      label={field.label}
      name={field.name}
      type={field.type === 'integer' ? 'number' : 'text'}
      value={value}
      onChange={(event) => onChange(field.name, event.target.value)}
      hint={field.help_text}
      placeholder={field.default ?? ''}
      disabled={disabled}
    />
  )
}

function RunResult({ run }) {
  if (!run) return null

  const tone =
    run.status === 'failed' ? 'error' : run.status === 'skipped' ? 'info' : 'success'

  return (
    <div className="mt-3">
      <Alert variant={tone}>
        <strong>
          {run.operation} — {run.status}
        </strong>
        {run.duration_ms != null && <span className="text-muted"> ({run.duration_ms} ms)</span>}
        {run.output && <> — {run.output}</>}
        {run.error && <> — {run.error}</>}
      </Alert>

      {run.result && Object.keys(run.result).length > 0 && (
        <details className="card" style={{ padding: '1rem' }}>
          <summary style={{ cursor: 'pointer' }}>Result details</summary>
          <pre
            style={{
              marginTop: '0.75rem',
              maxHeight: '320px',
              overflow: 'auto',
              fontSize: '0.8rem',
              whiteSpace: 'pre-wrap',
            }}
          >
            {JSON.stringify(run.result, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}

/**
 * Maintenance console: pick an operation, fill in its declared options, run it,
 * then read the recorded result and the audit trail.
 */
export default function OperationsConsole() {
  const operations = useOperations()
  const runOperation = useRunOperation()
  const [selectedKey, setSelectedKey] = useState(null)
  const [values, setValues] = useState({})

  const selected = useMemo(
    () => operations.data?.find((operation) => operation.key === selectedKey) ?? null,
    [operations.data, selectedKey]
  )

  const select = (operation) => {
    setSelectedKey(operation.key)
    setValues(initialArguments(operation))
    runOperation.reset()
  }

  const setField = (name, value) => setValues((previous) => ({ ...previous, [name]: value }))

  const submit = (event) => {
    event.preventDefault()
    runOperation.mutate({ key: selected.key, args: values })
  }

  const grouped = useMemo(() => {
    const groups = {}
    ;(operations.data ?? []).forEach((operation) => {
      groups[operation.group] = groups[operation.group] ?? []
      groups[operation.group].push(operation)
    })
    return groups
  }, [operations.data])

  if (operations.isLoading) return <p className="text-muted">Loading operations…</p>
  if (operations.isError) return <Alert>{describeApiError(operations.error)}</Alert>

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
        <div>
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="mb-3">
              <h4 className="text-muted mb-1" style={{ textTransform: 'uppercase', fontSize: '0.8rem' }}>
                {group}
              </h4>
              {items.map((operation) => {
                const safety = OPERATION_SAFETY[operation.safety] ?? { label: operation.safety }
                const isSelected = operation.key === selectedKey
                return (
                  <button
                    key={operation.key}
                    type="button"
                    onClick={() => select(operation)}
                    className="card"
                    style={{
                      display: 'block',
                      width: '100%',
                      textAlign: 'left',
                      marginBottom: '0.5rem',
                      padding: '0.85rem 1rem',
                      cursor: 'pointer',
                      border: isSelected
                        ? '2px solid var(--ocean-blue)'
                        : '2px solid transparent',
                      opacity: operation.allowed ? 1 : 0.65,
                    }}
                  >
                    <div className="row-between">
                      <strong>{operation.label}</strong>
                      <span
                        className={operation.safety === 'read' ? 'text-muted' : operation.safety === 'mutate' ? 'text-accent' : 'neg'}
                        style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}
                      >
                        {safety.label}
                      </span>
                    </div>
                    <small className="text-muted">{operation.description}</small>
                  </button>
                )
              })}
            </div>
          ))}
        </div>

        <div>
          {!selected ? (
            <EmptyState message="Pick an operation on the left to see its options." />
          ) : (
            <div className="card">
              <h3 className="mb-1">{selected.label}</h3>
              <p className="text-muted mb-3">{selected.description}</p>

              {!selected.allowed && <Alert variant="info">{selected.blocked_reason}</Alert>}
              {runOperation.isError && <Alert>{describeApiError(runOperation.error)}</Alert>}

              <form onSubmit={submit}>
                {selected.fields.length === 0 && (
                  <p className="text-muted">This operation takes no options.</p>
                )}
                {selected.fields.map((field) => (
                  <OperationField
                    key={field.name}
                    field={field}
                    value={values[field.name]}
                    onChange={setField}
                    disabled={!selected.allowed || runOperation.isPending}
                  />
                ))}

                <button
                  type="submit"
                  className={`btn ${selected.safety === 'read' ? 'btn-secondary' : 'btn-primary'}`}
                  disabled={!selected.allowed || runOperation.isPending}
                >
                  {runOperation.isPending ? 'Running…' : `Run ${selected.label.toLowerCase()}`}
                </button>
              </form>

              <RunResult run={runOperation.data} />
            </div>
          )}
        </div>
      </div>

      <h3 className="mt-4 mb-2">Recent runs</h3>
      <RunHistory />
    </div>
  )
}

/** Audit trail of console actions. */
export function RunHistory() {
  const history = useRunHistory()

  if (history.isError) return <Alert>{describeApiError(history.error)}</Alert>
  if (!history.isLoading && (history.data ?? []).length === 0) {
    return <EmptyState message="No operations have been run yet." />
  }

  return (
    <DataTable
      columns={['When', 'Operation', 'Status', 'Operator', 'Duration', 'Output']}
      isLoading={history.isLoading}
    >
      {(history.data ?? []).map((run) => (
        <tr key={run.id}>
          <td>{formatDate(run.started_at)}</td>
          <td>{run.operation}</td>
          <td className={statusTone(run.status)}>{run.status}</td>
          <td>{run.triggered_by_username ?? '—'}</td>
          <td className="numeric">{run.duration_ms != null ? `${run.duration_ms} ms` : '—'}</td>
          <td>
            <span title={run.error || run.output}>
              {(run.error || run.output || '—').slice(0, 90)}
            </span>
          </td>
        </tr>
      ))}
    </DataTable>
  )
}
