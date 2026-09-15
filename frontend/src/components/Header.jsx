import React, { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'
import AssayDetailsModal from './AssayDetailsModal'

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
    title = 'Study Types'
    rows = (stats.study_list || []).map(s => ({ label: s, val: null, clickValue: s }))
  } else if (id === 'qualification') {
    title = 'Qualification Breakdown'
    rows = [
      { label: 'Qualified Samples', val: stats.qualified_samples ?? 0, clickValue: null },
      { label: 'Disqualified Samples', val: stats.disqualified_samples ?? 0, clickValue: null },
      { label: 'Internal R&D Qualified', val: `${stats.internal_rd_qualified ?? 0} / ${stats.internal_rd_total ?? 0}`, clickValue: 'R&D' },
      { label: 'BioPharma Qualified', val: `${stats.biopharma_qualified ?? 0} / ${stats.biopharma_total ?? 0}`, clickValue: 'Biopharma' },
    ]
  }

  const field       = PANEL_FIELD[id]
  const activeField = Array.isArray(filters[field]) ? filters[field] : []

  const handleRowClick = (clickValue) => {
    if (!clickValue) return
    onClose()
    setFilterAndSearch(field || 'study', clickValue)
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
          const isActive = r.clickValue && activeField.includes(r.clickValue)
          const isClickable = Boolean(r.clickValue)
          return (
            <div
              key={i}
              className={`sp-row${isClickable ? ' clickable' : ''}${isActive ? ' sp-active' : ''}`}
              onClick={() => isClickable && handleRowClick(r.clickValue)}
              title={isClickable ? `Filter by "${r.clickValue}"` : ''}
            >
              <span className="sp-label">{r.label}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {r.val !== null && <span className="sp-val">{r.val}</span>}
                {isClickable && (isActive
                  ? <span className="sp-check">✓</span>
                  : <span className="sp-plus">+</span>)}
              </div>
            </div>
          )
        })}
      </div>
      <div className="sp-footer">{id === 'qualification' ? 'Sample Qualification Overview' : 'Click a row to filter & search'}</div>
    </div>
  )
}

export default function Header() {
  const { user, currentView, setCurrentView, logout } = useStore()
  const stats = useStore(s => s.stats)
  const [openPanel, setOpenPanel] = useState(null)
  const [showAssayGuide, setShowAssayGuide] = useState(false)

  const toggle = (id) => setOpenPanel(p => (p === id ? null : id))
  const assayCount = Object.keys(stats?.assay_samples || {}).length

  const badges = stats ? [
    { id: 'samples',       num: stats.samples ?? '—',            label: 'Samples'     },
    { id: 'qualification', num: stats.qualified_samples ?? '—',  label: 'Qualified'   },
    { id: 'drugs',         num: stats.drugs   ?? '—',            label: 'Drugs'       },
    { id: 'assayTypes',    num: assayCount,                       label: 'Assay Types' },
    { id: 'studies',       num: stats.studies ?? '—',            label: 'Study Types' },
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
          <button 
            className="header-nav-btn assay-guide-btn" 
            onClick={() => setShowAssayGuide(true)}
            title="View Assay Details & Readout Descriptions"
          >
            🔬 Assay Details
          </button>

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

      {/* Assay Details Modal */}
      <AssayDetailsModal isOpen={showAssayGuide} onClose={() => setShowAssayGuide(false)} />
    </header>
  )
}

