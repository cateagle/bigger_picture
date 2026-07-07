import { useCallback, useEffect, useState } from 'react'
import { fetchPendingVerification, submitVerification } from '../api/verifyApi'
import type { PendingVerification } from '../api/types'
import { Marker } from './Marker'
import { markerColor } from './markerColor'

export default function VerifyGame({ onBack }: { onBack: () => void }) {
  const [item, setItem] = useState<PendingVerification | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reviewedCount, setReviewedCount] = useState(0)

  const loadNext = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchPendingVerification()
      .then(setItem)
      .catch(() => setError('Could not load an annotation to review. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadNext()
  }, [loadNext])

  const handleDecision = (approved: boolean) => {
    if (!item || submitting) return
    setSubmitting(true)
    setError(null)
    submitVerification(item.annotationId, approved)
      .then(() => {
        setReviewedCount((count) => count + 1)
        loadNext()
      })
      .catch(() => setError('Could not submit your review. Please try again.'))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>Silver Eel League — Verification</h1>
        <p className="game-flavor">
          Before the long migration back to sea, a silver eel double-checks its bearings.
        </p>
        <p>
          Review the numbered points below - does each pair mark the same physical spot in both
          images? Flag it if any point looks wrong.
        </p>
      </header>

      {loading && <p className="game-status">Loading annotation…</p>}
      {error && <p className="game-status game-status-error">{error}</p>}

      {item && !loading && (
        <>
          <div className="image-pane-row">
            <div className="image-pane">
              <img src={item.imageA} alt="Annotated image A" />
              {item.correspondences.map((c, i) => (
                <Marker key={`a-${i}`} point={c.pointA} color={markerColor(i)} label={i + 1} />
              ))}
            </div>
            <div className="image-pane">
              <img src={item.imageB} alt="Annotated image B" />
              {item.correspondences.map((c, i) => (
                <Marker key={`b-${i}`} point={c.pointB} color={markerColor(i)} label={i + 1} />
              ))}
            </div>
          </div>

          <p className="game-hint">
            {item.correspondences.length} point{item.correspondences.length === 1 ? '' : 's'} marked
          </p>

          <footer className="game-footer">
            <span className="game-count">{reviewedCount} reviewed</span>
            <button type="button" className="btn" onClick={() => handleDecision(false)} disabled={submitting}>
              Flag
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleDecision(true)}
              disabled={submitting}
            >
              Approve
            </button>
          </footer>
        </>
      )}
    </div>
  )
}
