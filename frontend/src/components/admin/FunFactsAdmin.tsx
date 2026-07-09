import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { ApiError, assetUrl } from '../../api/client'
import { createFunFact, fetchFunFacts, updateFunFact } from '../../api/funFactApi'
import { fetchRegions } from '../../api/regionApi'
import type { FunFact, Region } from '../../api/types'
import '../admin/AdminPanels.css'
import './FunFactsAdmin.css'

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.slice(result.indexOf(',') + 1))
    }
    reader.onerror = () => reject(reader.error ?? new Error('Could not read file'))
    reader.readAsDataURL(file)
  })
}

export default function FunFactsAdmin() {
  const [facts, setFacts] = useState<FunFact[] | null>(null)
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editing, setEditing] = useState<FunFact | null>(null)
  const [title, setTitle] = useState('')
  const [factJson, setFactJson] = useState('')
  const [regionUuid, setRegionUuid] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [removeImage, setRemoveImage] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchFunFacts()
      .then(setFacts)
      .catch(() => setError('Could not load facts.'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  useEffect(() => {
    fetchRegions()
      .then(setRegions)
      .catch(() => setError('Could not load regions.'))
  }, [])

  const regionTitle = (regionUuidValue: string | null) => {
    if (!regionUuidValue) return '—'
    return regions?.find((r) => r.uuid === regionUuidValue)?.title ?? regionUuidValue
  }

  const startCreate = () => {
    setEditing(null)
    setTitle('')
    setFactJson('')
    setRegionUuid('')
    setImageFile(null)
    setRemoveImage(false)
    setFormError(null)
  }

  const startEdit = (fact: FunFact) => {
    setEditing(fact)
    setTitle(fact.title)
    setFactJson(JSON.stringify(fact.fact, null, 2))
    setRegionUuid(fact.region ?? '')
    setImageFile(null)
    setRemoveImage(false)
    setFormError(null)
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setImageFile(file)
    if (file) setRemoveImage(false)
  }

  const handleRemoveImageChange = (e: ChangeEvent<HTMLInputElement>) => {
    setRemoveImage(e.target.checked)
    if (e.target.checked) setImageFile(null)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (submitting) return

    let factValue: unknown
    try {
      factValue = JSON.parse(factJson)
    } catch {
      setFormError('Fact must be valid JSON.')
      return
    }

    setFormError(null)
    setSubmitting(true)

    const region = regionUuid === '' ? null : regionUuid

    const run = async () => {
      const imagePayload = imageFile
        ? { image: await fileToBase64(imageFile), image_filename: imageFile.name }
        : {}

      if (editing) {
        await updateFunFact(editing.uuid, {
          title,
          fact: factValue,
          region,
          ...(removeImage ? { clear_image: true } : imagePayload),
        })
      } else {
        await createFunFact({ title, fact: factValue, region, ...imagePayload })
      }
    }

    run()
      .then(() => {
        load()
        startCreate()
      })
      .catch((err: unknown) => {
        setFormError(err instanceof ApiError ? err.message : 'Could not save this fact.')
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="admin-panel">
      <div className="admin-panel-list">
        {loading && <p className="game-status">Loading…</p>}
        {error && <p className="game-status game-status-error">{error}</p>}
        {facts && (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Title</th>
                <th>Fact</th>
                <th>Region</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {facts.map((fact) => (
                <tr key={fact.uuid} className={editing?.uuid === fact.uuid ? 'admin-row-active' : ''}>
                  <td>
                    {fact.image && (
                      <img
                        src={assetUrl(fact.image.filepath)}
                        alt={fact.image.filename}
                        className="fun-facts-admin-thumb"
                      />
                    )}
                  </td>
                  <td>{fact.title}</td>
                  <td>{JSON.stringify(fact.fact)}</td>
                  <td>{regionTitle(fact.region)}</td>
                  <td>
                    <button type="button" className="btn" onClick={() => startEdit(fact)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {facts.length === 0 && (
                <tr>
                  <td colSpan={5}>No facts yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <form className="admin-form" onSubmit={handleSubmit}>
        <h3>{editing ? 'Edit fact' : 'New fact'}</h3>

        <label className="admin-form-field">
          Title
          <input type="text" value={title} required onChange={(e) => setTitle(e.target.value)} />
        </label>

        <label className="admin-form-field">
          Fact (JSON)
          <textarea rows={6} value={factJson} required onChange={(e) => setFactJson(e.target.value)} />
        </label>

        <label className="admin-form-field">
          Region
          <select value={regionUuid} onChange={(e) => setRegionUuid(e.target.value)}>
            <option value="">No region (all regions)</option>
            {(regions ?? []).map((region) => (
              <option key={region.uuid} value={region.uuid}>
                {region.title}
              </option>
            ))}
          </select>
        </label>

        {editing?.image && !removeImage && (
          <img
            src={assetUrl(editing.image.filepath)}
            alt={editing.image.filename}
            className="fun-facts-admin-thumb"
          />
        )}

        <label className="admin-form-field">
          {editing ? 'Replace image (optional)' : 'Image (optional)'}
          <input
            type="file"
            key={editing?.uuid ?? 'new'}
            accept="image/*"
            onChange={handleFileChange}
            disabled={removeImage}
          />
        </label>

        {editing?.image && (
          <label className="admin-form-field-inline">
            <input type="checkbox" checked={removeImage} onChange={handleRemoveImageChange} />
            Remove current image
          </label>
        )}

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
