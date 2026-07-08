/** Renders evenly-spaced grid lines over an `.image-pane`, tiling it into `size x size` cells. */
export function GridOverlay({ size }: { size: 2 | 3 }) {
  const offsets: number[] = []
  for (let i = 1; i < size; i++) {
    offsets.push((i / size) * 100)
  }

  return (
    <div className="grid-overlay">
      {offsets.map((pct) => (
        <div key={`v-${pct}`} className="grid-line grid-line-vertical" style={{ left: `${pct}%` }} />
      ))}
      {offsets.map((pct) => (
        <div key={`h-${pct}`} className="grid-line grid-line-horizontal" style={{ top: `${pct}%` }} />
      ))}
    </div>
  )
}
