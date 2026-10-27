import React, { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'
import AssayDetailsModal from './AssayDetailsModal'
import SecurityModal from './SecurityModal'

/**
 * Maps each panel id → the store filter field to add the clicked value into.
 */
const PANEL_FIELD = {
  samples: 'indication',
  drugs: 'drug',
  assayTypes: 'assay',
  studies: 'study',
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
  let rows = []

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

  const field = PANEL_FIELD[id]
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
  const {
    user, currentView, setCurrentView, logout, preRebootStats,
    unreadNotificationsCount, fetchNotifications
  } = useStore()
  const stats = useStore(s => s.stats)
  const [openPanel, setOpenPanel] = useState(null)
  const [showAssayGuide, setShowAssayGuide] = useState(false)
  const [showSecurityModal, setShowSecurityModal] = useState(false)
  const [securityInitialTab, setSecurityInitialTab] = useState('notifications')

  useEffect(() => {
    if (user) {
      fetchNotifications()
      const interval = setInterval(fetchNotifications, 45000)
      return () => clearInterval(interval)
    }
  }, [user])

  const toggle = (id) => setOpenPanel(p => (p === id ? null : id))
  const assayCount = Object.keys(stats?.assay_samples || {}).length

  const badges = stats ? [
    { id: 'samples', num: stats.samples ?? '—', label: 'Tumors Profiled' },
    { id: 'qualification', num: stats.qualified_samples ?? '—', label: 'Qualified' },
    { id: 'drugs', num: stats.drugs ?? '—', label: 'Drugs' },
    { id: 'assayTypes', num: assayCount, label: 'Assay Types' },
    { id: 'studies', num: stats.studies ?? '—', label: 'Study Types' },
  ] : []

  const openSecurity = (tab = 'notifications') => {
    setSecurityInitialTab(tab)
    setShowSecurityModal(true)
  }

  return (
    <header className="main-header">
      {/* Left Branding & Mode Indicator */}
      <div className="header-left-group">
        <div className="logo logo-clickable" onClick={() => setCurrentView('hub')} title="Return to Portal Hub">
          <FarcastLogo height={34} showSub={true} />
        </div>

        {currentView === 'database' && (
          <span className="era-badge-indicator post">
            Response Cohort
          </span>
        )}

        {currentView === 'pre_reboot' && (
          <span className="era-badge-indicator pre">
            Discovery Cohort
          </span>
        )}
      </div>

      {/* Center Stats */}
      {currentView === 'database' && (
        <div className="hstats" style={{ position: 'relative' }}>
          {badges.map(({ id, num, label, shortLabel }) => (
            <button
              key={id}
              className={`hstat${openPanel === id ? ' active' : ''}`}
              onClick={() => toggle(id)}
              title={`View ${label} breakdown`}
            >
              <b>{num}</b> <span className="hstat-full">{label}</span><span className="hstat-short">{shortLabel || label}</span>
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
      )}

      {currentView === 'pre_reboot' && preRebootStats && (
        <div className="hstats pre-reboot-hstats">
          <div className="hstat static-badge">
            <b>{preRebootStats.total_samples?.toLocaleString() || '22,094'}</b> Tumors
          </div>
          <div className="hstat static-badge">
            <b>{preRebootStats.with_block_count?.toLocaleString() || '2,773'}</b> Blocks
          </div>
          <div className="hstat static-badge">
            <b>{preRebootStats.scored_count?.toLocaleString() || '951'}</b> Scored
          </div>
        </div>
      )}

      {/* Right User Actions */}
      {user && (
        <div className="header-user-actions">
          {currentView === 'database' && (
            <button
              className="header-nav-btn assay-guide-btn"
              onClick={() => setShowAssayGuide(true)}
              title="View Assay Details & Readout Descriptions"
            >
              <span className="btn-icon">🔬</span>
              <span className="nav-btn-text">Assay Details</span>
            </button>
          )}

          {user.role === 'admin' && (
            <button
              className={`header-nav-btn admin-nav-btn ${currentView === 'admin' ? 'active' : ''}`}
              onClick={() => setCurrentView(currentView === 'admin' ? 'database' : 'admin')}
              title={currentView === 'admin' ? 'Switch to Database Search Workspace' : 'Open Admin Management Console'}
            >
              <span className="btn-icon">{currentView === 'admin' ? '📊' : '🛡️'}</span>
              <span className="nav-btn-text">{currentView === 'admin' ? 'Database' : 'Admin'}</span>
            </button>
          )}

          {/* Security Notifications Bell Button */}
          <button
            className="header-bell-btn"
            onClick={() => openSecurity('notifications')}
            title="View Security Notifications & Alerts"
          >
            <span className="bell-icon">🔔</span>
            {unreadNotificationsCount > 0 && (
              <span className="bell-badge-count">{unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}</span>
            )}
          </button>

          {/* User Profile Badge (Clickable to open Security & Account) */}
          <div
            className="user-profile-badge interactive"
            onClick={() => openSecurity('password')}
            title="Click to view Account Settings, Security & Login History"
          >
            <span className="user-avatar">{user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}</span>
            <div className="user-info">
              <span className="user-name">{user.full_name || user.email.split('@')[0]}</span>
              <span className="user-role">{user.role === 'admin' ? 'Admin' : (user.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : 'User')}</span>
            </div>
            <span className="avatar-chevron">▾</span>
          </div>

          <button className="header-logout-btn" onClick={logout} title="Sign Out">
            <span>🚪</span>
            <span className="logout-text">Sign Out</span>
          </button>
        </div>
      )}

      {/* Assay Details Modal */}
      <AssayDetailsModal isOpen={showAssayGuide} onClose={() => setShowAssayGuide(false)} />

      {/* Security & Account Settings Modal */}
      <SecurityModal
        isOpen={showSecurityModal}
        onClose={() => setShowSecurityModal(false)}
        initialTab={securityInitialTab}
      />
    </header>
  )
}


