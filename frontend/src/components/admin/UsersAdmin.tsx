import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { createUser, listUsers, updateUser } from '../../api/adminApi'
import { ApiError } from '../../api/client'
import type { Role, UserSummary } from '../../api/types'
import './AdminPanels.css'

const ROLES: Role[] = ['annotator', 'scientist', 'admin']

export default function UsersAdmin({ currentUserUuid }: { currentUserUuid: string }) {
  const [users, setUsers] = useState<UserSummary[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<UserSummary | null>(null)
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<Role>('annotator')
  const [expertLevel, setExpertLevel] = useState('0')
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const load = () => {
    setLoading(true)
    setError(null)
    listUsers()
      .then(setUsers)
      .catch(() => setError('Could not load users.'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const startCreate = () => {
    setEditing(null)
    setUsername('')
    setRole('annotator')
    setExpertLevel('0')
    setFormError(null)
  }

  const startEdit = (user: UserSummary) => {
    setEditing(user)
    setUsername(user.username)
    setRole(user.role)
    setExpertLevel(String(user.expert_level))
    setFormError(null)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return

    const expert_level = Number(expertLevel)
    if (!Number.isInteger(expert_level)) {
      setFormError('Expert level must be a whole number.')
      return
    }

    setFormError(null)
    setSubmitting(true)
    const request = editing
      ? updateUser(editing.uuid, { username, role, expert_level })
      : createUser({ username, role, expert_level })
    request
      .then(() => {
        load()
        startCreate()
      })
      .catch((err: unknown) => {
        setFormError(err instanceof ApiError ? err.message : 'Could not save this user.')
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-list">
        {loading && <p className="game-status">Loading…</p>}
        {error && <p className="game-status game-status-error">{error}</p>}
        {users && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
                <th>Expert level</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.uuid} className={editing?.uuid === user.uuid ? 'admin-row-active' : ''}>
                  <td>
                    {user.username}
                    {user.uuid === currentUserUuid && ' (you)'}
                  </td>
                  <td>{user.role}</td>
                  <td>{user.expert_level}</td>
                  <td>
                    <button type="button" className="btn" onClick={() => startEdit(user)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <form className="admin-form" onSubmit={handleSubmit}>
        <h3>{editing ? 'Edit user' : 'New user'}</h3>
        <label className="admin-form-field">
          Username
          <input type="text" value={username} required onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="admin-form-field">
          Role
          <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label className="admin-form-field">
          Expert level
          <input
            type="number"
            value={expertLevel}
            required
            onChange={(e) => setExpertLevel(e.target.value)}
          />
        </label>
        {formError && <p className="game-status game-status-error">{formError}</p>}
        <div className="admin-form-actions">
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Saving…' : editing ? 'Save changes' : 'Create'}
          </button>
          {editing && (
            <button type="button" className="btn" onClick={startCreate}>
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
