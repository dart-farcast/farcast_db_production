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

  // UI state
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState({ type: '', text: '' })

  const checkVerificationState = async () => {
    try {
      const data = await refreshUser()
      if (data?.pending_verification?.has_pending) {
        setActiveCodeInfo(data.pending_verification)
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
  }

  // 1. Password change handler
  const handleChangePassword = async (e) => {
    e.preventDefault()
    setMsg({ type: '', text: '' })

    if (newPassword !== confirmPassword) {
      setMsg({ type: 'error', text: 'New passwords do not match.' })
      return
    }

    if (newPassword.length < 6) {
      setMsg({ type: 'error', text: 'New password must be at least 6 characters.' })
      return
    }

    setLoading(true)
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
      setLoading(false)
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

    setLoading(true)
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
      setLoading(false)
    }
  }

  const handleSendCode = async () => {
    setMsg({ type: '', text: '' })
    setLoading(true)
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
      setMsg({ 
        type: 'success', 
        text: `Verification code generated: ${generatedCode}. Code has been auto-filled below and sent to your Notifications Bell.` 
      })
      fetchNotifications()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  const handleInstantVerify = async () => {
    setMsg({ type: '', text: '' })
    setLoading(true)
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
      setLoading(false)
    }
  }


  // 3. Deactivate Account
  const handleDeactivate = async (e) => {
    e.preventDefault()
    if (!confirm('Are you absolutely sure you want to deactivate your account? Access to the portal will be suspended until reactivation.')) return
    
    setMsg({ type: '', text: '' })
    setLoading(true)

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

      alert('Your account has been deactivated. You will now be signed out.')
      logout()
      onClose()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="security-modal-overlay" onClick={onClose}>
      <div className="security-modal-container" onClick={(e) => e.stopPropagation()}>
        
        {/* Modal Header */}
        <div className="security-modal-header">
          <div className="security-header-title">
            <span className="security-icon-badge">🛡️</span>
            <div>
              <h3>Account Security & Preferences</h3>
              <p className="security-subtitle">
                Logged in as <b>{user?.email}</b> ({user?.role === 'admin' ? 'Administrator' : 'User'})
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
            🔑 Password & Security
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
              <div className="sec-section-header">
                <div>
                  <h4>Security & Account Notifications</h4>
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
                    placeholder="Min 6 characters"
                    required
                  />
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

                <button type="submit" className="auth-btn-submit" disabled={loading}>
                  {loading ? 'Updating Password...' : 'Save New Password'}
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
                            {h.user_agent ? (h.user_agent.length > 38 ? h.user_agent.substring(0, 38) + '...' : h.user_agent) : 'Unknown Device'}
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
                      <h5 style={{ fontSize: '15px' }}>Email Confirmed & Verified</h5>
                      <p>Your work email (<b>{user?.email}</b>) has been fully verified.</p>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4, width: '100%', justifyContent: 'space-between', borderTop: '1px solid #A7F3D0', paddingTop: 10 }}>
                    <span style={{ fontSize: '11.5px', color: '#047857' }}>Status: Protected & Whitelisted</span>
                    <button 
                      type="button" 
                      className="btn-secondary-md" 
                      style={{ padding: '4px 10px', fontSize: '11.5px' }}
                      onClick={checkVerificationState}
                      disabled={loading}
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
                      disabled={loading}
                    >
                      {loading ? 'Verifying...' : '⚡ Verify Email Instantly'}
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
                        disabled={loading}
                      >
                        {loading ? 'Generating...' : '📩 Generate / Send Code'}
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
                        disabled={loading || !verifCode.trim()}
                        style={{ width: '100%' }}
                      >
                        {loading ? 'Confirming...' : '✓ Confirm & Verify Code'}
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

              <form className="auth-form" onSubmit={handleDeactivate} style={{ marginTop: 16 }}>
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

                <button type="submit" className="btn-danger-submit" disabled={loading}>
                  {loading ? 'Deactivating...' : 'Deactivate & Suspend Account'}
                </button>
              </form>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
