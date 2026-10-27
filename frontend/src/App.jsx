import React, { useEffect } from 'react'
import { useStore } from './store'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ResultsTable from './components/ResultsTable'
import SignPage from './components/SignPage'
import AdminPage from './components/AdminPage'
import LandingHub from './components/LandingHub'
import PreRebootExplorer from './components/PreRebootExplorer'

export default function App() {
  const { 
    token, user, currentView, setCurrentView, filters, runSearch, 
    setStats, setAssayTypes, loadPreRebootStats, authFetch, refreshUser 
  } = useStore()

  const total = useStore(s => s.total)

  // Load stats + assay types + pre-reboot stats + refresh user profile
  useEffect(() => {
    if (token) {
      refreshUser()
    }
    if (token && user?.is_whitelisted) {
      authFetch('/api/stats')
        .then(r => r.json())
        .then(setStats)
        .catch(() => {})

      authFetch('/api/assay_types')
        .then(r => r.json())
        .then(setAssayTypes)
        .catch(() => {})

      // Pre-reboot stats
      loadPreRebootStats()
    }
  }, [token])

  // Unauthenticated or unwhitelisted -> Render Sign / Login Page
  if (!token || currentView === 'login' || (user && !user.is_whitelisted)) {
    return <SignPage />
  }

  // Active filter tag pills for context bar (Response Cohort)
  const activeTags = []
  const add = (label, vals) => vals?.forEach(v => activeTags.push({ label, val: v }))
  add('Drug',       filters.drug)
  add('Arm',        filters.arm)
  add('Indication', filters.indication)
  add('Site',       filters.tumor_site)
  add('Study Type', filters.study)
  add('Study Code', filters.project)

  add('Assay',      filters.assay)
  if (filters.sample) activeTags.push({ label: 'Sample', val: filters.sample })
  if (filters.strict_drug && filters.drug?.length > 0) {
    activeTags.push({ label: 'Matched Control', val: 'Selected Drug(s) + Matched Control Only' })
  }

  return (
    <div className="app-layout">
      <Header />
      
      {currentView === 'hub' ? (
        <LandingHub />
      ) : currentView === 'pre_reboot' ? (
        <PreRebootExplorer />
      ) : currentView === 'admin' ? (
        <AdminPage />
      ) : (
        <div className="body-layout">
          <Sidebar onSearch={runSearch} />
          <main>
            {/* Detail intro banner for Response Cohort */}
            <div className="detail-intro-banner response">
              <div className="banner-text">
                <strong className="banner-title">Response Cohort:</strong>
                Each live tumor is perturbed with several treatments at once, capturing immune activity and cytotoxic response for every arm. A patient receives one treatment; these tumors show what the alternatives would have done.
              </div>
              <button 
                className="btn-back-hub" 
                onClick={() => setCurrentView('hub')}
                title="Return to Portal Hub"
              >
                ← Back to Hub
              </button>
            </div>

            {/* Context bar */}
            <div className="ctx-bar">
              {activeTags.length === 0
                ? <span style={{ color: 'var(--muted)', fontSize: 11 }}>No filters active — showing all</span>
                : activeTags.map((t, i) => (
                    <span className="ctx-tag" key={i}>
                      <span className="label">{t.label}</span>
                      <span className="val">{t.val}</span>
                    </span>
                  ))}
              {total > 0 && (
                <span className="res-count">
                  <b>{total}</b> result{total !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            <ResultsTable />
          </main>
        </div>
      )}
    </div>
  )
}
