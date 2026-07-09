import { useState } from 'react'
import type { FormEvent } from 'react'
import { login, signup } from '../api/authApi'
import { ApiError } from '../api/client'
import type { User } from '../api/types'
import './LoginScreen.css'

export default function LoginScreen({ onLoggedIn }: { onLoggedIn: (user: User) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [passwordRequired, setPasswordRequired] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = username.trim()
    if (!trimmed || submitting) return

    setSubmitting(true)
    setError(null)
    login(trimmed, passwordRequired ? password : undefined)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404 && !passwordRequired) {
          return signup(trimmed)
        }
        throw err
      })
      .then(onLoggedIn)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 409) {
          setError('That username was just taken by someone else. Please try a different one.')
        } else if (err instanceof ApiError && err.status === 401 && !passwordRequired) {
          setPasswordRequired(true)
        } else if (err instanceof ApiError && err.status === 401) {
          setError('Incorrect password.')
        } else {
          setError('Could not sign in. Please try again.')
        }
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>Sea the Bigger Picture</h1>
        <p>
          {passwordRequired
            ? 'This account needs a password to continue.'
            : 'Enter a username to continue — no password needed. Existing usernames log you back in; new ones create an account. This browser stays signed in.'}
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            className="login-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            maxLength={64}
            disabled={submitting || passwordRequired}
            autoFocus
          />
          {passwordRequired && (
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
          )}
          {error && <p className="login-error">{error}</p>}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting || !username.trim() || (passwordRequired && !password)}
          >
            {submitting ? 'Signing in…' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  )
}
