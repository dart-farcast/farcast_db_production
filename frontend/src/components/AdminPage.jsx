import React, { useState, useEffect } from 'react'
import { useStore } from '../store'

export default function AdminPage() {
  const { authFetch, setCurrentView, updateUser, user: currentUser, setStats } = useStore()
  const [activeTab, setActiveTab] = useState('users') // 'users' | 'whitelist' | 'audit' | 'logins'

  // Data state
  const [whitelist, setWhitelist] = useState([])
  const [users, setUsers] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [availableStudies, setAvailableStudies] = useState([])
  const [globalLoginHistory, setGlobalLoginHistory] = useState([])
  const [loadingLogins, setLoadingLogins] = useState(false)

  // Database Sync state
  const [syncingDb, setSyncingDb] = useState(false)

  // Form states for Whitelist
  const [newPattern, setNewPattern] = useState('')
  const [newNotes, setNewNotes] = useState('')

  // Search & Filter state for user table
  const [userSearch, setUserSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all') // 'all' | 'pending' | 'approved' | 'active' | 'suspended' | 'verified' | 'unverified' | 'study_scoped' | 'sample_scoped'

  // Search & Filter for Login History table
  const [loginSearch, setLoginSearch] = useState('')
  const [loginStatusFilter, setLoginStatusFilter] = useState('all')

  // Modal State for Study & Sample Permissions
  const [editingUser, setEditingUser] = useState(null)
  const [selectedStudies, setSelectedStudies] = useState([])
  const [isUnrestrictedStudies, setIsUnrestrictedStudies] = useState(true)
  const [isUnrestrictedSamples, setIsUnrestrictedSamples] = useState(true)
  const [sampleInputText, setSampleInputText] = useState('')
  const [canDownloadAccess, setCanDownloadAccess] = useState(false)

  // Modal State for Invite User
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteFullName, setInviteFullName] = useState('')
  const [inviteRole, setInviteRole] = useState('user')
  const [inviteCanDownload, setInviteCanDownload] = useState(false)
  const [inviteTempPassword, setInviteTempPassword] = useState('')

  // Modal State for Generated Credentials / Password
  const [credentialsModal, setCredentialsModal] = useState(null) // { email, role, temporary_password, title }

  // Modal State for Specific User Login History
  const [userLoginModal, setUserLoginModal] = useState(null) // { email, history }

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

  const loadGlobalLogins = async () => {
    setLoadingLogins(true)
    try {
      const res = await authFetch('/api/admin/login-history')
      const data = await res.json()
      if (data.success && Array.isArray(data.history)) {
        setGlobalLoginHistory(data.history)
      }
    } catch (e) {
      // ignore
    } finally {
      setLoadingLogins(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (activeTab === 'logins') {
      loadGlobalLogins()
    }
  }, [activeTab])

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

  // Handle Admin User Invite
  const handleInviteSubmit = async (e) => {
    e.preventDefault()
    if (!inviteEmail.trim()) return

    setMsg({ type: '', text: '' })
    setLoading(true)

    try {
      const res = await authFetch('/api/admin/invite', {
        method: 'POST',
        body: JSON.stringify({
          email: inviteEmail.trim().toLowerCase(),
          full_name: inviteFullName.trim(),
          role: inviteRole,
          can_download: inviteCanDownload,
          temporary_password: inviteTempPassword.trim() || undefined
        })
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to invite user.')

      setShowInviteModal(false)
      setCredentialsModal({
        title: '🎉 User Invited & Provisioned Successfully',
        email: data.email,
        role: data.role,
        temporary_password: data.temporary_password,
        note: 'Please securely provide these login credentials to the user.'
      })

      setInviteEmail('')
      setInviteFullName('')
      setInviteRole('user')
      setInviteCanDownload(false)
      setInviteTempPassword('')
      loadData()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  // Handle Admin Reset User Password
  const handleAdminResetPassword = async (userId, userEmail) => {
    if (!confirm(`Generate a new temporary password for '${userEmail}'?`)) return

    setMsg({ type: '', text: '' })
    try {
      const res = await authFetch(`/api/admin/users/${userId}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({})
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to reset password.')

      setCredentialsModal({
        title: '🔑 Temporary Password Generated',
        email: userEmail,
        temporary_password: data.temporary_password,
        note: 'The user password has been reset. Please copy and provide this temporary password to the user.'
      })
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
  }

  // Handle View User Logins
  const handleViewUserLogins = async (userId, userEmail) => {
    try {
      const res = await authFetch(`/api/admin/users/${userId}/login-history`)
      const data = await res.json()
      if (data.success) {
        setUserLoginModal({
          email: userEmail,
          history: data.history || []
        })
      }
    } catch (e) {
      alert('Failed to load login history for this user.')
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
      statusFilter === 'active' ? u.is_active :
      statusFilter === 'suspended' ? !u.is_active :
      statusFilter === 'verified' ? u.is_verified :
      statusFilter === 'unverified' ? !u.is_verified :
      statusFilter === 'study_scoped' ? (u.allowed_studies !== '*' && Array.isArray(u.allowed_studies)) :
      statusFilter === 'sample_scoped' ? (u.allowed_samples !== '*' && Array.isArray(u.allowed_samples)) : true

    return matchesSearch && matchesRole && matchesStatus
  })

  // Filtered Login History list
  const filteredLogins = globalLoginHistory.filter(l => {
    const q = loginSearch.toLowerCase()
    const matchesSearch = !q || (
      (l.email && l.email.toLowerCase().includes(q)) ||
      (l.ip_address && l.ip_address.toLowerCase().includes(q)) ||
      (l.user_agent && l.user_agent.toLowerCase().includes(q))
    )
    const matchesStatus = loginStatusFilter === 'all' || l.status === loginStatusFilter
    return matchesSearch && matchesStatus
  })

  // Metrics
  const pendingCount = users.filter(u => !u.is_whitelisted).length
  const suspendedCount = users.filter(u => !u.is_active).length
  const unverifiedCount = users.filter(u => !u.is_verified).length
  const studyScopedCount = users.filter(u => u.allowed_studies !== '*' && Array.isArray(u.allowed_studies)).length
  const sampleScopedCount = users.filter(u => u.allowed_samples !== '*' && Array.isArray(u.allowed_samples)).length

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    alert('Copied to clipboard!')
  }

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
            className="btn-primary-invite" 
            onClick={() => setShowInviteModal(true)}
            title="Invite, provision, and assign roles to new users securely"
          >
            ➕ Invite User
          </button>
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
          className={`metric-card actionable ${suspendedCount > 0 ? 'danger-card' : ''} ${activeTab === 'users' && statusFilter === 'suspended' ? 'active-card' : ''}`}
          onClick={() => { setActiveTab('users'); setStatusFilter('suspended'); setRoleFilter('all'); setUserSearch(''); }}
          title="Click to view suspended / deactivated accounts"
        >
          <div className="metric-header">
            <span className="metric-icon">⛔</span>
            <span className="metric-trend danger">{suspendedCount > 0 ? `${suspendedCount} Suspended` : 'All Active'}</span>
          </div>
          <div className="metric-val">{suspendedCount}</div>
          <div className="metric-label">Suspended Accounts</div>
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
          className={`metric-card actionable ${activeTab === 'logins' ? 'active-card' : ''}`}
          onClick={() => setActiveTab('logins')}
          title="Click to view live authentication and login events"
        >
          <div className="metric-header">
            <span className="metric-icon">📋</span>
            <span className="metric-trend success">Live</span>
          </div>
          <div className="metric-val">Security</div>
          <div className="metric-label">Login History Logs</div>
        </div>
      </div>

      {/* Alert Notification */}
      {msg.text && (
        <div className={`admin-alert ${msg.type}`}>
          <span>{msg.type === 'error' ? '❌' : '✅'}</span>
          <span>{msg.text}</span>
        </div>
      )}

      {/* Subtabs Navigation */}
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
          className={`subtab-btn ${activeTab === 'logins' ? 'active' : ''}`}
          onClick={() => setActiveTab('logins')}
        >
          📋 Login Activity & Security Logs
        </button>
        <button 
          className={`subtab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          📜 Audit Logs ({auditLogs.length})
        </button>
      </div>

      {/* ── TAB 1: User Directory & Access Control ────────────────────────────── */}
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
                <option value="active">🟢 Active Users</option>
                <option value="suspended">⛔ Suspended Users ({suspendedCount})</option>
                <option value="verified">🛡️ Email Verified</option>
                <option value="unverified">⚠️ Email Unverified ({unverifiedCount})</option>
                <option value="study_scoped">🔒 Study-Scoped ({studyScopedCount})</option>
                <option value="sample_scoped">🎯 Sample-Scoped ({sampleScopedCount})</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Role:</label>
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="manager">Manager</option>
                <option value="analyst">Analyst</option>
                <option value="user">User</option>
              </select>
            </div>
          </div>

          <div className="admin-table-container">
            <div className="admin-table-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User Profile</th>
                    <th>Role</th>
                    <th>Account Status</th>
                    <th>Download Access</th>
                    <th>Study Access</th>
                    <th>Sample Access Scope</th>
                    <th>Last Login</th>
                    <th style={{ textAlign: 'right' }}>Actions & Controls</th>
                  </tr>
                </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isUnrestrictedUserStudies = u.allowed_studies === '*' || !Array.isArray(u.allowed_studies)
                  const studyCount = isUnrestrictedUserStudies ? availableStudies.length : u.allowed_studies.length
                  const isUnrestrictedUserSamples = u.allowed_samples === '*' || !Array.isArray(u.allowed_samples)
                  const sampleCount = isUnrestrictedUserSamples ? 0 : u.allowed_samples.length

                  return (
                    <tr key={u.id} className={!u.is_active ? 'row-suspended' : ''}>
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
                        <select 
                          className={`role-select ${u.role}`}
                          value={u.role}
                          onChange={(e) => handleUserUpdate(u.id, { role: e.target.value })}
                          title="Assign user role"
                        >
                          <option value="admin">🛡️ Admin</option>
                          <option value="manager">💼 Manager</option>
                          <option value="analyst">🔬 Analyst</option>
                          <option value="user">👤 User</option>
                        </select>
                      </td>
                      <td>
                        <div className="status-badges-stack">
                          {/* Active / Suspended */}
                          <span className={`status-pill ${u.is_active ? 'active' : 'suspended'}`}>
                            {u.is_active ? '🟢 Active' : '⛔ Suspended'}
                          </span>
                          
                          {/* Whitelist */}
                          <span className={`status-pill ${u.is_whitelisted ? 'approved' : 'pending'}`}>
                            {u.is_whitelisted ? '✅ Approved' : '⏳ Pending'}
                          </span>

                          {/* Email Verification */}
                          <span className={`status-pill ${u.is_verified ? 'verified' : 'unverified'}`}>
                            {u.is_verified ? '🛡️ Verified' : '⚠️ Unverified'}
                          </span>
                        </div>
                      </td>
                      <td>
                        {u.role === 'admin' ? (
                          <span className="scope-badge unrestricted" title="Admins automatically have download and export access">
                            📥 Full Access
                          </span>
                        ) : (
                          <button
                            className={`status-badge ${u.can_download ? 'approved' : 'pending'}`}
                            style={{ cursor: 'pointer', border: 'none', padding: '2.5px 7px', fontSize: '10.5px', display: 'inline-flex', alignItems: 'center', gap: 3 }}
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
                      <td className="text-muted" style={{ fontSize: '10.5px', whiteSpace: 'nowrap' }}>
                        {u.last_login ? new Date(u.last_login).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Never'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="action-buttons-group">
                          {/* Suspend / Reactivate */}
                          <button 
                            className={u.is_active ? 'btn-warn-sm' : 'btn-success-sm'}
                            onClick={() => handleUserUpdate(u.id, { is_active: !u.is_active })}
                            title={u.is_active ? 'Suspend and disable user account' : 'Reactivate user account'}
                          >
                            {u.is_active ? '⛔ Suspend' : '🟢 Restore'}
                          </button>

                          {/* Whitelist Toggle */}
                          <button 
                            className={u.is_whitelisted ? 'btn-secondary-sm' : 'btn-success-sm'}
                            onClick={() => handleUserUpdate(u.id, { is_whitelisted: !u.is_whitelisted })}
                            title={u.is_whitelisted ? 'Revoke whitelist approval' : 'Approve whitelist access'}
                          >
                            {u.is_whitelisted ? 'Revoke WL' : 'Approve WL'}
                          </button>

                          {/* Manual Email Verification */}
                          {!u.is_verified && (
                            <button
                              className="btn-secondary-sm"
                              onClick={() => handleUserUpdate(u.id, { is_verified: true })}
                              title="Manually verify this user's email address"
                            >
                              ✓ Verify
                            </button>
                          )}

                          {/* Reset Password */}
                          <button
                            className="btn-secondary-sm"
                            onClick={() => handleAdminResetPassword(u.id, u.email)}
                            title="Generate a new temporary password for user"
                          >
                            🔑 Reset
                          </button>

                          {/* View Logins */}
                          <button
                            className="btn-secondary-sm"
                            onClick={() => handleViewUserLogins(u.id, u.email)}
                            title="View recent login events for this user"
                          >
                            📋 Logins
                          </button>

                          {/* Delete */}
                          {currentUser && currentUser.id !== u.id && (
                            <button 
                              className="btn-danger-sm"
                              onClick={() => handleDeleteUser(u.id, u.email)}
                              title="Permanently Delete User Account"
                            >
                              🗑️
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
        </div>
      )}

      {/* ── TAB 2: Whitelist Registry ─────────────────────────────────────────── */}
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
            <div className="admin-table-scroll">
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
        </div>
      )}

      {/* ── TAB 3: Global Login Activity & Security Logs ──────────────────────── */}
      {activeTab === 'logins' && (
        <div className="admin-section">
          <div className="admin-toolbar">
            <div className="search-input-group">
              <span className="search-icon">🔍</span>
              <input 
                type="text" 
                placeholder="Search by user email, IP address, or device..." 
                value={loginSearch}
                onChange={(e) => setLoginSearch(e.target.value)}
              />
            </div>
            <div className="filter-group">
              <label>Status:</label>
              <select value={loginStatusFilter} onChange={(e) => setLoginStatusFilter(e.target.value)}>
                <option value="all">All Events</option>
                <option value="SUCCESS">✓ Successful Logins</option>
                <option value="FAILED">✗ Failed Attempts</option>
                <option value="BLOCKED">⛔ Blocked / Suspended Logins</option>
              </select>
            </div>
            <button className="btn-secondary-md" onClick={loadGlobalLogins} disabled={loadingLogins}>
              🔄 Refresh Logs
            </button>
          </div>

          <div className="admin-table-container">
            <h3>Authentication & Security Access Logs</h3>
            <div className="admin-table-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User Email</th>
                    <th>Status</th>
                    <th>IP Address</th>
                    <th>Device / User Agent</th>
                    <th>Event Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLogins.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '32px' }}>
                        No authentication events match your filter.
                      </td>
                    </tr>
                  ) : (
                    filteredLogins.map((l) => (
                      <tr key={l.id}>
                        <td className="text-muted font-mono" style={{ fontSize: '0.85rem' }}>
                          {l.timestamp ? new Date(l.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                        </td>
                        <td><b>{l.email}</b></td>
                        <td>
                          <span className={`status-pill ${l.status.toLowerCase()}`}>
                            {l.status === 'SUCCESS' ? '✓ Success' : 
                             l.status === 'BLOCKED' ? '⛔ Blocked' : '✗ Failed'}
                          </span>
                        </td>
                        <td className="monospace-cell">{l.ip_address || '—'}</td>
                        <td className="ua-cell" title={l.user_agent}>
                          {l.user_agent ? (l.user_agent.length > 40 ? l.user_agent.substring(0, 40) + '...' : l.user_agent) : 'Unknown Device'}
                        </td>
                        <td className="text-muted">{l.reason || '—'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 4: Audit Logs ─────────────────────────────────────────────────── */}
      {activeTab === 'audit' && (
        <div className="admin-section">
          <div className="admin-table-container">
            <h3>System Audit Logs</h3>
            <div className="admin-table-scroll">
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
        </div>
      )}

      {/* ── MODAL: INVITE USER ────────────────────────────────────────────────── */}
      {showInviteModal && (
        <div className="modal-backdrop" onClick={() => setShowInviteModal(false)}>
          <div className="modal-card invite-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>➕ Invite & Provision Platform User</h3>
                <span className="modal-subtitle">Directly configure role, permissions, and initial credentials</span>
              </div>
              <button className="modal-close-btn" onClick={() => setShowInviteModal(false)}>✕</button>
            </div>

            <form onSubmit={handleInviteSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label htmlFor="inv-email">Work Email Address *</label>
                  <input
                    id="inv-email"
                    type="email"
                    placeholder="colleague@farcastbio.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="inv-name">Full Name</label>
                  <input
                    id="inv-name"
                    type="text"
                    placeholder="e.g. Dr. Jordan Lee"
                    value={inviteFullName}
                    onChange={(e) => setInviteFullName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="inv-role">Assigned Platform Role</label>
                  <select
                    id="inv-role"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                  >
                    <option value="user">👤 User (Standard query & exploration)</option>
                    <option value="analyst">🔬 Analyst (Advanced querying & analysis)</option>
                    <option value="manager">💼 Manager (Department oversight & reporting)</option>
                    <option value="admin">🛡️ Administrator (Full system privileges)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="inv-pass">Temporary Initial Password (Optional)</label>
                  <input
                    id="inv-pass"
                    type="text"
                    placeholder="Leave blank to auto-generate secure password"
                    value={inviteTempPassword}
                    onChange={(e) => setInviteTempPassword(e.target.value)}
                  />
                </div>

                <div className="form-checkbox-row" style={{ marginTop: 12 }}>
                  <label className="checkbox-container">
                    <input
                      type="checkbox"
                      checked={inviteCanDownload}
                      onChange={(e) => setInviteCanDownload(e.target.checked)}
                    />
                    <span className="checkbox-custom"></span>
                    <span className="checkbox-label">Grant Data Download & Export Permission</span>
                  </label>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Creating User...' : 'Provision User Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CREDENTIALS COPY ───────────────────────────────────────────── */}
      {credentialsModal && (
        <div className="modal-backdrop" onClick={() => setCredentialsModal(null)}>
          <div className="modal-card credentials-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>{credentialsModal.title || '🔑 Account Credentials'}</h3>
                <span className="modal-subtitle">{credentialsModal.note}</span>
              </div>
              <button className="modal-close-btn" onClick={() => setCredentialsModal(null)}>✕</button>
            </div>

            <div className="modal-body">
              <div className="credentials-box">
                <div className="cred-row">
                  <span className="cred-label">Account Email:</span>
                  <span className="cred-val font-mono"><b>{credentialsModal.email}</b></span>
                </div>
                {credentialsModal.role && (
                  <div className="cred-row">
                    <span className="cred-label">Platform Role:</span>
                    <span className="cred-val"><b>{credentialsModal.role.toUpperCase()}</b></span>
                  </div>
                )}
                <div className="cred-row highlight">
                  <span className="cred-label">Temporary Password:</span>
                  <span className="cred-val font-mono">{credentialsModal.temporary_password}</span>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button 
                type="button" 
                className="btn-primary"
                onClick={() => {
                  const payload = `FarCast Platform Credentials\nEmail: ${credentialsModal.email}\nRole: ${credentialsModal.role || 'User'}\nPassword: ${credentialsModal.temporary_password}`
                  copyToClipboard(payload)
                }}
              >
                📋 Copy Credentials to Clipboard
              </button>
              <button type="button" className="btn-secondary" onClick={() => setCredentialsModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: USER SPECIFIC LOGIN HISTORY ─────────────────────────────────── */}
      {userLoginModal && (
        <div className="modal-backdrop" onClick={() => setUserLoginModal(null)}>
          <div className="modal-card user-logins-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>📋 Login History for {userLoginModal.email}</h3>
                <span className="modal-subtitle">Recent authentication attempts and device records</span>
              </div>
              <button className="modal-close-btn" onClick={() => setUserLoginModal(null)}>✕</button>
            </div>

            <div className="modal-body">
              {userLoginModal.history.length === 0 ? (
                <p style={{ textAlign: 'center', padding: '24px', color: 'var(--muted)' }}>
                  No login events logged for this user.
                </p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Status</th>
                      <th>IP Address</th>
                      <th>Device / User Agent</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {userLoginModal.history.map((h) => (
                      <tr key={h.id}>
                        <td className="text-muted font-mono">
                          {h.timestamp ? new Date(h.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                        </td>
                        <td>
                          <span className={`status-pill ${h.status.toLowerCase()}`}>
                            {h.status === 'SUCCESS' ? '✓ Success' : 
                             h.status === 'BLOCKED' ? '⛔ Blocked' : '✗ Failed'}
                          </span>
                        </td>
                        <td className="monospace-cell">{h.ip_address || '—'}</td>
                        <td className="ua-cell" title={h.user_agent}>
                          {h.user_agent ? (h.user_agent.length > 36 ? h.user_agent.substring(0, 36) + '...' : h.user_agent) : 'Unknown'}
                        </td>
                        <td className="text-muted">{h.reason || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={() => setUserLoginModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: STUDY & SAMPLE ACCESS RBAC ──────────────────────────────────── */}
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
                        User is authorized to export Excel/CSV reports from Discovery Cohort and download Response Cohort datasets.
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
