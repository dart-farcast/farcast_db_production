import React, { useState, useEffect } from 'react'
import { useStore } from '../store'

export default function AdminPage() {
  const { authFetch, setCurrentView, updateUser, user: currentUser, setStats } = useStore()
  const [activeTab, setActiveTab] = useState('users') // 'users' | 'whitelist' | 'audit'

  // Data state
  const [whitelist, setWhitelist] = useState([])
  const [users, setUsers] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [availableStudies, setAvailableStudies] = useState([])

  // Database Sync state
  const [syncingDb, setSyncingDb] = useState(false)

  // Form states
  const [newPattern, setNewPattern] = useState('')
  const [newNotes, setNewNotes] = useState('')

  // Search & Filter state for user table
  const [userSearch, setUserSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all') // 'all' | 'pending' | 'approved' | 'scoped'

  // Modal State for Study & Sample Permissions
  const [editingUser, setEditingUser] = useState(null)
  const [selectedStudies, setSelectedStudies] = useState([])
  const [isUnrestrictedStudies, setIsUnrestrictedStudies] = useState(true)
  const [isUnrestrictedSamples, setIsUnrestrictedSamples] = useState(true)
  const [sampleInputText, setSampleInputText] = useState('')
  const [canDownloadAccess, setCanDownloadAccess] = useState(false)

  // General UI state
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const handleSyncDatabase = async () => {
    setSyncingDb(true)
    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch('/api/admin/sync_database', {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.error || data.detail || 'Failed to synchronize database.')
      
      if (data.stats && setStats) {
        setStats(data.stats)
      }
      setMsg({ 
        type: 'success', 
        text: `Database cache synchronized successfully from Supabase! (${data.meta_len || 0} Metadata Samples, ${data.overlay_len || 0} Overlay Rows, ${data.stats?.drugs || 0} Unique Drugs).` 
      })
      loadData()
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to synchronize database.' })
    } finally {
      setSyncingDb(false)
    }
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [wlRes, userRes, auditRes, studyRes] = await Promise.all([
        authFetch('/api/admin/whitelist'),
        authFetch('/api/admin/users'),
        authFetch('/api/admin/audit_logs'),
        authFetch('/api/admin/available_studies'),
      ])
      const wlData = await wlRes.json()
      const userData = await userRes.json()
      const auditData = await auditRes.json()
      const studyData = await studyRes.json()

      if (wlData?.whitelist) setWhitelist(wlData.whitelist)
      else if (Array.isArray(wlData)) setWhitelist(wlData)

      if (userData?.users) setUsers(userData.users)
      else if (Array.isArray(userData)) setUsers(userData)

      if (auditData?.logs) setAuditLogs(auditData.logs)
      else if (Array.isArray(auditData)) setAuditLogs(auditData)

      if (studyData?.studies) setAvailableStudies(studyData.studies)
      else if (Array.isArray(studyData)) setAvailableStudies(studyData)

    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to load administration data.' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleAddWhitelist = async (e) => {
    e.preventDefault()
    if (!newPattern.trim()) return
    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch('/api/admin/whitelist', {
        method: 'POST',
        body: JSON.stringify({ pattern: newPattern.trim(), notes: newNotes.trim() }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to add whitelist.')
      
      setMsg({ type: 'success', text: data.message })
      setNewPattern('')
      setNewNotes('')
      loadData()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
  }

  const handleRemoveWhitelist = async (pattern) => {
    if (!confirm(`Are you sure you want to revoke '${pattern}' from the whitelist?`)) return
    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch(`/api/admin/whitelist/${encodeURIComponent(pattern)}`, {
        method: 'DELETE',
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to remove whitelist.')
      setMsg({ type: 'success', text: data.message })
      loadData()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
  }

  const handleUserUpdate = async (userId, updatePayload) => {
    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        body: JSON.stringify(updatePayload),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to update user.')
      setMsg({ type: 'success', text: data.message })
      
      // If self updated, sync current user state
      if (currentUser && currentUser.id === userId) {
        updateUser(updatePayload)
      }

      loadData()
      return true
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
      return false
    }
  }

  const handleDeleteUser = async (userId, userEmail) => {
    if (!confirm(`Are you sure you want to permanently delete user account '${userEmail}'? This action cannot be undone.`)) return
    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to delete user account.')
      setMsg({ type: 'success', text: data.message })
      loadData()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
  }

  // Open modal for editing study & sample access
  const openPermissionsModal = (user) => {
    setEditingUser(user)
    setCanDownloadAccess(Boolean(user.can_download))
    if (user.allowed_studies === '*' || !Array.isArray(user.allowed_studies)) {
      setIsUnrestrictedStudies(true)
      setSelectedStudies(availableStudies)
    } else {
      setIsUnrestrictedStudies(false)
      setSelectedStudies(user.allowed_studies)
    }

    if (user.allowed_samples === '*' || !Array.isArray(user.allowed_samples)) {
      setIsUnrestrictedSamples(true)
      setSampleInputText('')
    } else {
      setIsUnrestrictedSamples(false)
      setSampleInputText(user.allowed_samples.join(', '))
    }
  }

  const toggleStudySelection = (studyName) => {
    setSelectedStudies(prev => 
      prev.includes(studyName) ? prev.filter(s => s !== studyName) : [...prev, studyName]
    )
  }

  const handleSavePermissions = async () => {
    if (!editingUser) return

    let finalSamples = '*'
    if (!isUnrestrictedSamples) {
      const parsed = sampleInputText
        .split(/[\s,]+/)
        .map(s => s.trim().toUpperCase())
        .filter(Boolean)
      finalSamples = Array.from(new Set(parsed))
      if (finalSamples.length === 0) {
        setMsg({ type: 'error', text: 'Please specify at least one valid Sample ID or select Unrestricted Samples.' })
        return
      }
    }

    let finalStudies = '*'
    if (!isUnrestrictedStudies) {
      if (selectedStudies.length === 0) {
        setMsg({ type: 'error', text: 'Please select at least one study or select Unrestricted Studies.' })
        return
      }
      finalStudies = selectedStudies
    }

    const payload = {
      allowed_studies: finalStudies,
      allowed_samples: finalSamples,
      can_download: Boolean(canDownloadAccess)
    }

    const success = await handleUserUpdate(editingUser.id, payload)
    if (success) {
      setEditingUser(null)
    }
  }

  // Filtered users list
  const filteredUsers = users.filter(u => {
    const q = userSearch.toLowerCase()
    const matchesSearch = !q || (
      u.email.toLowerCase().includes(q) ||
      (u.full_name && u.full_name.toLowerCase().includes(q))
    )
    const matchesRole = roleFilter === 'all' || u.role === roleFilter
    const matchesStatus = 
      statusFilter === 'all' ? true :
      statusFilter === 'pending' ? !u.is_whitelisted :
      statusFilter === 'approved' ? u.is_whitelisted :
      statusFilter === 'study_scoped' ? (u.allowed_studies !== '*' && Array.isArray(u.allowed_studies)) :
      statusFilter === 'sample_scoped' ? (u.allowed_samples !== '*' && Array.isArray(u.allowed_samples)) : true

    return matchesSearch && matchesRole && matchesStatus
  })

  // Metrics
  const pendingCount = users.filter(u => !u.is_whitelisted).length
  const adminCount = users.filter(u => u.role === 'role' || u.role === 'admin').length
  const studyScopedCount = users.filter(u => u.allowed_studies !== '*' && Array.isArray(u.allowed_studies)).length
  const sampleScopedCount = users.filter(u => u.allowed_samples !== '*' && Array.isArray(u.allowed_samples)).length

  return (
    <div className="admin-container">
      {/* Hero Executive Header */}
      <div className="admin-hero-banner">
        <div className="admin-hero-title">
          <div className="admin-hero-badge">
            <span className="live-dot"></span> Enterprise Access Control & RBAC
          </div>
          <h2>🛡️ Admin Management Console</h2>
          <p className="admin-hero-sub">
            Manage Whitelisted Email Domains, User Directories, Security Audit Logs, and Study-Level Data Permissions.
          </p>
        </div>
        <div className="admin-hero-actions">
          <button 
            className="btn-sync-db" 
            onClick={handleSyncDatabase} 
            disabled={syncingDb}
            title="Reload all assay, metadata, and overlay tables directly from Supabase Cloud into memory cache"
          >
            {syncingDb ? (
              <>
                <span className="spinner-sm"></span> Syncing Supabase...
              </>
            ) : (
              <>
                🔄 Sync Database
              </>
            )}
          </button>
          <button className="btn-secondary-lg" onClick={() => setCurrentView('database')}>
            📊 Database Search Workspace
          </button>
        </div>
      </div>

      {/* KPI Metrics Dashboard - Actionable & Interactive */}
      <div className="admin-metrics-grid">
        <div 
          className={`metric-card actionable ${activeTab === 'users' && statusFilter === 'all' ? 'active-card' : ''}`}
          onClick={() => { setActiveTab('users'); setStatusFilter('all'); setRoleFilter('all'); setUserSearch(''); }}
          title="Click to view all registered accounts"
        >
          <div className="metric-header">
            <span className="metric-icon">👥</span>
            <span className="metric-trend">Total</span>
          </div>
          <div className="metric-val">{users.length}</div>
          <div className="metric-label">Registered Accounts</div>
        </div>

        <div 
          className={`metric-card actionable ${pendingCount > 0 ? 'warning-card' : ''} ${activeTab === 'users' && statusFilter === 'pending' ? 'active-card' : ''}`}
          onClick={() => { setActiveTab('users'); setStatusFilter('pending'); setRoleFilter('all'); setUserSearch(''); }}
          title="Click to view accounts pending approval"
        >
          <div className="metric-header">
            <span className="metric-icon">⏳</span>
            <span className="metric-trend warning">{pendingCount > 0 ? 'Action Needed' : 'Clean'}</span>
          </div>
          <div className="metric-val">{pendingCount}</div>
          <div className="metric-label">Pending Approval</div>
        </div>

        <div 
          className={`metric-card actionable ${activeTab === 'users' && statusFilter === 'study_scoped' ? 'active-card' : ''}`}
          onClick={() => { setActiveTab('users'); setStatusFilter('study_scoped'); setRoleFilter('all'); setUserSearch(''); }}
          title="Click to view study-scoped users"
        >
          <div className="metric-header">
            <span className="metric-icon">🔒</span>
            <span className="metric-trend info">RBAC</span>
          </div>
          <div className="metric-val">{studyScopedCount}</div>
          <div className="metric-label">Study-Scoped Users</div>
        </div>

        <div 
          className={`metric-card actionable ${activeTab === 'users' && statusFilter === 'sample_scoped' ? 'active-card' : ''}`}
          onClick={() => { setActiveTab('users'); setStatusFilter('sample_scoped'); setRoleFilter('all'); setUserSearch(''); }}
          title="Click to view sample-scoped users"
        >
          <div className="metric-header">
            <span className="metric-icon">🎯</span>
            <span className="metric-trend warning">RBAC</span>
          </div>
          <div className="metric-val">{sampleScopedCount}</div>
          <div className="metric-label">Sample-Scoped Users</div>
        </div>

        <div 
          className={`metric-card actionable ${activeTab === 'whitelist' ? 'active-card' : ''}`}
          onClick={() => setActiveTab('whitelist')}
          title="Click to manage whitelisted email/domain patterns"
        >
          <div className="metric-header">
            <span className="metric-icon">🌐</span>
            <span className="metric-trend">Active</span>
          </div>
          <div className="metric-val">{whitelist.length}</div>
          <div className="metric-label">Whitelisted Patterns</div>
        </div>

        <div 
          className={`metric-card actionable ${activeTab === 'audit' ? 'active-card' : ''}`}
          onClick={() => setActiveTab('audit')}
          title="Click to view security audit logs"
        >
          <div className="metric-header">
            <span className="metric-icon">📜</span>
            <span className="metric-trend">Audit</span>
          </div>
          <div className="metric-val">{auditLogs.length}</div>
          <div className="metric-label">System Security Events</div>
        </div>

        <div 
          className="metric-card actionable"
          onClick={handleSyncDatabase}
          title="Click to synchronize live database cache with Supabase Cloud"
        >
          <div className="metric-header">
            <span className="metric-icon">⚡</span>
            <span className="metric-trend success">{syncingDb ? 'Syncing...' : 'Connected'}</span>
          </div>
          <div className="metric-val" style={{ fontSize: '18px', padding: '4px 0' }}>
            {syncingDb ? '⏳ Syncing...' : '🔄 Sync Now'}
          </div>
          <div className="metric-label">Supabase Cloud Cache</div>
        </div>
      </div>

      {/* Alert Notification */}
      {msg.text && (
        <div className={`admin-alert ${msg.type}`}>
          <span>{msg.type === 'error' ? '❌' : '✅'}</span>
          <span>{msg.text}</span>
        </div>
      )}

      {/* Subtabs */}
      <div className="admin-subtabs">
        <button 
          className={`subtab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          👥 User Directory & RBAC ({users.length}) {pendingCount > 0 && <span className="badge-pending">{pendingCount}</span>}
        </button>
        <button 
          className={`subtab-btn ${activeTab === 'whitelist' ? 'active' : ''}`}
          onClick={() => setActiveTab('whitelist')}
        >
          📧 Whitelist Registry ({whitelist.length})
        </button>
        <button 
          className={`subtab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          📜 Audit Logs ({auditLogs.length})
        </button>
      </div>

      {/* TAB 1: User Directory & Access Control */}
      {activeTab === 'users' && (
        <div className="admin-section">
          <div className="admin-toolbar">
            <div className="search-input-group">
              <span className="search-icon">🔍</span>
              <input 
                type="text" 
                placeholder="Search user by name or email..." 
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
            </div>
            <div className="filter-group">
              <label>Status:</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="all">All Statuses</option>
                <option value="pending">⏳ Pending Approval ({pendingCount})</option>
                <option value="approved">✅ Approved</option>
                <option value="study_scoped">🔒 Study-Scoped ({studyScopedCount})</option>
                <option value="sample_scoped">🎯 Sample-Scoped ({sampleScopedCount})</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Role:</label>
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                <option value="all">All Roles</option>
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          <div className="admin-table-container">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>User Profile</th>
                  <th>Role</th>
                  <th>Account Status</th>
                  <th>Download Access</th>
                  <th>Study Access</th>
                  <th>Sample Access Scope</th>
                  <th>Created At</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isUnrestrictedUserStudies = u.allowed_studies === '*' || !Array.isArray(u.allowed_studies)
                  const studyCount = isUnrestrictedUserStudies ? availableStudies.length : u.allowed_studies.length
                  const isUnrestrictedUserSamples = u.allowed_samples === '*' || !Array.isArray(u.allowed_samples)
                  const sampleCount = isUnrestrictedUserSamples ? 0 : u.allowed_samples.length

                  return (
                    <tr key={u.id}>
                      <td>
                        <div className="user-profile-cell">
                          <div className="avatar-circle">
                            {u.full_name ? u.full_name[0].toUpperCase() : u.email[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="user-full-name">{u.full_name || 'Unnamed User'}</div>
                            <div className="user-email-sub">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`role-badge ${u.role}`}>
                          {u.role === 'admin' ? '🛡️ Admin' : '👤 User'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${u.is_whitelisted ? 'approved' : 'pending'}`}>
                          {u.is_whitelisted ? '✅ Approved' : '⏳ Pending Whitelist'}
                        </span>
                      </td>
                      <td>
                        {u.role === 'admin' ? (
                          <span className="scope-badge unrestricted" title="Admins automatically have download and export access">
                            📥 Full Access
                          </span>
                        ) : (
                          <button
                            className={`status-badge ${u.can_download ? 'approved' : 'pending'}`}
                            style={{ cursor: 'pointer', border: 'none', padding: '4px 10px', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                            onClick={() => handleUserUpdate(u.id, { can_download: !u.can_download })}
                            title="Click to toggle data download permission for this user"
                          >
                            {u.can_download ? '📥 Allowed' : '🔒 Restricted'}
                          </button>
                        )}
                      </td>
                      <td>
                        <div className="study-scope-cell">
                          {isUnrestrictedUserStudies ? (
                            <span className="scope-badge unrestricted">
                              🌐 All Studies ({availableStudies.length})
                            </span>
                          ) : (
                            <span className="scope-badge scoped" title={u.allowed_studies.join(', ')}>
                              🔒 {studyCount} Stud{studyCount === 1 ? 'y' : 'ies'}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="study-scope-cell">
                          {isUnrestrictedUserSamples ? (
                            <span className="scope-badge unrestricted">
                              🌐 All Samples
                            </span>
                          ) : (
                            <span 
                              className="scope-badge sample-scoped" 
                              title={u.allowed_samples.slice(0, 30).join(', ') + (u.allowed_samples.length > 30 ? '...' : '')}
                            >
                              🎯 {sampleCount} Sample{sampleCount === 1 ? '' : 's'}
                            </span>
                          )}
                          <button 
                            className="btn-scope-edit" 
                            onClick={() => openPermissionsModal(u)}
                            title="Configure Study & Sample-Wise Permissions"
                          >
                            ⚙️ Permissions
                          </button>
                        </div>
                      </td>
                      <td className="text-muted" style={{ fontSize: '0.85rem' }}>
                        {u.created_at ? u.created_at.split('T')[0] : 'N/A'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="action-buttons-group">
                          <button 
                            className={u.is_whitelisted ? 'btn-warn-sm' : 'btn-success-sm'}
                            onClick={() => handleUserUpdate(u.id, { is_whitelisted: !u.is_whitelisted })}
                          >
                            {u.is_whitelisted ? 'Revoke Access' : 'Approve Account'}
                          </button>
                          <button 
                            className="btn-secondary-sm"
                            onClick={() => handleUserUpdate(u.id, { role: u.role === 'admin' ? 'user' : 'admin' })}
                          >
                            {u.role === 'admin' ? 'Demote' : 'Make Admin'}
                          </button>
                          {currentUser && currentUser.id !== u.id && (
                            <button 
                              className="btn-danger-sm"
                              onClick={() => handleDeleteUser(u.id, u.email)}
                              title="Permanently Delete User Account"
                            >
                              🗑️ Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: Whitelist Registry */}
      {activeTab === 'whitelist' && (
        <div className="admin-section grid-2col">
          {/* Add Form */}
          <div className="whitelist-add-card">
            <h3>+ Whitelist New Pattern</h3>
            <p className="hint-text">
              Add a specific email (e.g. <code>researcher@institution.org</code>) or a company domain (e.g. <code>@farcastbio.com</code>) to grant immediate auto-approval.
            </p>
            <form className="whitelist-form-stacked" onSubmit={handleAddWhitelist}>
              <div className="form-group">
                <label>Email Pattern or Domain</label>
                <input 
                  type="text"
                  placeholder="e.g. name@company.com or @domain.com"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Department / Notes</label>
                <input 
                  type="text"
                  placeholder="e.g. Oncology R&D Team"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-primary-lg">
                + Add Whitelist Entry
              </button>
            </form>
          </div>

          {/* Table */}
          <div className="admin-table-container">
            <h3>Active Whitelist Rules</h3>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Pattern</th>
                  <th>Scope</th>
                  <th>Notes</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {whitelist.map((item) => {
                  const isDomain = item.pattern.startsWith('@')
                  return (
                    <tr key={item.id}>
                      <td className="font-mono">
                        <b>{item.pattern}</b>
                      </td>
                      <td>
                        <span className={`badge ${isDomain ? 'domain' : 'single'}`}>
                          {isDomain ? '🌐 Domain-wide' : '👤 Single Email'}
                        </span>
                      </td>
                      <td>{item.notes || '—'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button 
                          className="btn-danger-sm"
                          onClick={() => handleRemoveWhitelist(item.pattern)}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Audit Logs */}
      {activeTab === 'audit' && (
        <div className="admin-section">
          <div className="admin-table-container">
            <h3>System Audit Logs</h3>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor</th>
                  <th>Action Code</th>
                  <th>Event Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-muted font-mono" style={{ fontSize: '0.85rem' }}>
                      {log.timestamp ? log.timestamp.replace('T', ' ').substring(0, 19) : ''}
                    </td>
                    <td><b>{log.actor_email}</b></td>
                    <td>
                      <span className="audit-code-badge">{log.action}</span>
                    </td>
                    <td>{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* STUDY & SAMPLE ACCESS RBAC MODAL */}
      {editingUser && (
        <div className="modal-backdrop" onClick={() => setEditingUser(null)}>
          <div className="modal-card rbac-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>🛡️ Configure Data Access & RBAC Permissions</h3>
                <span className="modal-subtitle">User: <b>{editingUser.email}</b> ({editingUser.full_name || 'Unnamed'})</span>
              </div>
              <button className="modal-close-btn" onClick={() => setEditingUser(null)}>✕</button>
            </div>

            <div className="modal-body">
              {/* SECTION 1: Study Permissions */}
              <div className="rbac-section-block">
                <div className="rbac-section-title">
                  <span>📂 1. Study-Level Data Scope</span>
                </div>
                <div className="access-toggle-box">
                  <label className={`toggle-option ${isUnrestrictedStudies ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="studyAccessMode" 
                      checked={isUnrestrictedStudies}
                      onChange={() => setIsUnrestrictedStudies(true)}
                    />
                    <div>
                      <strong>🌐 Unrestricted Access (All Studies)</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        User can query and view data across all studies (Biopharma, Internal R&D).
                      </p>
                    </div>
                  </label>

                  <label className={`toggle-option ${!isUnrestrictedStudies ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="studyAccessMode" 
                      checked={!isUnrestrictedStudies}
                      onChange={() => setIsUnrestrictedStudies(false)}
                    />
                    <div>
                      <strong>🔒 Restricted Study Access</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        Explicitly limit user to only see data belonging to checked studies below.
                      </p>
                    </div>
                  </label>
                </div>

                {!isUnrestrictedStudies && (
                  <div className="study-checkbox-grid">
                    <span className="section-label">Select Permitted Studies:</span>
                    <div className="checkboxes-wrapper">
                      {availableStudies.map((study) => {
                        const checked = selectedStudies.includes(study)
                        return (
                          <label key={study} className={`study-chip ${checked ? 'selected' : ''}`}>
                            <input 
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleStudySelection(study)}
                            />
                            <span>{study}</span>
                          </label>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* SECTION 2: Sample-Wise Permissions */}
              <div className="rbac-section-block" style={{ marginTop: '20px' }}>
                <div className="rbac-section-title">
                  <span>🎯 2. Sample-Wise Access Scope</span>
                </div>
                <div className="access-toggle-box">
                  <label className={`toggle-option ${isUnrestrictedSamples ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="sampleAccessMode" 
                      checked={isUnrestrictedSamples}
                      onChange={() => setIsUnrestrictedSamples(true)}
                    />
                    <div>
                      <strong>🌐 Unrestricted Samples (All Samples)</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        User can view all sample IDs within their permitted studies.
                      </p>
                    </div>
                  </label>

                  <label className={`toggle-option ${!isUnrestrictedSamples ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="sampleAccessMode" 
                      checked={!isUnrestrictedSamples}
                      onChange={() => setIsUnrestrictedSamples(false)}
                    />
                    <div>
                      <strong>🎯 Specific Sample IDs Only</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        Strictly limit user to view and search ONLY the sample IDs specified below.
                      </p>
                    </div>
                  </label>
                </div>

                {!isUnrestrictedSamples && (
                  <div className="sample-input-box">
                    <div className="sample-input-header">
                      <span className="section-label">Enter or Paste Allowed Sample IDs:</span>
                      <div className="sample-quick-actions">
                        <button 
                          type="button" 
                          className="btn-link-action"
                          onClick={() => setSampleInputText('')}
                        >
                          🧹 Clear
                        </button>
                        <button 
                          type="button" 
                          className="btn-link-action"
                          onClick={() => {
                            const parsed = sampleInputText
                              .split(/[\s,]+/)
                              .map(s => s.trim().toUpperCase())
                              .filter(Boolean)
                            setSampleInputText(Array.from(new Set(parsed)).join(', '))
                          }}
                        >
                          ✨ Format & Deduplicate
                        </button>
                      </div>
                    </div>
                    <textarea 
                      className="sample-textarea"
                      rows={4}
                      placeholder="e.g. FBR1A210009, FBR1A210010, FBR1A210016, FBR2O240350... (comma, space, or line separated)"
                      value={sampleInputText}
                      onChange={(e) => setSampleInputText(e.target.value)}
                    />
                    {(() => {
                      const parsed = sampleInputText
                        .split(/[\s,]+/)
                        .map(s => s.trim().toUpperCase())
                        .filter(Boolean)
                      const uniqueCount = new Set(parsed).size
                      return (
                        <div className="sample-count-badge">
                          <span>🎯 <b>{uniqueCount}</b> Unique Sample{uniqueCount === 1 ? '' : 's'} Configured</span>
                          {uniqueCount > 0 && (
                            <span className="sample-preview-list">
                              Preview: {Array.from(new Set(parsed)).slice(0, 5).join(', ')}{uniqueCount > 5 ? ` +${uniqueCount - 5} more` : ''}
                            </span>
                          )}
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>

              {/* SECTION 3: Download & Export Permissions */}
              <div className="rbac-section-block" style={{ marginTop: '20px' }}>
                <div className="rbac-section-title">
                  <span>📥 3. Data Download & Export Access</span>
                </div>
                <div className="access-toggle-box">
                  <label className={`toggle-option ${canDownloadAccess ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="downloadAccessMode" 
                      checked={canDownloadAccess}
                      onChange={() => setCanDownloadAccess(true)}
                    />
                    <div>
                      <strong>📥 Download Access Granted</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        User is authorized to export Excel/CSV reports from Bio-Repository and download Cohort datasets.
                      </p>
                    </div>
                  </label>

                  <label className={`toggle-option ${!canDownloadAccess ? 'active' : ''}`}>
                    <input 
                      type="radio" 
                      name="downloadAccessMode" 
                      checked={!canDownloadAccess}
                      onChange={() => setCanDownloadAccess(false)}
                    />
                    <div>
                      <strong>🔒 Download Access Restricted</strong>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted)' }}>
                        User can browse and query data in the UI, but cannot download or export files without admin permission.
                      </p>
                    </div>
                  </label>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setEditingUser(null)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleSavePermissions}>
                Save Permissions
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
