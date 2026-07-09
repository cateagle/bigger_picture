import { useEffect, useReducer } from 'react'
import type { RefObject } from 'react'
import type { NormalizedPoint } from '../api/types'
import './ZoomLens.css'

type Props = {
  imageRef: RefObject<HTMLImageElement | null>
  point: NormalizedPoint | null
  cursor?: { x: number; y: number } | null
  zoom?: number
  // When true, the lens stays centered on `point` instead of following the cursor.
  pinned?: boolean
}

const SIZE = 160

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

export function ZoomLens({ imageRef, point, cursor, zoom = 4, pinned = false }: Props) {
  // A pinned lens is positioned from the image's on-screen rect, so it must
  // re-render when the page scrolls or resizes to stay over its point.
  const [, forceUpdate] = useReducer((n) => n + 1, 0)
  useEffect(() => {
    if (!pinned) return
    window.addEventListener('scroll', forceUpdate, true)
    window.addEventListener('resize', forceUpdate)
    return () => {
      window.removeEventListener('scroll', forceUpdate, true)
      window.removeEventListener('resize', forceUpdate)
    }
  }, [pinned])

  const image = imageRef.current

  if (!image || !point) return null
  if (!pinned && !cursor) return null

  const rect = image.getBoundingClientRect()

  // Point position in on-screen image pixels.
  const x = point.x * rect.width
  const y = point.y * rect.height

  let left: number
  let top: number
  if (pinned) {
    // Sit the lens directly over the selected point, clamped to the viewport.
    left = clamp(rect.left + x - SIZE / 2, 8, window.innerWidth - SIZE - 8)
    top = clamp(rect.top + y - SIZE / 2, 8, window.innerHeight - SIZE - 8)
  } else {
    left = cursor!.x + 20
    top = cursor!.y + 20
  }

  return (
    <div
      className={`zoom-lens${pinned ? ' zoom-lens-pinned' : ''}`}
      style={{
        left,
        top,
        backgroundImage: `url(${image.src})`,
        backgroundSize: `${rect.width * zoom}px ${rect.height * zoom}px`,
        backgroundPosition: `${SIZE / 2 - x * zoom}px ${SIZE / 2 - y * zoom}px`,
      }}
    />
  )
}
