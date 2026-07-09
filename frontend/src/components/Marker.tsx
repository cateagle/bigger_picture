import type { NormalizedPoint } from '../api/types'

export function Marker({
  point,
  color,
  label,
  status,
}: {
  point: NormalizedPoint
  color: string
  label: number
  /** When set, draws a colored ring around the marker to show its review decision. */
  status?: 'approved' | 'flagged'
}) {
  return (
    <div
      className={`marker${status ? ` marker-${status}` : ''}`}
      style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%`, backgroundColor: color }}
    >
      {label}
    </div>
  )
}
