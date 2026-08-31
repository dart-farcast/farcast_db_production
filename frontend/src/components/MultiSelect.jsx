import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useStore } from '../store'

/**
 * MultiSelect — tag-chip input with debounced autocomplete dropdown.
 * Props:
 *   field        — autocomplete field key (drug, indication, study, etc.)
 *   label        — display label
 *   placeholder  — input placeholder
 *   selected     — string[] of selected values
 *   onChange     — (newArray) => void
 */
export default function MultiSelect({ field, label, placeholder, selected = [], onChange }) {
  const { authFetch }           = useStore()
  const [query, setQuery]       = useState('')
  const [opts, setOpts]         = useState([])
  const [hiIdx, setHiIdx]       = useState(-1)
  const [focused, setFocused]   = useState(false)
  const inputRef = useRef(null)
  const timerRef = useRef(null)

  const fetchOpts = useCallback((q) => {
    authFetch(`/api/autocomplete?field=${field}&q=${encodeURIComponent(q || '')}`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setOpts(data.filter(v => !selected.includes(v)))
        } else {
          setOpts([])
        }
        setHiIdx(-1)
      })
      .catch(() => setOpts([]))
  }, [field, selected, authFetch])

  const handleInput = (e) => {
    const q = e.target.value
    setQuery(q)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => fetchOpts(q), 200)
  }

  const handleFocus = () => {
    setFocused(true)
    fetchOpts(query)
  }

  const addValue = (val) => {
    if (val && !selected.includes(val)) {
      onChange([...selected, val])
    }
    setQuery('')
    setOpts([])
    inputRef.current?.focus()
  }

  const removeValue = (val) => {
    onChange(selected.filter(v => v !== val))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHiIdx(i => Math.min(i + 1, opts.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHiIdx(i => Math.max(i - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (hiIdx >= 0 && opts[hiIdx]) addValue(opts[hiIdx])
      else if (query.trim()) addValue(query.trim())
    } else if (e.key === 'Backspace' && !query && selected.length) {
      removeValue(selected[selected.length - 1])
    } else if (e.key === 'Escape') {
      setOpts([])
    }
  }

  const open = focused && (opts.length > 0 || (query.length > 0 && opts.length === 0))

  return (
    <div className="ff">
      <label>{label}</label>
      <div className="ms-wrap">
        <div
          className={`ms-box${focused ? ' focused' : ''}`}
          onClick={() => inputRef.current?.focus()}
        >
          {selected.map(v => (
            <span className="ms-chip" key={v}>
              {v}
              <button type="button" onClick={e => { e.stopPropagation(); removeValue(v) }}>×</button>
            </span>
          ))}
          <input
            ref={inputRef}
            className="ms-input"
            placeholder={selected.length === 0 ? placeholder : ''}
            value={query}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onFocus={handleFocus}
            onBlur={() => setTimeout(() => setFocused(false), 200)}
          />
        </div>
        {open && (
          <div className="ms-dropdown">
            {opts.length === 0
              ? <div className="ms-empty">No matches</div>
              : opts.map((o, i) => (
                  <div
                    key={o}
                    className={`ms-opt${i === hiIdx ? ' hi' : ''}`}
                    onMouseDown={() => addValue(o)}
                  >
                    {o}
                  </div>
                ))
            }
          </div>
        )}
      </div>
    </div>
  )
}
