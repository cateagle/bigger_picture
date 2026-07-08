import type { RegionMesh } from './api/types'

function ringSignedArea(ring: number[][]): number {
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i]
    const [x2, y2] = ring[i + 1]
    sum += x1 * y2 - x2 * y1
  }
  return sum
}

/**
 * three-globe/d3-geo renders a polygon's *complement* (the whole globe minus
 * the intended area) unless the exterior ring winds clockwise in (lng, lat)
 * order - the opposite of the GeoJSON RFC 7946 convention that most
 * authoring tools (geojson.io, Turf, GIS exports) produce by default. Force
 * the orientation here rather than relying on however a region's mesh
 * happened to be authored; holes (rings after the first) must wind the
 * opposite way from the exterior ring to still read as holes.
 */
function normalizeRingWinding(rings: number[][][]): number[][][] {
  return rings.map((ring, i) => {
    const isExterior = i === 0
    const isClockwise = ringSignedArea(ring) < 0
    const needsReversal = isExterior ? !isClockwise : isClockwise
    return needsReversal ? [...ring].reverse() : ring
  })
}

/** Normalizes a `RegionMesh`'s ring winding for correct rendering by `react-globe.gl` (see `normalizeRingWinding`). */
export function normalizeMeshWinding(mesh: RegionMesh): RegionMesh {
  if (mesh.type === 'Polygon') {
    return { ...mesh, coordinates: normalizeRingWinding(mesh.coordinates as number[][][]) }
  }
  return {
    ...mesh,
    coordinates: (mesh.coordinates as number[][][][]).map((polygon) => normalizeRingWinding(polygon)),
  }
}
