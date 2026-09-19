import { useEffect, useId, useMemo, useRef, useState } from 'react'

/**
 * Description input with a real suggestion list.
 *
 * A native `<datalist>` was tried first and rejected: browsers render its options
 * inconsistently (Chrome showed the option label — a usage count — instead of the
 * value, so the user saw "365× used" rather than "Restaurante"), and it cannot be
 * styled into something usable for finance work. This is a plain listbox, so the
 * suggestion text is always the description the user typed before.
 *
 * Keyboard: ArrowDown/ArrowUp move, Enter accepts, Escape closes, Tab accepts the
 * highlighted suggestion. Blur closes the list without stealing the click.
 *
 * @param {Object} props
 * @param {string} props.value
 * @param {(value: string) => void} props.onChange
 * @param {Array<{description: string, uses: number}>} props.suggestions
 * @param {string} [props.id]
 * @param {string} [props.placeholder]
 * @param {boolean} [props.autoFocus]
 * @param {boolean} [props.isLoading]
 * @param {(value: string) => void} [props.onEnter] called when Enter is pressed with no highlight
 */
export default function DescriptionInput({
  value,
  onChange,
  suggestions = [],
  id,
  placeholder,
  autoFocus = false,
  isLoading = false,
  onEnter,
}) {
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const containerRef = useRef(null)
  const generatedId = useId()
  const inputId = id ?? `description-${generatedId}`
  const listId = `${inputId}-list`

  const query = (value ?? '').trim().toLocaleLowerCase()

  /**
   * Filter locally as the user types.
   *
   * Two rules make this feel right in practice:
   *  - the **shortest** matching word helps most, so typing `s` surfaces `Snacks`
   *    before a long description that happens to contain an "s";
   *  - a description the user is currently typing (an exact prefix) ranks first.
   */
  const matches = useMemo(() => {
    const pool = suggestions.filter((item) => item.description)
    const filtered = query
      ? pool.filter((item) => item.description.toLocaleLowerCase().includes(query))
      : pool

    return [...filtered]
      .sort((a, b) => {
        if (query) {
          const aStarts = a.description.toLocaleLowerCase().startsWith(query) ? 0 : 1
          const bStarts = b.description.toLocaleLowerCase().startsWith(query) ? 0 : 1
          if (aStarts !== bStarts) return aStarts - bStarts
          if (a.description.length !== b.description.length) {
            return a.description.length - b.description.length
          }
        }
        return (b.uses ?? 0) - (a.uses ?? 0)
      })
      .slice(0, 12)
  }, [suggestions, query])

  // Reset the highlight when the list changes underneath it.
  useEffect(() => {
    setHighlight(0)
  }, [query, suggestions])

  // Close when clicking anywhere else.
  useEffect(() => {
    if (!open) return undefined
    const onDocumentClick = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocumentClick)
    return () => document.removeEventListener('mousedown', onDocumentClick)
  }, [open])

  const choose = (description) => {
    onChange(description)
    setOpen(false)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setHighlight((current) => Math.min(current + 1, matches.length - 1))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlight((current) => Math.max(current - 1, 0))
      return
    }
    if (event.key === 'Escape') {
      setOpen(false)
      return
    }
    if (event.key === 'Enter' && open && matches.length > 0) {
      // Accept the highlighted suggestion instead of submitting the form.
      event.preventDefault()
      choose(matches[highlight]?.description ?? matches[0].description)
      return
    }
    if (event.key === 'Tab' && open && matches.length > 0) {
      choose(matches[highlight]?.description ?? matches[0].description)
      return
    }
    if (event.key === 'Enter' && onEnter) {
      // Let the parent decide (usually: submit the form).
      onEnter(value)
    }
  }

  const showList = open && matches.length > 0

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <input
        className="form-input"
        id={inputId}
        name="description"
        type="text"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        value={value ?? ''}
        onChange={(event) => {
          onChange(event.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
      />

      {showList && (
        <ul className="autocomplete" id={listId} role="listbox">
          {matches.map((item, index) => (
            <li
              key={item.description}
              role="option"
              aria-selected={index === highlight}
              className={`autocomplete__option${index === highlight ? ' is-highlighted' : ''}`}
              onMouseEnter={() => setHighlight(index)}
              onMouseDown={(event) => {
                // mousedown, not click: blur would close the list first.
                event.preventDefault()
                choose(item.description)
              }}
            >
              <span className="autocomplete__text">{item.description}</span>
              <span className="autocomplete__meta">{item.uses}×</span>
            </li>
          ))}
        </ul>
      )}

      <small className="text-muted">
        {isLoading && suggestions.length === 0
          ? 'Loading suggestions…'
          : suggestions.length > 0
            ? `Start typing to reuse one of your ${suggestions.length} descriptions`
            : 'Suggestions appear once you have logged a few descriptions'}
      </small>
    </div>
  )
}
