import { useCallback, useEffect, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { fetchNextImagePair, submitAnnotation } from '../api/annotationApi'
import { fetchDivesForRegion } from '../api/diveApi'
import type { Correspondence, ImagePair, NormalizedPoint, Region } from '../api/types'
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

export default function AnnotateGame({ region, onBack }: { region: Region; onBack: () => void }) {
  // undefined = still resolving a dive for this region; null = region has no dives yet.
  const [diveUuid, setDiveUuid] = useState<string | null | undefined>(undefined)
  const [pair, setPair] = useState<ImagePair | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [correspondences, setCorrespondences] = useState<Correspondence[]>([])
  const [pending, setPending] = useState<{ side: 'A' | 'B'; point: NormalizedPoint } | null>(null)
  const imageARef = useRef<HTMLImageElement>(null)
  const imageBRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    setDiveUuid(undefined)
    setLoading(true)
    setError(null)
    fetchDivesForRegion(region.uuid)
      .then((dives) => setDiveUuid(dives[0]?.uuid ?? null))
      .catch(() => setError('Could not load dive imagery for this region. Please try again.'))
  }, [region.uuid])

  const loadNextPair = useCallback((forDiveUuid: string) => {
    setLoading(true)
    setError(null)
    setCorrespondences([])
    setPending(null)
    fetchNextImagePair(forDiveUuid)
      .then((next) => {
        setPair(next)
        setDone(next === null)
      })
      .catch(() => setError('Could not load an image pair. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (diveUuid) {
      loadNextPair(diveUuid)
    } else if (diveUuid === null) {
      setLoading(false)
    }
  }, [diveUuid, loadNextPair])

  const handleClickImage = (side: 'A' | 'B') => (e: ReactMouseEvent<HTMLImageElement>) => {
    if (submitting) return
    const point = pointFromClick(e)

    if (pending && pending.side !== side) {
      const pointA = pending.side === 'A' ? pending.point : point
      const pointB = pending.side === 'B' ? pending.point : point
      setCorrespondences((prev) => [...prev, { pointA, pointB }])
      setPending(null)
      return
    }

    setPending({ side, point })
  }

  const handleUndo = () => {
    if (pending) {
      setPending(null)
      return
    }
    setCorrespondences((prev) => prev.slice(0, -1))
  }

  const handleClear = () => {
    setCorrespondences([])
    setPending(null)
  }

  const handleSubmit = () => {
    if (!pair || !diveUuid || correspondences.length < MIN_CORRESPONDENCES) return
    const imageA = imageARef.current
    const imageB = imageBRef.current
    if (!imageA || !imageB) return

    setSubmitting(true)
    setError(null)
    submitAnnotation(pair, correspondences, {
      widthA: imageA.naturalWidth,
      heightA: imageA.naturalHeight,
      widthB: imageB.naturalWidth,
      heightB: imageB.naturalHeight,
    })
      .then(() => loadNextPair(diveUuid))
      .catch(() => setError('Could not submit your annotation. Please try again.'))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>Yellow Eel League — Annotating</h1>
        <p className="game-flavor">
          For years, a yellow eel learns every rock and reed of its river home by heart.
        </p>
        <p>
          Click a point in either image, then click the same physical spot in the other image.
          Repeat for at least {MIN_CORRESPONDENCES} points, then submit.
        </p>
        <p className="game-region">Region: {region.title}</p>
      </header>

      {loading && <p className="game-status">Loading image pair…</p>}
      {error && <p className="game-status game-status-error">{error}</p>}
      {!loading && !error && diveUuid === null && (
        <p className="game-status">No dive imagery is available for this region yet.</p>
      )}
      {!loading && !error && diveUuid && done && (
        <p className="game-status">No more pairs to annotate in this region right now — nice work!</p>
      )}

      {pair && !loading && (
        <>
          <div className="image-pane-row">
            <div className="image-pane">
              <img
                ref={imageARef}
                src={pair.imageA}
                alt="Image A"
                onClick={handleClickImage('A')}
                className={`clickable${pending?.side === 'A' ? ' awaiting-match' : ''}`}
              />
              {correspondences.map((c, i) => (
                <Marker key={`a-${i}`} point={c.pointA} color={markerColor(i)} label={i + 1} />
              ))}
              {pending?.side === 'A' && (
                <div
                  className="marker marker-pending"
                  style={{ left: `${pending.point.x * 100}%`, top: `${pending.point.y * 100}%` }}
                >
                  {correspondences.length + 1}
                </div>
              )}
            </div>
            <div className="image-pane">
              <img
                ref={imageBRef}
                src={pair.imageB}
                alt="Image B"
                onClick={handleClickImage('B')}
                className={`clickable${pending?.side === 'B' ? ' awaiting-match' : ''}`}
              />
              {correspondences.map((c, i) => (
                <Marker key={`b-${i}`} point={c.pointB} color={markerColor(i)} label={i + 1} />
              ))}
              {pending?.side === 'B' && (
                <div
                  className="marker marker-pending"
                  style={{ left: `${pending.point.x * 100}%`, top: `${pending.point.y * 100}%` }}
                >
                  {correspondences.length + 1}
                </div>
              )}
            </div>
          </div>

          <p className="game-hint">
            {pending
              ? `Now click the matching point in the ${pending.side === 'A' ? 'right' : 'left'} image.`
              : 'Click a point in either image to start a new match.'}
          </p>

          <footer className="game-footer">
            <span className="game-count">
              {correspondences.length} point{correspondences.length === 1 ? '' : 's'} matched
            </span>
            <button
              type="button"
              className="btn"
              onClick={handleUndo}
              disabled={submitting || (correspondences.length === 0 && !pending)}
            >
              Undo
            </button>
            <button
              type="button"
              className="btn"
              onClick={handleClear}
              disabled={submitting || (correspondences.length === 0 && !pending)}
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
