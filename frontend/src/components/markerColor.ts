// Fixed categorical order (never re-sorted/cycled by rank) so a given
// correspondence keeps its color for its whole lifetime on screen.
const MARKER_COLORS = [
  '#2a78d6', // blue
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
  '#e87ba4', // magenta
  '#eb6834', // orange
]

export function markerColor(index: number): string {
  return MARKER_COLORS[index % MARKER_COLORS.length]
}
