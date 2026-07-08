import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../../api/client'
import './AdminPanels.css'

export interface FieldConfig {
  key: string
  label: string
  type: 'text' | 'textarea' | 'json'
  required?: boolean
}

type EntityBase = { uuid: string; title: string }

export default function SimpleEntityAdmin<T extends EntityBase>({
  entityName,
  fields,
  fetchList,
  create,
  update,
}: {
  entityName: string
  fields: FieldConfig[]
  fetchList: () => Promise<T[]>
  create: (input: Record<string, unknown>) => Promise<T>
  update: (uuid: string, input: Record<string, unknown>) => Promise<T>
}) {
  const [rows, setRows] = useState<T[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<T | null>(null)
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchList()
      .then(setRows)
      .catch(() => setError(`Could not load ${entityName.toLowerCase()}.`))
      .finally(() => setLoading(false))
  }

  useEffect(load, [entityName, fetchList])

  const startCreate = () => {
    setEditing(null)
    setFormValues({})
    setFormError(null)
  }

  const startEdit = (row: T) => {
    setEditing(row)
    const values: Record<string, string> = {}
    for (const field of fields) {
      const value = (row as unknown as Record<string, unknown>)[field.key]
      values[field.key] = field.type === 'json' ? (value ? JSON.stringify(value, null, 2) : '') : ((value as string) ?? '')
    }
    setFormValues(values)
    setFormError(null)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return

    const payload: Record<string, unknown> = {}
    for (const field of fields) {
      const raw = formValues[field.key] ?? ''
      if (field.type === 'json') {
        if (raw.trim() === '') {
          payload[field.key] = null
          continue
        }
        try {
          payload[field.key] = JSON.parse(raw)
        } catch {
          setFormError(`${field.label} must be valid JSON.`)
          return
        }
      } else {
        payload[field.key] = raw.trim() === '' ? null : raw
      }
    }

    setFormError(null)
    setSubmitting(true)
    const request = editing ? update(editing.uuid, payload) : create(payload)
    request
      .then(() => {
        load()
        startCreate()
      })
      .catch((err: unknown) => {
        setFormError(err instanceof ApiError ? err.message : `Could not save this ${entityName.toLowerCase()}.`)
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-list">
        {loading && <p className="game-status">Loading…</p>}
        {error && <p className="game-status game-status-error">{error}</p>}
        {rows && (
          <table className="admin-table">
            <thead>
              <tr>
                {fields.map((f) => (
                  <th key={f.key}>{f.label}</th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.uuid} className={editing?.uuid === row.uuid ? 'admin-row-active' : ''}>
                  {fields.map((f) => (
                    <td key={f.key}>
                      {f.type === 'json'
                        ? JSON.stringify((row as unknown as Record<string, unknown>)[f.key] ?? null)
                        : String((row as unknown as Record<string, unknown>)[f.key] ?? '')}
                    </td>
                  ))}
                  <td>
                    <button type="button" className="btn" onClick={() => startEdit(row)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={fields.length + 1}>No {entityName.toLowerCase()} yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <form className="admin-form" onSubmit={handleSubmit}>
        <h3>{editing ? `Edit ${entityName.toLowerCase()}` : `New ${entityName.toLowerCase()}`}</h3>
        {fields.map((field) => (
          <label key={field.key} className="admin-form-field">
            {field.label}
            {field.type === 'text' ? (
              <input
                type="text"
                value={formValues[field.key] ?? ''}
                required={field.required}
                onChange={(e) => setFormValues((v) => ({ ...v, [field.key]: e.target.value }))}
              />
            ) : (
              <textarea
                rows={field.type === 'json' ? 6 : 3}
                value={formValues[field.key] ?? ''}
                required={field.required}
                onChange={(e) => setFormValues((v) => ({ ...v, [field.key]: e.target.value }))}
              />
            )}
          </label>
        ))}
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
