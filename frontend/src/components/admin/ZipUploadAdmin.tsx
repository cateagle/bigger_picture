import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { ApiError } from '../../api/client'
import { uploadDatasetZip } from '../../api/datasetApi'
import type { DatasetImportCounts } from '../../api/datasetApi'
import '../admin/AdminPanels.css'

export default function ZipUploadAdmin() {
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DatasetImportCounts | null>(null)

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
    setError(null)
    setResult(null)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!file || submitting) return
    setSubmitting(true)
    setError(null)
    setResult(null)
    uploadDatasetZip(file)
      .then((created) => {
        setResult(created)
        setFile(null)
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not upload this zip file.')
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <form className="admin-form" onSubmit={handleSubmit}>
      <h3>Bulk import from zip</h3>

      <p className="zip-upload-description">
        Upload a zip archive containing up to 7 optional, semicolon-delimited CSVs (labels.csv,
        cameras.csv, regions.csv, dives.csv, images.csv, candidates.csv, pairs.csv) plus an
        images/ folder, and import them in dependency order. Requires the scientist role.
      </p>
      <p className="zip-upload-description">
        The whole import is all-or-nothing: any error aborts with nothing persisted and no asset
        files left behind. On success, returns per-entity created counts - newly minted uuids
        (from rows using uuid "new") are never echoed back, so reference such rows by title in
        later rows of the same import.
      </p>
      <p className="zip-upload-description">
        Fails with 422 identifying the offending file and row if any CSV row is invalid,
        references a nonexistent entity, or if the zip is malformed or contains an unsafe path.
      </p>

      <label className="admin-form-field">
        Zip file
        <input type="file" accept=".zip,application/zip" onChange={handleFileChange} />
      </label>

      {error && <p className="game-status game-status-error">{error}</p>}
      {result && (
        <p className="game-status">
          Imported {result.labels} label(s), {result.cameras} camera(s), {result.regions} region(s),{' '}
          {result.dives} dive(s), {result.images} image(s), {result.candidate_pairs} candidate
          pair(s), {result.image_pairs} image pair(s).
        </p>
      )}

      <div className="admin-form-actions">
        <button type="submit" className="btn btn-primary" disabled={!file || submitting}>
          {submitting ? 'Uploading…' : 'Upload'}
        </button>
      </div>
    </form>
  )
}
