import React, { useState, useEffect } from 'react'
import { useStore } from '../store'

function PasswordInput({ value, onChange, placeholder = '••••••••', required = true, id = 'sec-pwd' }) {
  const [show, setShow] = useState(false)
  return (
    <div className="password-input-wrapper">
      <input
        id={id}
        type={show ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
      />
      <button
        type="button"
        className="password-toggle-btn"
        onClick={() => setShow(!show)}
        title={show ? 'Hide password' : 'Show password'}
        tabIndex="-1"
      >
        {show ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  )
}

// ── Password strength helper ───────────────────────────────────────────────────
function getPasswordStrength(pwd) {
  if (!pwd) return { score: 0, label: '', color: '' }
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd)) score++
  if (/[0-9]/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd)) score++
  const labels = ['', 'Weak', 'Fair', 'Strong', 'Very Strong']
  const colors = ['', '#EF4444', '#F59E0B', '#10B981', '#6366F1']
  return { score, label: labels[score] || 'Weak', color: colors[score] || '#EF4444' }
}

// ── UA parser helper ───────────────────────────────────────────────────────────
function parseUserAgent(ua) {
  if (!ua || ua === 'unknown') return 'Unknown Device'
  let browser = 'Browser'
  let os = 'OS'

  if (/Edg\//.test(ua)) browser = 'Edge'
  else if (/OPR\/|Opera/.test(ua)) browser = 'Opera'
  else if (/Chrome\//.test(ua)) browser = 'Chrome'
  else if (/Firefox\//.test(ua)) browser = 'Firefox'
  else if (/Safari\//.test(ua) && !/Chrome/.test(ua)) browser = 'Safari'
  else if (/MSIE|Trident/.test(ua)) browser = 'IE'

  if (/Windows NT 10/.test(ua)) os = 'Win 10'
  else if (/Windows NT 6\.3/.test(ua)) os = 'Win 8.1'
  else if (/Windows NT 6\.1/.test(ua)) os = 'Win 7'
  else if (/Windows/.test(ua)) os = 'Windows'
  else if (/Mac OS X/.test(ua)) os = 'macOS'
  else if (/Linux/.test(ua)) os = 'Linux'
  else if (/Android/.test(ua)) os = 'Android'
  else if (/iPhone|iPad/.test(ua)) os = 'iOS'

  return `${browser} · ${os}`
}

export default function SecurityModal({ isOpen, onClose, initialTab = 'notifications' }) {
  const {
    user, authFetch, logout, updateUser, refreshUser,
    notifications, unreadNotificationsCount,
    fetchNotifications, markNotificationRead, markAllNotificationsRead
  } = useStore()

  const [tab, setTab] = useState(initialTab) // 'notifications' | 'password' | 'history' | 'verification' | 'deactivate'

  // Change Password state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Login History state
  const [loginHistory, setLoginHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Verification state
  const [verifCode, setVerifCode] = useState('')
  const [activeCodeInfo, setActiveCodeInfo] = useState(null)

  // Deactivation state
  const [deactPassword, setDeactPassword] = useState('')
  const [deactReason, setDeactReason] = useState('')
  const [deactConfirmText, setDeactConfirmText] = useState('')  // typed confirmation
  const [deactStep, setDeactStep] = useState(1)                // 1 = form, 2 = confirm dialog

  // Separate loading states (fix: shared loading state bug)
  const [loadingPwd, setLoadingPwd] = useState(false)
  const [loadingInstant, setLoadingInstant] = useState(false)
  const [loadingCode, setLoadingCode] = useState(false)
  const [loadingVerify, setLoadingVerify] = useState(false)
  const [loadingDeact, setLoadingDeact] = useState(false)

  // UI state
  const [msg, setMsg] = useState({ type: '', text: '' })

  const pwdStrength = getPasswordStrength(newPassword)

  const checkVerificationState = async () => {
    try {
      const data = await refreshUser()
      if (data?.pending_verification?.has_pending) {
        setActiveCodeInfo(data.pending_verification)
      } else {
        // Fix: clear activeCodeInfo if user is already verified or no pending code
        if (data?.user?.is_verified) {
          setActiveCodeInfo(null)
        }
      }
    } catch (e) {}
  }

  useEffect(() => {
    if (isOpen) {
      setTab(initialTab)
      setMsg({ type: '', text: '' })
      fetchNotifications()
      checkVerificationState()
      if (initialTab === 'history') {
        loadHistory()
      }
    }
  }, [isOpen, initialTab])

  const loadHistory = async () => {
    setLoadingHistory(true)
    try {
      const res = await authFetch('/api/auth/login-history')
      const data = await res.json()
      if (data.success) {
        setLoginHistory(data.history || [])
      }
    } catch (e) {
      // ignore
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleChangeTab = (newTab) => {
    setTab(newTab)
    setMsg({ type: '', text: '' })
    if (newTab === 'history') {
      loadHistory()
    }
    if (newTab === 'verification') {
      checkVerificationState()
    }
    if (newTab === 'deactivate') {
      setDeactStep(1)
      setDeactConfirmText('')
    }
  }

  // 1. Password change handler
  const handleChangePassword = async (e) => {
    e.preventDefault()
    setMsg({ type: '', text: '' })

    if (newPassword !== confirmPassword) {
      setMsg({ type: 'error', text: 'New passwords do not match.' })
      return
    }

    if (newPassword.length < 8) {
      setMsg({ type: 'error', text: 'New password must be at least 8 characters.' })
      return
    }
    if (!/[A-Z]/.test(newPassword)) {
      setMsg({ type: 'error', text: 'Password must contain at least one uppercase letter.' })
      return
    }
    if (!/[0-9]/.test(newPassword)) {
      setMsg({ type: 'error', text: 'Password must contain at least one number.' })
      return
    }

    setLoadingPwd(true)
    try {
      const res = await authFetch('/api/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Password change failed.')

      setMsg({ type: 'success', text: 'Password successfully updated! Security notification generated.' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      fetchNotifications()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoadingPwd(false)
    }
  }

  // 2. Email verification handlers
  const handleVerifyEmail = async (e) => {
    if (e) e.preventDefault()
    setMsg({ type: '', text: '' })

    if (!verifCode.trim()) {
      setMsg({ type: 'error', text: 'Please enter a valid verification code.' })
      return
    }

    setLoadingVerify(true)
    try {
      const res = await authFetch('/api/auth/verify-email', {
        method: 'POST',
        body: JSON.stringify({
          email: user?.email,
          code: verifCode.trim(),
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Verification failed.')

      setMsg({ type: 'success', text: 'Email ownership confirmed successfully! Your account is now verified.' })
      updateUser({ is_verified: true })
      setVerifCode('')
      setActiveCodeInfo(null)
      fetchNotifications()
      refreshUser()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoadingVerify(false)
    }
  }

  const handleSendCode = async () => {
    setMsg({ type: '', text: '' })
    setLoadingCode(true)
    try {
      const res = await authFetch('/api/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email: user?.email }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to generate code.')

      if (data.is_verified) {
        updateUser({ is_verified: true })
        setMsg({ type: 'success', text: 'Your email address is already verified!' })
        return
      }

      const generatedCode = data.verification_code || ''
      if (generatedCode) {
        setActiveCodeInfo({ code: generatedCode })
        setVerifCode(generatedCode)
      }
      // Fix: do NOT expose the raw code in the alert message
      setMsg({
        type: 'success',
        text: 'Verification code generated and sent to your Notifications Bell.'
      })
      fetchNotifications()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoadingCode(false)
    }
  }

  const handleInstantVerify = async () => {
    setMsg({ type: '', text: '' })
    setLoadingInstant(true)
    try {
      const res = await authFetch('/api/auth/verify-email-instant', {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Instant verification failed.')

      setMsg({ type: 'success', text: 'Email verified successfully! You have confirmed account ownership.' })
      updateUser({ is_verified: true })
      setVerifCode('')
      setActiveCodeInfo(null)
      fetchNotifications()
      refreshUser()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoadingInstant(false)
    }
  }

  // 3. Deactivate Account — inline confirmation (no browser dialogs)
  const handleDeactivateSubmit = (e) => {
    e.preventDefault()
    setMsg({ type: '', text: '' })
    // Move to typed-confirm step
    setDeactStep(2)
  }

  const handleDeactivateConfirm = async () => {
    if (deactConfirmText !== 'DEACTIVATE') {
      setMsg({ type: 'error', text: 'Please type DEACTIVATE exactly to confirm.' })
      return
    }
    setMsg({ type: '', text: '' })
    setLoadingDeact(true)
    try {
      const res = await authFetch('/api/auth/deactivate', {
        method: 'POST',
        body: JSON.stringify({
          password: deactPassword,
          reason: deactReason || 'User requested suspension',
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to deactivate account.')

      setMsg({ type: 'success', text: 'Your account has been deactivated. You will now be signed out.' })
      setTimeout(() => {
        logout()
        onClose()
      }, 1800)
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
      setDeactStep(1)
    } finally {
      setLoadingDeact(false)
    }
  }

  // Last login info from history (displayed in header)
  const lastLogin = user?.last_login
    ? new Date(user.last_login).toLocaleString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : null

  if (!isOpen) return null

  return (
    <div className="security-modal-overlay" onClick={onClose}>
      <div className="security-modal-container" onClick={(e) => e.stopPropagation()}>

        {/* Modal Header */}
        <div className="security-modal-header">
          <div className="security-header-title">
            <span className="security-icon-badge">🛡️</span>
            <div>
              <h3>Account Security &amp; Preferences</h3>
              <p className="security-subtitle">
                Logged in as <b>{user?.email}</b> ({user?.role === 'admin' ? 'Administrator' : 'User'})
                {lastLogin && <span style={{ marginLeft: 8, color: '#94A3B8', fontWeight: 400 }}>· Last login: {lastLogin}</span>}
              </p>
            </div>
          </div>
          <button className="security-close-btn" onClick={onClose} title="Close">×</button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="security-modal-nav">
          <button
            className={`sec-nav-btn ${tab === 'notifications' ? 'active' : ''}`}
            onClick={() => handleChangeTab('notifications')}
          >
            🔔 Notifications {unreadNotificationsCount > 0 && <span className="unread-pill">{unreadNotificationsCount}</span>}
          </button>
          <button
            className={`sec-nav-btn ${tab === 'password' ? 'active' : ''}`}
            onClick={() => handleChangeTab('password')}
          >
            🔑 Password &amp; Security
          </button>
          <button
            className={`sec-nav-btn ${tab === 'history' ? 'active' : ''}`}
            onClick={() => handleChangeTab('history')}
          >
            📋 Login History
          </button>
          <button
            className={`sec-nav-btn ${tab === 'verification' ? 'active' : ''}`}
            onClick={() => handleChangeTab('verification')}
          >
            📧 Email Status {!user?.is_verified && <span className="warning-dot" title="Unverified"></span>}
          </button>
          <button
            className={`sec-nav-btn danger ${tab === 'deactivate' ? 'active' : ''}`}
            onClick={() => handleChangeTab('deactivate')}
          >
            ⚠️ Deactivate
          </button>
        </div>

        {/* Alert Notifications */}
        {msg.text && (
          <div className={`auth-alert ${msg.type}`} style={{ margin: '16px 24px 0' }}>
            <span className="alert-icon">{msg.type === 'success' ? '✅' : '⚠️'}</span>
            <span>{msg.text}</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="security-modal-body">

          {/* TAB 1: NOTIFICATIONS */}
          {tab === 'notifications' && (
            <div className="sec-tab-content">

              {/* User profile card */}
              <div className="sec-profile-card">
                <div className="sec-profile-avatar">
                  {(user?.full_name || user?.email || '?')[0].toUpperCase()}
                </div>
                <div className="sec-profile-info">
                  <span className="sec-profile-name">{user?.full_name || user?.email}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span className={`sec-profile-badge ${user?.role === 'admin' ? 'admin' : 'user'}`}>
                      {user?.role === 'admin' ? '⚙️ Admin' : '👤 User'}
                    </span>
                    <span className={`sec-profile-badge ${user?.is_verified ? 'verified' : 'unverified'}`}>
                      {user?.is_verified ? '✅ Verified' : '⚠️ Unverified'}
                    </span>
                    {user?.is_whitelisted && (
                      <span className="sec-profile-badge whitelisted">🔓 Whitelisted</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="sec-section-header">
                <div>
                  <h4>Security &amp; Account Notifications</h4>
                  <p className="sec-desc">Real-time alerts regarding logins, password changes, and access updates.</p>
                </div>
                {notifications.some(n => !n.is_read) && (
                  <button className="sec-btn-text" onClick={markAllNotificationsRead}>
                    Mark all as read
                  </button>
                )}
              </div>

              {notifications.length === 0 ? (
                <div className="sec-empty-state">
                  <span className="empty-icon">🔔</span>
                  <p>No notifications yet. You're all caught up!</p>
                </div>
              ) : (
                <div className="sec-notifications-list">
                  {notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`sec-notif-card ${!n.is_read ? 'unread' : ''}`}
                      onClick={() => !n.is_read && markNotificationRead(n.id)}
                    >
                      <div className="sec-notif-icon">
                        {n.notification_type === 'password' ? '🔒' :
                         n.notification_type === 'account' ? '✨' :
                         n.notification_type === 'security' ? '🛡️' : 'ℹ️'}
                      </div>
                      <div className="sec-notif-info">
                        <div className="sec-notif-title-row">
                          <span className="sec-notif-title">{n.title}</span>
                          <span className="sec-notif-time">
                            {n.created_at ? new Date(n.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently'}
                          </span>
                        </div>
                        <p className="sec-notif-msg">{n.message}</p>
                      </div>
                      {!n.is_read && <span className="sec-unread-dot" title="Unread notification"></span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: PASSWORD CHANGE */}
          {tab === 'password' && (
            <div className="sec-tab-content">
              <div className="sec-section-header">
                <div>
                  <h4>Change Account Password</h4>
                  <p className="sec-desc">Update your password regularly to keep your enterprise research account secure.</p>
                </div>
              </div>

              <form className="auth-form" onSubmit={handleChangePassword}>
                <div className="form-group">
                  <label htmlFor="cur-pwd">Current Password</label>
                  <PasswordInput
                    id="cur-pwd"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="new-pwd">New Password</label>
                  <PasswordInput
                    id="new-pwd"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min 8 chars, 1 uppercase, 1 number"
                    required
                  />

                  {/* Password Strength Meter */}
                  {newPassword.length > 0 && (
                    <div className="pwd-strength-bar" style={{ marginTop: 8 }}>
                      <div className="pwd-strength-segments">
                        {[1, 2, 3, 4].map(i => (
                          <div
                            key={i}
                            className="pwd-strength-seg"
                            style={{
                              background: i <= pwdStrength.score ? pwdStrength.color : '#E2E8F0'
                            }}
                          />
                        ))}
                      </div>
                      {pwdStrength.label && (
                        <span className="pwd-strength-label" style={{ color: pwdStrength.color }}>
                          {pwdStrength.label}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Requirements checklist */}
                  <div className="pwd-requirements">
                    <div className={`pwd-req-item ${newPassword.length >= 8 ? 'met' : ''}`}>
                      {newPassword.length >= 8 ? '✓' : '○'} At least 8 characters
                    </div>
                    <div className={`pwd-req-item ${/[A-Z]/.test(newPassword) ? 'met' : ''}`}>
                      {/[A-Z]/.test(newPassword) ? '✓' : '○'} One uppercase letter
                    </div>
                    <div className={`pwd-req-item ${/[0-9]/.test(newPassword) ? 'met' : ''}`}>
                      {/[0-9]/.test(newPassword) ? '✓' : '○'} One number
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="conf-pwd">Confirm New Password</label>
                  <PasswordInput
                    id="conf-pwd"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    required
                  />
                </div>

                <button type="submit" className="auth-btn-submit" disabled={loadingPwd}>
                  {loadingPwd ? 'Updating Password...' : 'Save New Password'}
                </button>
              </form>
            </div>
          )}

          {/* TAB 3: LOGIN HISTORY */}
          {tab === 'history' && (
            <div className="sec-tab-content">
              <div className="sec-section-header">
                <div>
                  <h4>Recent Login Activity</h4>
                  <p className="sec-desc">Review recent authentication events and devices associated with your account.</p>
                </div>
                <button className="sec-btn-text" onClick={loadHistory} disabled={loadingHistory}>
                  🔄 Refresh
                </button>
              </div>

              {loadingHistory ? (
                <div className="sec-loading-state">
                  <span className="spinner-sm"></span> Loading authentication history...
                </div>
              ) : loginHistory.length === 0 ? (
                <div className="sec-empty-state">
                  <p>No login records logged yet.</p>
                </div>
              ) : (
                <div className="sec-history-table-wrapper">
                  <table className="sec-history-table">
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Status</th>
                        <th>IP Address</th>
                        <th>Client / Device</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loginHistory.map((h) => (
                        <tr key={h.id}>
                          <td className="timestamp-cell">
                            {h.timestamp ? new Date(h.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                          </td>
                          <td>
                            <span className={`status-badge-chip ${h.status.toLowerCase()}`}>
                              {h.status === 'SUCCESS' ? '✓ Success' :
                               h.status === 'BLOCKED' ? '⛔ Blocked' : '✗ Failed'}
                            </span>
                          </td>
                          <td className="monospace-cell">{h.ip_address || '—'}</td>
                          <td className="ua-cell" title={h.user_agent}>
                            {parseUserAgent(h.user_agent)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: EMAIL STATUS */}
          {tab === 'verification' && (
            <div className="sec-tab-content">
              <div className="sec-section-header">
                <div>
                  <h4>Email Verification Status</h4>
                  <p className="sec-desc">Verifying your email confirms account ownership and enables critical security alerts.</p>
                </div>
              </div>

              {user?.is_verified ? (
                <div className="sec-verified-box" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <span className="verified-big-icon">✅</span>
                    <div>
                      <h5 style={{ fontSize: '15px' }}>Email Confirmed &amp; Verified</h5>
                      <p>Your work email (<b>{user?.email}</b>) has been fully verified.</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4, width: '100%', justifyContent: 'space-between', borderTop: '1px solid #A7F3D0', paddingTop: 10 }}>
                    <span style={{ fontSize: '11.5px', color: '#047857' }}>Status: Protected &amp; Whitelisted</span>
                    <button
                      type="button"
                      className="btn-secondary-md"
                      style={{ padding: '4px 10px', fontSize: '11.5px' }}
                      onClick={checkVerificationState}
                      disabled={loadingInstant || loadingCode}
                    >
                      🔄 Refresh Status
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div className="sec-unverified-box">
                    <div className="unverified-header">
                      <span className="unverified-icon">⚠️</span>
                      <div>
                        <h5>Email Not Yet Verified</h5>
                        <p>Account ownership for <b>{user?.email}</b> has not been confirmed. Choose a verification method below.</p>
                      </div>
                    </div>
                  </div>

                  {/* Method 1: Instant Verification */}
                  <div style={{
                    background: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '13.5px', color: '#1E2859', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>⚡</span> Instant Self-Verification
                      </span>
                      <span style={{ fontSize: '11px', background: '#EEF2FF', color: '#4F46E5', fontWeight: 600, padding: '2px 8px', borderRadius: '4px' }}>
                        Fastest
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: '12.5px', color: '#475569', lineHeight: 1.4 }}>
                      Since you are actively logged in to your account, you can verify ownership immediately with 1-click without waiting for an email.
                    </p>
                    <button
                      type="button"
                      className="auth-btn-submit"
                      style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', marginTop: 4 }}
                      onClick={handleInstantVerify}
                      disabled={loadingInstant}
                    >
                      {loadingInstant ? 'Verifying...' : '⚡ Verify Email Instantly'}
                    </button>
                  </div>

                  {/* Method 2: 6-Digit Code */}
                  <div style={{
                    background: '#FFFFFF',
                    border: '1px solid #E2E8F0',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 700, fontSize: '13.5px', color: '#1E2859', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>🔑</span> 6-Digit Verification PIN
                      </span>
                      <button
                        type="button"
                        className="btn-secondary-md"
                        style={{ padding: '5px 12px', fontSize: '12px' }}
                        onClick={handleSendCode}
                        disabled={loadingCode}
                      >
                        {loadingCode ? 'Generating...' : '📩 Generate / Send Code'}
                      </button>
                    </div>

                    <p style={{ margin: 0, fontSize: '12.5px', color: '#475569', lineHeight: 1.4 }}>
                      Request a PIN. The code will be dispatched to your email and stored in your in-app Security Bell (🔔).
                    </p>

                    {(activeCodeInfo?.code || verifCode) && (
                      <div style={{
                        background: '#FAF5FF',
                        border: '1px dashed #C084FC',
                        borderRadius: '6px',
                        padding: '10px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}>
                        <div>
                          <span style={{ fontSize: '11px', color: '#7E22CE', fontWeight: 600, display: 'block', textTransform: 'uppercase' }}>
                            Active Verification Code
                          </span>
                          <span style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '4px', color: '#6B21A8', fontFamily: 'var(--mono)' }}>
                            {activeCodeInfo?.code || verifCode}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="btn-secondary-md"
                          style={{ fontSize: '11.5px', padding: '4px 10px', background: '#F3E8FF', borderColor: '#D8B4FE', color: '#6B21A8' }}
                          onClick={() => setVerifCode(activeCodeInfo?.code || verifCode)}
                        >
                          ✨ Auto-Fill Code
                        </button>
                      </div>
                    )}

                    <form className="auth-form" onSubmit={handleVerifyEmail} style={{ marginTop: 2 }}>
                      <div className="form-group" style={{ marginBottom: 12 }}>
                        <label htmlFor="sec-verif-code" style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
                          Enter 6-Digit Code
                        </label>
                        <input
                          id="sec-verif-code"
                          type="text"
                          placeholder="e.g. 191865"
                          value={verifCode}
                          onChange={(e) => setVerifCode(e.target.value)}
                          maxLength={10}
                          required
                          className="monospace-input"
                          style={{ textAlign: 'center', fontSize: '16px', letterSpacing: '3px', fontWeight: 700 }}
                        />
                      </div>

                      <button
                        type="submit"
                        className="auth-btn-submit"
                        disabled={loadingVerify || !verifCode.trim()}
                        style={{ width: '100%' }}
                      >
                        {loadingVerify ? 'Confirming...' : '✓ Confirm & Verify Code'}
                      </button>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: DEACTIVATE ACCOUNT */}
          {tab === 'deactivate' && (
            <div className="sec-tab-content danger-zone">
              <div className="sec-section-header">
                <div>
                  <h4 style={{ color: 'var(--red, #ef4444)' }}>Deactivate FarCast Account</h4>
                  <p className="sec-desc">
                    Deactivating your account immediately suspends active database sessions and revokes query access. You can restore your account anytime via the sign-in page.
                  </p>
                </div>
              </div>

              <div className="danger-callout">
                <strong>Controlled Account Suspension</strong>
                <p>
                  Your audit history and saved permissions will be safely preserved. To resume access in the future, you will just need to authenticate with your password.
                </p>
              </div>

              {deactStep === 1 && (
                <form className="auth-form" onSubmit={handleDeactivateSubmit} style={{ marginTop: 16 }}>
                  <div className="form-group">
                    <label htmlFor="deact-pwd">Confirm Current Password</label>
                    <PasswordInput
                      id="deact-pwd"
                      value={deactPassword}
                      onChange={(e) => setDeactPassword(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="deact-reason">Reason for Suspension (Optional)</label>
                    <input
                      id="deact-reason"
                      type="text"
                      placeholder="e.g. Project completion, sabbatical, or department transfer"
                      value={deactReason}
                      onChange={(e) => setDeactReason(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="btn-danger-submit" disabled={!deactPassword}>
                    Continue to Confirm Deactivation →
                  </button>
                </form>
              )}

              {deactStep === 2 && (
                <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{
                    background: '#FEF2F2',
                    border: '1px solid #FECACA',
                    borderRadius: 8,
                    padding: '14px 16px'
                  }}>
                    <p style={{ margin: 0, fontSize: '13px', color: '#991B1B', fontWeight: 600 }}>
                      ⚠️ Final Confirmation Required
                    </p>
                    <p style={{ margin: '6px 0 0', fontSize: '12.5px', color: '#B91C1C' }}>
                      Type <b style={{ fontFamily: 'var(--mono)', letterSpacing: 1 }}>DEACTIVATE</b> in the box below to confirm account suspension.
                    </p>
                  </div>

                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
                      Type "DEACTIVATE" to confirm
                    </label>
                    <input
                      type="text"
                      className="deact-confirm-input"
                      placeholder="DEACTIVATE"
                      value={deactConfirmText}
                      onChange={(e) => setDeactConfirmText(e.target.value)}
                      autoFocus
                    />
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      type="button"
                      className="btn-secondary-md"
                      style={{ flex: 1 }}
                      onClick={() => { setDeactStep(1); setDeactConfirmText(''); setMsg({ type: '', text: '' }) }}
                      disabled={loadingDeact}
                    >
                      ← Go Back
                    </button>
                    <button
                      type="button"
                      className="btn-danger-submit"
                      style={{ flex: 2, marginTop: 0 }}
                      onClick={handleDeactivateConfirm}
                      disabled={loadingDeact || deactConfirmText !== 'DEACTIVATE'}
                    >
                      {loadingDeact ? 'Deactivating...' : 'Deactivate & Suspend Account'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
