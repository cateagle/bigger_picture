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

/** Collects the exterior-ring vertices of a mesh (the outer ring of every polygon). */
function outerRingVertices(mesh: RegionMesh): number[][] {
  if (mesh.type === 'Polygon') {
    return (mesh.coordinates as number[][][])[0] ?? []
  }
  return (mesh.coordinates as number[][][][]).flatMap((polygon) => polygon[0] ?? [])
}

/**
 * Bounding-box centre of a region mesh plus its angular `span` (the larger of
 * its latitude/longitude extents, in degrees). Used to drop a beacon at a
 * region's location and to tell small regions (tiny `span`) apart from large
 * ones. The centre is stable and always sits within the region's extent, which
 * is all a beacon needs — no need for a true area-weighted centroid.
 */
export function meshCentroid(mesh: RegionMesh): { lat: number; lng: number; span: number } {
  const vertices = outerRingVertices(mesh)
  let minLng = Infinity
  let maxLng = -Infinity
  let minLat = Infinity
  let maxLat = -Infinity
  for (const [lng, lat] of vertices) {
    if (lng < minLng) minLng = lng
    if (lng > maxLng) maxLng = lng
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  }
  return {
    lat: (minLat + maxLat) / 2,
    lng: (minLng + maxLng) / 2,
    span: Math.max(maxLat - minLat, maxLng - minLng),
  }
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
