import { useCallback, useEffect, useState } from 'react'
import { fetchCandidatePair, submitOverlapDecision } from '../api/overlapApi'
import type { CandidatePair } from '../api/types'

export default function OverlapGame({ onBack }: { onBack: () => void }) {
  const [pair, setPair] = useState<CandidatePair | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reviewedCount, setReviewedCount] = useState(0)

  const loadNextPair = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchCandidatePair()
      .then(setPair)
      .catch(() => setError('Could not load an image pair. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadNextPair()
  }, [loadNextPair])

  const handleDecision = (overlaps: boolean) => {
    if (!pair || submitting) return
    setSubmitting(true)
    setError(null)
    submitOverlapDecision(pair, overlaps)
      .then(() => {
        setReviewedCount((count) => count + 1)
        loadNextPair()
      })
      .catch(() => setError('Could not submit your answer. Please try again.'))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>Glass Eel League — Finding Overlap</h1>
        <p className="game-flavor">
          A glass eel drifts in from the open ocean, scanning the coastline for familiar water.
        </p>
        <p>Look at both images below and decide whether they show the same physical scene.</p>
      </header>

      {loading && <p className="game-status">Loading image pair…</p>}
      {error && <p className="game-status game-status-error">{error}</p>}

      {pair && !loading && (
        <>
          <div className="image-pane-row">
            <div className="image-pane">
              <img src={pair.imageA} alt="Candidate scene A" />
            </div>
            <div className="image-pane">
              <img src={pair.imageB} alt="Candidate scene B" />
            </div>
          </div>

          <footer className="game-footer">
            <span className="game-count">
              {reviewedCount} pair{reviewedCount === 1 ? '' : 's'} reviewed
            </span>
            <button type="button" className="btn" onClick={() => handleDecision(false)} disabled={submitting}>
              Different scene
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleDecision(true)}
              disabled={submitting}
            >
              Same scene
            </button>
          </footer>
        </>
      )}
    </div>
  )
}
