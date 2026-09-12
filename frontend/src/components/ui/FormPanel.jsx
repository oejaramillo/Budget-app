/**
 * Collapsible section used to show/hide a resource form above its table.
 *
 * @param {Object} props
 * @param {string} props.title
 * @param {boolean} props.isOpen
 * @param {() => void} props.onToggle
 * @param {React.ReactNode} props.children
 * @param {string} [props.openLabel]
 * @param {string} [props.closeLabel]
 */
export default function FormPanel({
  title,
  isOpen,
  onToggle,
  children,
  openLabel = 'Add new',
  closeLabel = 'Hide form',
}) {
  return (
    <div>
      <div className="page-header">
        <h2 style={{ fontSize: '1.25rem', margin: 0 }}>{title}</h2>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onToggle}>
          {isOpen ? closeLabel : openLabel}
        </button>
      </div>
      {isOpen && <div className="mb-3">{children}</div>}
    </div>
  )
}
