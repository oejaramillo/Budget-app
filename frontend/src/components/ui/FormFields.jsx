/**
 * Shared form primitives.
 *
 * Kept deliberately small: a label, a control, an optional hint and an error slot.
 * That is enough for every form in the app without pulling in a form library.
 */

/**
 * @param {Object} props
 * @param {string} props.label
 * @param {string} [props.htmlFor]
 * @param {string} [props.error]
 * @param {string} [props.hint]
 * @param {React.ReactNode} props.children
 */
export function Field({ label, htmlFor, error, hint, children }) {
  return (
    <div className="form-group">
      <label className="form-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && !error && <small className="text-muted">{hint}</small>}
      {error && (
        <small style={{ color: 'var(--alert-red)', display: 'block' }}>{error}</small>
      )}
    </div>
  )
}

/**
 * @param {Object} props
 * @param {string} props.label
 * @param {string} props.name
 * @param {string} [props.type]
 * @param {string|number} props.value
 * @param {(event: any) => void} props.onChange
 * @param {string} [props.error]
 * @param {string} [props.hint]
 * @param {string} [props.step]
 * @param {boolean} [props.required]
 * @param {boolean} [props.disabled]
 * @param {string} [props.placeholder]
 */
export function TextField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  error,
  hint,
  step,
  required = false,
  disabled = false,
  placeholder,
}) {
  return (
    <Field label={label} htmlFor={name} error={error} hint={hint}>
      <input
        className="form-input"
        id={name}
        name={name}
        type={type}
        step={step}
        value={value ?? ''}
        onChange={onChange}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
      />
    </Field>
  )
}

/**
 * @param {Object} props
 * @param {string} props.label
 * @param {string} props.name
 * @param {string|number} props.value
 * @param {(event: any) => void} props.onChange
 * @param {Array<{value: string|number, label: string}>} props.options
 * @param {string} [props.error]
 * @param {string} [props.hint]
 * @param {string} [props.placeholder]
 * @param {boolean} [props.required]
 */
export function SelectField({
  label,
  name,
  value,
  onChange,
  options,
  error,
  hint,
  placeholder,
  required = false,
}) {
  return (
    <Field label={label} htmlFor={name} error={error} hint={hint}>
      <select
        className="form-input"
        id={name}
        name={name}
        value={value ?? ''}
        onChange={onChange}
        required={required}
        aria-invalid={Boolean(error)}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  )
}

/**
 * @param {Object} props
 * @param {string} props.label
 * @param {string} props.name
 * @param {string} props.value
 * @param {(event: any) => void} props.onChange
 * @param {string} [props.error]
 * @param {number} [props.rows]
 */
export function TextAreaField({ label, name, value, onChange, error, rows = 3 }) {
  return (
    <Field label={label} htmlFor={name} error={error}>
      <textarea
        className="form-input"
        id={name}
        name={name}
        rows={rows}
        value={value ?? ''}
        onChange={onChange}
      />
    </Field>
  )
}
