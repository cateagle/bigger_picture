import { useState } from 'react'
import type { FormEvent } from 'react'
import { setPassword } from '../../api/authApi'
import { ApiError } from '../../api/client'
import './AdminPanels.css'

export default function PasswordSettings() {
  const [password, setPasswordValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return

    setSubmitting(true)
    setError(null)
    setSaved(false)
    setPassword(password)
      .then(() => {
        setSaved(true)
        setPasswordValue('')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not update password.')
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <form className="admin-form" onSubmit={handleSubmit}>
      <h3>Change my password</h3>
      <label className="admin-form-field">
        New password
        <input
          type="password"
          value={password}
          required
          minLength={10}
          maxLength={127}
          onChange={(e) => setPasswordValue(e.target.value)}
        />
      </label>
      {error && <p className="game-status game-status-error">{error}</p>}
      {saved && <p className="game-status">Password updated.</p>}
      <div className="admin-form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save password'}
        </button>
      </div>
    </form>
  )
}
