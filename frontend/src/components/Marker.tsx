import type { NormalizedPoint } from '../api/types'

export function Marker({ point, color, label }: { point: NormalizedPoint; color: string; label: number }) {
  return (
    <div
      className="marker"
      style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%`, backgroundColor: color }}
    >
      {label}
    </div>
  )
}
