import { useCallback, useEffect, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { fetchImagePair, submitAnnotation } from '../api/annotationApi'
import type { Correspondence, ImagePair, NormalizedPoint } from '../api/types'
import { Marker } from './Marker'
import { markerColor } from './markerColor'
import './AnnotateGame.css'

const MIN_CORRESPONDENCES = 4

function pointFromClick(e: ReactMouseEvent<HTMLImageElement>): NormalizedPoint {
  const rect = e.currentTarget.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width
  const y = (e.clientY - rect.top) / rect.height
  return {
    x: Math.min(1, Math.max(0, x)),
    y: Math.min(1, Math.max(0, y)),
  }
}

export default function AnnotateGame({ onBack }: { onBack: () => void }) {
  const [pair, setPair] = useState<ImagePair | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [correspondences, setCorrespondences] = useState<Correspondence[]>([])
  const [pendingA, setPendingA] = useState<NormalizedPoint | null>(null)

  const loadNextPair = useCallback(() => {
    setLoading(true)
    setError(null)
    setCorrespondences([])
    setPendingA(null)
    fetchImagePair()
      .then(setPair)
      .catch(() => setError('Could not load an image pair. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadNextPair()
  }, [loadNextPair])

  const handleClickA = (e: ReactMouseEvent<HTMLImageElement>) => {
    if (submitting) return
    setPendingA(pointFromClick(e))
  }

  const handleClickB = (e: ReactMouseEvent<HTMLImageElement>) => {
    if (submitting || !pendingA) return
    const pointB = pointFromClick(e)
    setCorrespondences((prev) => [...prev, { pointA: pendingA, pointB }])
    setPendingA(null)
  }

  const handleUndo = () => {
    if (pendingA) {
      setPendingA(null)
      return
    }
    setCorrespondences((prev) => prev.slice(0, -1))
  }

  const handleClear = () => {
    setCorrespondences([])
    setPendingA(null)
  }

  const handleSubmit = () => {
    if (!pair || correspondences.length < MIN_CORRESPONDENCES) return
    setSubmitting(true)
    setError(null)
    submitAnnotation(pair.pairId, correspondences)
      .then(() => loadNextPair())
      .catch(() => setError('Could not submit your annotation. Please try again.'))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>Stage 2 — Annotating</h1>
        <p>
          Click a point in the left image, then click the same physical spot in the right image.
          Repeat for at least {MIN_CORRESPONDENCES} points, then submit.
        </p>
      </header>

      {loading && <p className="game-status">Loading image pair…</p>}
      {error && <p className="game-status game-status-error">{error}</p>}

      {pair && !loading && (
        <>
          <div className="image-pane-row">
            <div className="image-pane">
              <img
                src={pair.imageA}
                alt="Image A"
                onClick={handleClickA}
                className={`clickable${pendingA ? ' awaiting-match' : ''}`}
              />
              {correspondences.map((c, i) => (
                <Marker key={`a-${i}`} point={c.pointA} color={markerColor(i)} label={i + 1} />
              ))}
              {pendingA && (
                <div
                  className="marker marker-pending"
                  style={{ left: `${pendingA.x * 100}%`, top: `${pendingA.y * 100}%` }}
                >
                  {correspondences.length + 1}
                </div>
              )}
            </div>
            <div className="image-pane">
              <img src={pair.imageB} alt="Image B" onClick={handleClickB} className="clickable" />
              {correspondences.map((c, i) => (
                <Marker key={`b-${i}`} point={c.pointB} color={markerColor(i)} label={i + 1} />
              ))}
            </div>
          </div>

          <p className="game-hint">
            {pendingA
              ? 'Now click the matching point in the right image.'
              : 'Click a point in the left image to start a new match.'}
          </p>

          <footer className="game-footer">
            <span className="game-count">
              {correspondences.length} point{correspondences.length === 1 ? '' : 's'} matched
            </span>
            <button
              type="button"
              className="btn"
              onClick={handleUndo}
              disabled={submitting || (correspondences.length === 0 && !pendingA)}
            >
              Undo
            </button>
            <button
              type="button"
              className="btn"
              onClick={handleClear}
              disabled={submitting || (correspondences.length === 0 && !pendingA)}
            >
              Clear
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting || correspondences.length < MIN_CORRESPONDENCES}
            >
              {submitting ? 'Submitting…' : `Submit & next pair`}
            </button>
          </footer>
        </>
      )}
    </div>
  )
}
