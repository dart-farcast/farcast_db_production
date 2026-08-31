import React, { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'

/**
 * Maps each panel id → the store filter field to add the clicked value into.
 */
const PANEL_FIELD = {
  samples:    'indication',
  drugs:      'drug',
  assayTypes: 'assay',
  studies:    'study',
}

function StatPanel({ id, stats, onClose }) {
  const ref = useRef(null)
  const { setFilterAndSearch, filters } = useStore()

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  if (!stats) return null

  let title = ''
  let rows  = []

  if (id === 'samples') {
    title = 'Samples by Cancer Type'
    rows = Object.entries(stats.indications || {})
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ label: name, val: count, clickValue: name }))

  } else if (id === 'drugs') {
    title = 'Top Drugs'
    rows = (stats.top_drugs || []).map(d => ({ label: d, val: null, clickValue: d }))

  } else if (id === 'assayTypes') {
    title = 'Assay Types'
    rows = Object.entries(stats.assay_samples || {}).map(([name, count]) => ({
      label: name, val: count, clickValue: name,
    }))

  } else if (id === 'studies') {
    title = 'Studies'
    rows = (stats.study_list || []).map(s => ({ label: s, val: null, clickValue: s }))
  }

  const field       = PANEL_FIELD[id]
  const activeField = Array.isArray(filters[field]) ? filters[field] : []

  const handleRowClick = (clickValue) => {
    onClose()
    setFilterAndSearch(field, clickValue)
  }

  return (
    <div className="stat-panel" ref={ref}>
      <div className="sp-head">{title}</div>
      <div style={{ maxHeight: 300, overflowY: 'auto' }}>
        {rows.length === 0 && (
          <div className="sp-row">
            <span className="sp-label" style={{ color: 'var(--muted)' }}>No data</span>
          </div>
        )}
        {rows.map((r, i) => {
          const isActive = activeField.includes(r.clickValue)
          return (
            <div
              key={i}
              className={`sp-row clickable${isActive ? ' sp-active' : ''}`}
              onClick={() => handleRowClick(r.clickValue)}
              title={`Filter by "${r.clickValue}"`}
            >
              <span className="sp-label">{r.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {r.val !== null && <span className="sp-val">{r.val}</span>}
                {isActive
                  ? <span className="sp-check">✓</span>
                  : <span className="sp-plus">+</span>}
              </div>
            </div>
          )
        })}
      </div>
      <div className="sp-footer">Click a row to filter &amp; search</div>
    </div>
  )
}

export default function Header() {
  const { user, currentView, setCurrentView, logout } = useStore()
  const stats = useStore(s => s.stats)
  const [openPanel, setOpenPanel] = useState(null)

  const toggle = (id) => setOpenPanel(p => (p === id ? null : id))
  const assayCount = Object.keys(stats?.assay_samples || {}).length

  const badges = stats ? [
    { id: 'samples',    num: stats.samples ?? '—',  label: 'Samples'     },
    { id: 'drugs',      num: stats.drugs   ?? '—',  label: 'Drugs'       },
    { id: 'assayTypes', num: assayCount,             label: 'Assay Types' },
    { id: 'studies',    num: stats.studies ?? '—',  label: 'Studies'     },
  ] : []

  return (
    <header className="main-header">
      <div className="logo" onClick={() => setCurrentView('database')} style={{ cursor: 'pointer' }}>
        <FarcastLogo height={34} showSub={true} />
      </div>

      <div className="hstats" style={{ position: 'relative' }}>
        {badges.map(({ id, num, label }) => (
          <button
            key={id}
            className={`hstat${openPanel === id ? ' active' : ''}`}
            onClick={() => toggle(id)}
          >
            <b>{num}</b> {label}
          </button>
        ))}
        {openPanel && (
          <StatPanel
            id={openPanel}
            stats={stats}
            onClose={() => setOpenPanel(null)}
          />
        )}
      </div>

      {user && (
        <div className="header-user-actions">
          {user.role === 'admin' && (
            <button 
              className={`header-nav-btn ${currentView === 'admin' ? 'active' : ''}`}
              onClick={() => setCurrentView(currentView === 'admin' ? 'database' : 'admin')}
            >
              {currentView === 'admin' ? '📊 Database Search' : '🛡️ Admin Console'}
            </button>
          )}

          <div className="user-profile-badge">
            <span className="user-avatar">{user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}</span>
            <div className="user-info">
              <span className="user-name">{user.full_name || user.email.split('@')[0]}</span>
              <span className="user-role">{user.role === 'admin' ? 'Admin' : 'Whitelisted User'}</span>
            </div>
          </div>

          <button className="header-logout-btn" onClick={logout} title="Sign Out">
            🚪 Sign Out
          </button>
        </div>
      )}
    </header>
  )
}
