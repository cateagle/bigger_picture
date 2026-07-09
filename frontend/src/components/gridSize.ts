export type GridSize = 0 | 2 | 3

/** Cycles Off -> 2x2 -> 3x3 -> Off. */
export function nextGridSize(size: GridSize): GridSize {
  if (size === 0) return 2
  if (size === 2) return 3
  return 0
}

export function gridToggleLabel(size: GridSize): string {
  return size === 0 ? 'Grid: Off' : `Grid: ${size}×${size}`
}
