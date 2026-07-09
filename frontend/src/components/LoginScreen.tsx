import { useState } from 'react'
import type { FormEvent } from 'react'
import { login, signup } from '../api/authApi'
import { ApiError } from '../api/client'
import type { User } from '../api/types'
import './LoginScreen.css'

type Mode = 'initial' | 'need-password' | 'signup' | 'locked'

export default function LoginScreen({ onLoggedIn }: { onLoggedIn: (user: User) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [mode, setMode] = useState<Mode>('initial')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = () => {
    setMode('initial')
    setPassword('')
    setConfirmPassword('')
    setError(null)
  }

  const handleProbe = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = username.trim()
    if (!trimmed || submitting) return

    setSubmitting(true)
    setError(null)
    login(trimmed)
      .then(onLoggedIn)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setMode('signup')
        } else if (err instanceof ApiError && err.status === 403) {
          setMode('locked')
        } else if (err instanceof ApiError && err.status === 401) {
          setMode('need-password')
        } else {
          setError('Could not sign in. Please try again.')
        }
      })
      .finally(() => setSubmitting(false))
  }

  const handleLoginWithPassword = (e: FormEvent) => {
    e.preventDefault()
    if (!password || submitting) return

    setSubmitting(true)
    setError(null)
    login(username.trim(), password)
      .then(onLoggedIn)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) {
          setMode('locked')
        } else {
          setError('Incorrect password.')
        }
      })
      .finally(() => setSubmitting(false))
  }

  const handleSignup = (e: FormEvent) => {
    e.preventDefault()
    if (!password || submitting) return
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    setError(null)
    signup(username.trim(), password)
      .then(onLoggedIn)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 409) {
          setError('That username was just taken by someone else. Please try a different one.')
          reset()
        } else {
          setError('Could not create account. Please try again.')
        }
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>Sea the Bigger Picture</h1>

        {mode === 'initial' && (
          <>
            <p>Enter a username to continue. This browser stays signed in.</p>
            <form onSubmit={handleProbe}>
              <input
                type="text"
                className="login-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                maxLength={64}
                disabled={submitting}
                autoFocus
              />
              {error && <p className="login-error">{error}</p>}
              <button type="submit" className="btn btn-primary" disabled={submitting || !username.trim()}>
                {submitting ? 'Continuing…' : 'Continue'}
              </button>
            </form>
          </>
        )}

        {mode === 'need-password' && (
          <>
            <p>This account needs a password to continue.</p>
            <form onSubmit={handleLoginWithPassword}>
              <input type="text" className="login-input" value={username} disabled />
              <input
                type="password"
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                maxLength={127}
                disabled={submitting}
                autoFocus
              />
              {error && <p className="login-error">{error}</p>}
              <button type="submit" className="btn btn-primary" disabled={submitting || !password}>
                {submitting ? 'Signing in…' : 'Continue'}
              </button>
              <button type="button" className="btn" onClick={reset} disabled={submitting}>
                Try a different username
              </button>
            </form>
          </>
        )}

        {mode === 'signup' && (
          <>
            <p>No account with this username yet. Choose a password to create one.</p>
            <form onSubmit={handleSignup}>
              <input type="text" className="login-input" value={username} disabled />
              <input
                type="password"
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                minLength={10}
                maxLength={127}
                disabled={submitting}
                autoFocus
              />
              <input
                type="password"
                className="login-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                minLength={10}
                maxLength={127}
                disabled={submitting}
              />
              {error && <p className="login-error">{error}</p>}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || password.length < 10 || !confirmPassword}
              >
                {submitting ? 'Creating account…' : 'Create account'}
              </button>
              <button type="button" className="btn" onClick={reset} disabled={submitting}>
                Try a different username
              </button>
            </form>
          </>
        )}

        {mode === 'locked' && (
          <>
            <p>This account exists but doesn't have a password yet. Ask an admin to set one before you can log in.</p>
            <button type="button" className="btn btn-primary" onClick={reset}>
              Try a different username
            </button>
          </>
        )}
      </div>
    </div>
  )
}
