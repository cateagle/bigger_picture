import { useState } from 'react'
import type { FormEvent } from 'react'
import { signup } from '../api/authApi'
import { ApiError } from '../api/client'
import type { User } from '../api/types'
import './LoginScreen.css'

export default function LoginScreen({ onLoggedIn }: { onLoggedIn: (user: User) => void }) {
  const [username, setUsername] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = username.trim()
    if (!trimmed || submitting) return

    setSubmitting(true)
    setError(null)
    signup(trimmed)
      .then(onLoggedIn)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 409) {
          setError('That username is already taken. Log in from the browser where you first signed up with it.')
        } else {
          setError('Could not sign in. Please try again.')
        }
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>Bigger Picture</h1>
        <p>Pick a username to start playing — no password needed, this browser stays signed in.</p>
        <form onSubmit={handleSubmit}>
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
            {submitting ? 'Signing in…' : 'Start playing'}
          </button>
        </form>
      </div>
    </div>
  )
}
