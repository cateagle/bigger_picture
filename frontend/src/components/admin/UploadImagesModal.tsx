import { useState } from 'react'
import type { ChangeEvent } from 'react'
import { createImage } from '../../api/datasetApi'
import { ApiError } from '../../api/client'
import './AdminPanels.css'
import './CreateStrideCandidatePairsModal.css'

export default function UploadImagesModal({
  diveUuid,
  onCancel,
  onUploaded,
}: {
  diveUuid: string
  onCancel: () => void
  onUploaded: (uploadedCount: number) => void
}) {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [formError, setFormError] = useState<string | null>(null)

  const handleFilesChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFiles(Array.from(e.target.files ?? []))
  }

  const handleUpload = async () => {
    if (uploading || files.length === 0) return
    setFormError(null)
    setUploading(true)
    setProgress(0)

    let uploadedCount = 0
    for (const file of files) {
      try {
        await createImage(diveUuid, file)
        uploadedCount += 1
        setProgress(uploadedCount)
      } catch (err: unknown) {
        setFormError(
          `Uploaded ${uploadedCount} of ${files.length} images before failing on "${file.name}": ${
            err instanceof ApiError ? err.message : 'Could not upload image.'
          }`,
        )
        setUploading(false)
        onUploaded(uploadedCount)
        return
      }
    }

    setUploading(false)
    onUploaded(uploadedCount)
  }

  return (
    <div className="stride-modal-backdrop" onClick={uploading ? undefined : onCancel}>
      <div
        className="stride-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-images-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="admin-form">
          <h3 id="upload-images-modal-title">Upload images</h3>
          <p className="game-status">Each uploaded image is assigned a random uuid; the original filename is kept for display only.</p>
          <label className="admin-form-field">
            Select images
            <input type="file" accept="image/*" multiple disabled={uploading} onChange={handleFilesChange} />
          </label>
          {files.length > 0 && (
            <p className="game-status">
              {uploading ? `Uploading ${progress} of ${files.length}…` : `${files.length} image(s) selected.`}
            </p>
          )}
          {formError && <p className="game-status game-status-error">{formError}</p>}
          <div className="admin-form-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading || files.length === 0}
            >
              {uploading ? 'Uploading…' : 'Upload'}
            </button>
            <button type="button" className="btn" onClick={onCancel} disabled={uploading}>
              {uploading ? 'Close' : 'Cancel'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
