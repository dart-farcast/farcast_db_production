import React, { useState } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'

// Show / Hide Password Eye Icon Toggle
function PasswordInput({ 
  value, 
  onChange, 
  placeholder = '••••••••', 
  required = true, 
  id = 'password-input', 
  name = 'password',
  autoComplete = 'current-password'
}) {
  const [show, setShow] = useState(false)

  return (
    <div className="password-input-wrapper">
      <input
        id={id}
        name={name}
        type={show ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        autoComplete={autoComplete}
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

export default function SignPage() {
  const { setAuth } = useStore()

  // Views: 'login' | 'register' | 'forgot' | 'reset' | 'verify' | 'reactivate'
  const [view, setView] = useState('login')

  // Form Fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmResetPassword, setConfirmResetPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [verificationCode, setVerificationCode] = useState('')
  const [resetCode, setResetCode] = useState('')

  // UI States
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [pendingUser, setPendingUser] = useState(null)
  const [accountDeactivated, setAccountDeactivated] = useState(false)

  const clearMessages = () => {
    setError('')
    setSuccessMsg('')
  }

  const navigateTo = (targetView) => {
    clearMessages()
    setPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setConfirmResetPassword('')
    if (targetView === 'login') {
      setResetCode('')
      setVerificationCode('')
    }
    setView(targetView)
  }

  // 1. Handle Login & Registration
  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    clearMessages()
    setPendingUser(null)
    setAccountDeactivated(false)
    setLoading(true)

    const endpoint = view === 'login' ? '/api/auth/login' : '/api/auth/register'
    const body = view === 'login'
      ? { email: email.trim().toLowerCase(), password, remember_me: rememberMe }
      : { email: email.trim().toLowerCase(), password, full_name: fullName.trim() }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (!res.ok || !data.success) {
        if (res.status === 403 && data.detail?.includes('deactivated')) {
          setAccountDeactivated(true)
        }
        throw new Error(data.detail || data.message || 'Authentication failed.')
      }

      if (view === 'register') {
        // Automatically offer verification step
        setSuccessMsg(data.message || 'Account registered! Please confirm email verification.')
        if (data.verification_code) {
          setVerificationCode(data.verification_code)
        }
        // Switch to verification view with registered email pre-filled
        setView('verify')
        return
      }

      // Check if whitelisted
      if (data.user && !data.user.is_whitelisted) {
        setPendingUser(data.user)
      } else {
        setAuth(data.user, data.token, rememberMe)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 2. Handle Forgot Password Request
  const handleForgotSubmit = async (e) => {
    e.preventDefault()
    clearMessages()
    setLoading(true)

    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Failed to request password reset.')
      }

      setSuccessMsg(data.message || 'A 6-digit recovery code has been sent to your email.')
      // DO NOT autofill recovery code — user must enter the OTP code received
      setResetCode('')
      setPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setConfirmResetPassword('')
      setView('reset')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 3. Handle Reset Password Execution
  const handleResetSubmit = async (e) => {
    e.preventDefault()
    clearMessages()

    if (!resetCode.trim()) {
      setError('Please enter the 6-digit recovery code received via email.')
      return
    }

    if (newPassword !== confirmResetPassword) {
      setError('New passwords do not match. Please re-enter.')
      return
    }

    if (newPassword.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          token: resetCode.trim(),
          new_password: newPassword
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Password reset failed.')
      }

      setSuccessMsg('Your password has been successfully reset! Please sign in with your new credentials.')
      setPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setConfirmResetPassword('')
      setResetCode('')
      setView('login')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 4. Handle Email Verification
  const handleVerifySubmit = async (e) => {
    e.preventDefault()
    clearMessages()
    setLoading(true)

    try {
      const res = await fetch('/api/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: verificationCode.trim()
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Email verification failed.')
      }

      setSuccessMsg('Email ownership verified successfully! You can now sign in.')
      setView('login')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleResendVerification = async () => {
    clearMessages()
    setLoading(true)
    try {
      const res = await fetch('/api/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.detail || 'Failed to resend code.')
      // Keep code field blank so user enters the OTP from their email
      setVerificationCode('')
      setSuccessMsg(data.message || 'New verification code has been dispatched to your email.')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // 5. Handle Reactivation
  const handleReactivateSubmit = async (e) => {
    e.preventDefault()
    clearMessages()
    setLoading(true)

    try {
      const res = await fetch('/api/auth/reactivate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password
        }),
      })
      const data = await res.json()
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Reactivation failed.')
      }

      setSuccessMsg('Account successfully reactivated! Please sign in now.')
      setAccountDeactivated(false)
      setView('login')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        {/* Brand Header */}
        <div className="auth-header">
          <div style={{ marginBottom: 12 }}>
            <FarcastLogo height={42} showSub={true} theme="dark" />
          </div>
          <h2>Farcast Data Explorer</h2>
          <p className="auth-subtitle">Production Research & Assay Platform</p>
        </div>

        {/* Tab Selection (Sign In vs Register) */}
        {(view === 'login' || view === 'register') && (
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${view === 'login' ? 'active' : ''}`}
              onClick={() => { setView('login'); clearMessages(); setPendingUser(null); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${view === 'register' ? 'active' : ''}`}
              onClick={() => { setView('register'); clearMessages(); setPendingUser(null); }}
            >
              Create Account
            </button>
          </div>
        )}

        {/* View Title for Special Flows */}
        {view === 'forgot' && (
          <div className="auth-subflow-header">
            <h3>🔑 Password Recovery</h3>
            <p>Enter your work email to receive password reset instructions.</p>
          </div>
        )}
        {view === 'reset' && (
          <div className="auth-subflow-header">
            <h3>🔒 Reset Your Password</h3>
            <p>Enter the 6-digit recovery code and choose a new secure password.</p>
          </div>
        )}
        {view === 'verify' && (
          <div className="auth-subflow-header">
            <h3>📧 Email Ownership Verification</h3>
            <p>Confirm account ownership for <b>{email}</b> to activate platform features.</p>
          </div>
        )}
        {view === 'reactivate' && (
          <div className="auth-subflow-header">
            <h3>🔄 Account Reactivation</h3>
            <p>Enter your credentials to restore your deactivated account.</p>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="auth-alert error">
            <span className="alert-icon">⚠️</span>
            <div style={{ flex: 1 }}>
              <span>{error}</span>
              {accountDeactivated && (
                <div style={{ marginTop: 8 }}>
                  <button 
                    type="button" 
                    className="auth-link-btn" 
                    onClick={() => { setView('reactivate'); clearMessages(); }}
                  >
                    👉 Click here to reactivate your account now
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Success Notification */}
        {successMsg && (
          <div className="auth-alert success">
            <span className="alert-icon">✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        {/* Pending Whitelist Notification */}
        {pendingUser && (
          <div className="auth-alert warning">
            <span className="alert-icon">⏳</span>
            <div>
              <strong>Access Pending Whitelist Approval</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem' }}>
                Your account (<b>{pendingUser.email}</b>) is registered. An administrator must whitelist your email domain before access to the database is granted.
              </p>
            </div>
          </div>
        )}

        {/* ── FLOW 1: LOGIN / REGISTER ────────────────────────────────────────── */}
        {!pendingUser && (view === 'login' || view === 'register') && (
          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {view === 'register' && (
              <div className="form-group">
                <label htmlFor="reg-fullname">Full Name</label>
                <input
                  id="reg-fullname"
                  type="text"
                  placeholder="e.g. Dr. Alex Morgan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required={view === 'register'}
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="auth-email">Work Email</label>
              <input
                id="auth-email"
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <div className="form-label-row">
                <label htmlFor="auth-password">Password</label>
                {view === 'login' && (
                  <button
                    type="button"
                    className="auth-link-text"
                    onClick={() => navigateTo('forgot')}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <PasswordInput
                id="auth-password"
                name="current-password"
                autoComplete={view === 'register' ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={view === 'register' ? 'Min 6 characters' : '••••••••'}
                required
              />
            </div>

            {/* Remember Me Checkbox */}
            {view === 'login' && (
              <div className="form-checkbox-row">
                <label className="checkbox-container">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span className="checkbox-custom"></span>
                  <span className="checkbox-label">Remember me for 30 days</span>
                </label>
              </div>
            )}

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? (
                <span className="btn-loading-content">
                  <span className="spinner-sm"></span> Processing...
                </span>
              ) : (view === 'login' ? 'Sign In' : 'Register Account')}
            </button>

            {/* Account Deactivation Prompt */}
            {view === 'login' && (
              <div className="auth-footer-links">
                <button
                  type="button"
                  className="auth-link-muted"
                  onClick={() => navigateTo('reactivate')}
                >
                  Deactivated account? Reactivate here
                </button>
                <span className="auth-sep">•</span>
                <button
                  type="button"
                  className="auth-link-muted"
                  onClick={() => navigateTo('verify')}
                >
                  Verify Email
                </button>
              </div>
            )}
          </form>
        )}

        {/* ── FLOW 2: FORGOT PASSWORD ─────────────────────────────────────────── */}
        {view === 'forgot' && (
          <form className="auth-form" onSubmit={handleForgotSubmit}>
            <div className="form-group">
              <label htmlFor="forgot-email">Enter Registered Work Email</label>
              <input
                id="forgot-email"
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? 'Sending Recovery Code...' : 'Generate Reset Code'}
            </button>

            <div className="auth-footer-links">
              <button
                type="button"
                className="auth-link-muted"
                onClick={() => navigateTo('reset')}
              >
                Already have a reset code?
              </button>
              <span className="auth-sep">•</span>
              <button
                type="button"
                className="auth-link-muted"
                onClick={() => navigateTo('login')}
              >
                Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ── FLOW 3: RESET PASSWORD ──────────────────────────────────────────── */}
        {view === 'reset' && (
          <form className="auth-form" onSubmit={handleResetSubmit}>
            <div className="form-group">
              <label htmlFor="reset-email">Work Email</label>
              <input
                id="reset-email"
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="reset-token">6-Digit Recovery Code / Reset Token</label>
              <input
                id="reset-token"
                name="otp-reset-token"
                type="text"
                placeholder="Enter 6-digit code from email"
                value={resetCode}
                onChange={(e) => setResetCode(e.target.value)}
                required
                className="monospace-input"
                autoComplete="one-time-code"
                maxLength={10}
              />
            </div>

            <div className="form-group">
              <label htmlFor="new-password">New Password</label>
              <PasswordInput
                id="new-password"
                name="farcast-new-password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 6 characters"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirm-new-password">Confirm New Password</label>
              <PasswordInput
                id="confirm-new-password"
                name="farcast-confirm-new-password"
                autoComplete="new-password"
                value={confirmResetPassword}
                onChange={(e) => setConfirmResetPassword(e.target.value)}
                placeholder="Re-enter new password"
                required
              />
            </div>

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? 'Updating Password...' : 'Reset Password & Secure Account'}
            </button>

            <div className="auth-footer-links">
              <button
                type="button"
                className="auth-link-muted"
                onClick={() => navigateTo('login')}
              >
                Return to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ── FLOW 4: EMAIL VERIFICATION ──────────────────────────────────────── */}
        {view === 'verify' && (
          <form className="auth-form" onSubmit={handleVerifySubmit}>
            <div className="form-group">
              <label htmlFor="verify-email">Account Email</label>
              <input
                id="verify-email"
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="verify-code">6-Digit Email Verification Code</label>
              <input
                id="verify-code"
                type="text"
                placeholder="e.g. 482190"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                required
                className="monospace-input"
                maxLength={10}
              />
            </div>

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? 'Verifying...' : 'Confirm Email Ownership'}
            </button>

            <div className="auth-footer-links">
              <button
                type="button"
                className="auth-link-muted"
                onClick={handleResendVerification}
                disabled={loading}
              >
                🔄 Resend Code
              </button>
              <span className="auth-sep">•</span>
              <button
                type="button"
                className="auth-link-muted"
                onClick={() => navigateTo('login')}
              >
                Return to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ── FLOW 5: REACTIVATION ────────────────────────────────────────────── */}
        {view === 'reactivate' && (
          <form className="auth-form" onSubmit={handleReactivateSubmit}>
            <div className="form-group">
              <label htmlFor="react-email">Account Email</label>
              <input
                id="react-email"
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="react-password">Password</label>
              <PasswordInput
                id="react-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? 'Reactivating...' : 'Reactivate My Account'}
            </button>

            <div className="auth-footer-links">
              <button
                type="button"
                className="auth-link-muted"
                onClick={() => { setView('login'); clearMessages(); }}
              >
                Back to Sign In
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  )
}
