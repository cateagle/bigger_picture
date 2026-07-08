import type { NormalizedPoint } from '../api/types'

export function Marker({
  point,
  color,
  label,
  reviewed = false,
}: {
  point: NormalizedPoint
  color: string
  label: number
  reviewed?: boolean
}) {
  return (
    <div
      className={reviewed ? 'marker marker-reviewed' : 'marker'}
      style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%`, backgroundColor: color }}
    >
      {label}
    </div>
  )
}
