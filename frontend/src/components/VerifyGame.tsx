import { useCallback, useEffect, useState } from 'react'
import { fetchDivesForRegion } from '../api/diveApi'
import { fetchNextPendingVerification, submitVerification } from '../api/verifyApi'
import type { PendingVerification, Region } from '../api/types'
import { Marker } from './Marker'
import { markerColor } from './markerColor'

export default function VerifyGame({ region, onBack }: { region: Region; onBack: () => void }) {
  // undefined = still resolving a dive for this region; null = region has no dives yet.
  const [diveUuid, setDiveUuid] = useState<string | null | undefined>(undefined)
  const [item, setItem] = useState<PendingVerification | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reviewedCount, setReviewedCount] = useState(0)

  useEffect(() => {
    setDiveUuid(undefined)
    setLoading(true)
    setError(null)
    fetchDivesForRegion(region.uuid)
      .then((dives) => setDiveUuid(dives[0]?.uuid ?? null))
      .catch(() => setError('Could not load dive imagery for this region. Please try again.'))
  }, [region.uuid])

  const loadNext = useCallback((forDiveUuid: string) => {
    setLoading(true)
    setError(null)
    fetchNextPendingVerification(forDiveUuid)
      .then((next) => {
        setItem(next)
        setDone(next === null)
      })
      .catch(() => setError('Could not load an annotation to review. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (diveUuid) {
      loadNext(diveUuid)
    } else if (diveUuid === null) {
      setLoading(false)
    }
  }, [diveUuid, loadNext])

  const handleDecision = (approved: boolean) => {
    if (!item || !diveUuid || submitting) return
    setSubmitting(true)
    setError(null)
    submitVerification(item, approved)
      .then(() => {
        setReviewedCount((count) => count + 1)
        loadNext(diveUuid)
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
        <p className="game-region">Region: {region.title}</p>
      </header>

      {loading && <p className="game-status">Loading annotation…</p>}
      {error && <p className="game-status game-status-error">{error}</p>}
      {!loading && !error && diveUuid === null && (
        <p className="game-status">No dive imagery is available for this region yet.</p>
      )}
      {!loading && !error && diveUuid && done && (
        <p className="game-status">Nothing left to review in this region right now — nice work!</p>
      )}

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
