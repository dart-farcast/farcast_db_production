import React, { useState } from 'react'
import { useStore } from '../store'
import FarcastLogo from './FarcastLogo'

export default function SignPage() {
  const { setAuth } = useStore()
  const [tab, setTab] = useState('login') // 'login' | 'register'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pendingUser, setPendingUser] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setPendingUser(null)
    setLoading(true)

    const endpoint = tab === 'login' ? '/api/auth/login' : '/api/auth/register'
    const body = tab === 'login'
      ? { email, password }
      : { email, password, full_name: fullName }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Authentication failed.')
      }

      // Check if whitelisted
      if (data.user && !data.user.is_whitelisted) {
        setPendingUser(data.user)
      } else {
        setAuth(data.user, data.token)
      }
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
          <h2>Farcast TruTumor Multimodal Database</h2>
          <p className="auth-subtitle">Production Research & Assay Platform</p>
        </div>

        {/* Tab Selection */}
        <div className="auth-tabs">
          <button
            className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(''); setPendingUser(null); }}
          >
            Sign In
          </button>
          <button
            className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); setPendingUser(null); }}
          >
            Create Account
          </button>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="auth-alert error">
            <span className="alert-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Pending Whitelist Notification */}
        {pendingUser && (
          <div className="auth-alert warning">
            <span className="alert-icon">⏳</span>
            <div>
              <strong>Access Pending Whitelist Approval</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem' }}>
                Your account (<b>{pendingUser.email}</b>) has been registered successfully. An administrator must whitelist your email before access to the database is granted.
              </p>
            </div>
          </div>
        )}

        {/* Form Body */}
        {!pendingUser && (
          <form className="auth-form" onSubmit={handleSubmit}>
            {tab === 'register' && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. Dr. Alex Morgan"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required={tab === 'register'}
                />
              </div>
            )}

            <div className="form-group">
              <label>Work Email</label>
              <input
                type="email"
                placeholder="name@farcastbio.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="auth-btn-submit" disabled={loading}>
              {loading ? 'Processing...' : (tab === 'login' ? 'Sign In' : 'Register Account')}
            </button>
          </form>
        )}

        {/* Default Admin Quick Login Hint */}
        <div className="auth-footer-hint">
          <span className="hint-label">🔑 Initial Admin Access:</span>
          <code>admin@farcastbio.com</code> / <code>admin123</code>
        </div>
      </div>
    </div>
  )
}
