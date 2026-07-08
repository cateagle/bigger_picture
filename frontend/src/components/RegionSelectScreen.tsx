import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Globe from 'react-globe.gl'
import { fetchRegions } from '../api/regionApi'
import type { Region, RegionMesh, User } from '../api/types'
import './RegionSelectScreen.css'

const CAP_COLOR = 'rgba(42, 120, 214, 0.55)'
const CAP_COLOR_HOVER = 'rgba(233, 168, 47, 0.75)'
const STROKE_COLOR = 'rgba(255, 255, 255, 0.85)'

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

function normalizeMeshWinding(mesh: RegionMesh): RegionMesh {
  if (mesh.type === 'Polygon') {
    return { ...mesh, coordinates: normalizeRingWinding(mesh.coordinates as number[][][]) }
  }
  return {
    ...mesh,
    coordinates: (mesh.coordinates as number[][][][]).map((polygon) => normalizeRingWinding(polygon)),
  }
}

/**
 * The observed element mounts only once region data has loaded (an async,
 * conditionally-rendered container), so a plain object ref + mount-time
 * effect would miss it - the effect runs before the element exists. A
 * callback ref re-fires whenever the node itself mounts/unmounts instead.
 */
function useContainerSize() {
  const [size, setSize] = useState({ width: 0, height: 0 })
  const observerRef = useRef<ResizeObserver | null>(null)

  const ref = useCallback((el: HTMLDivElement | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    observerRef.current = observer
  }, [])

  return { ref, size }
}

export default function RegionSelectScreen({
  user,
  onSelect,
  onOpenAdmin,
  onOpenTeam,
  onLogout,
}: {
  user: User
  onSelect: (region: Region) => void
  onOpenAdmin: () => void
  onOpenTeam: () => void
  onLogout: () => void
}) {
  const [regions, setRegions] = useState<Region[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hovered, setHovered] = useState<Region | null>(null)
  const { ref: globeContainerRef, size: globeSize } = useContainerSize()

  useEffect(() => {
    fetchRegions()
      .then(setRegions)
      .catch(() => setError('Could not load regions. Please try again.'))
  }, [])

  const meshedRegions = useMemo(
    () =>
      (regions ?? [])
        .filter((r): r is Region & { metadata: { mesh: RegionMesh } } => !!r.metadata?.mesh)
        .map((r) => ({ ...r, metadata: { ...r.metadata, mesh: normalizeMeshWinding(r.metadata.mesh) } })),
    [regions],
  )

  return (
    <div className="region-select-screen">
      <div className="account-bar">
        <span>
          Signed in as <strong>{user.username}</strong>
        </span>
        {user.role !== 'annotator' && (
          <button type="button" className="back-link" onClick={onOpenAdmin}>
            Admin
          </button>
        )}
        <button type="button" className="back-link" onClick={onOpenTeam}>
          Team
        </button>
        <button type="button" className="back-link" onClick={onLogout}>
          Log out
        </button>
      </div>

      <header className="region-select-header">
        <p className="region-select-eyebrow">Journey of the Eel</p>
        <h1>Choose a region</h1>
        <p>Every region holds its own set of dive imagery. Spin the globe and pick a highlighted area, or choose from the list below.</p>
      </header>

      {error && <p className="game-status game-status-error">{error}</p>}
      {!error && regions === null && <p className="game-status">Loading regions…</p>}

      {regions !== null && (
        <>
          <div className="region-globe-container" ref={globeContainerRef}>
            {globeSize.width > 0 && (
              <Globe
                width={globeSize.width}
                height={globeSize.height}
                globeImageUrl="/globe/earth-blue-marble.jpg"
                backgroundImageUrl="/globe/night-sky.png"
                polygonsData={meshedRegions}
                // react-globe.gl's bundled GeoJsonGeometry type declares `coordinates: number[]`,
                // which is too narrow for real Polygon/MultiPolygon geometry (nested arrays).
                polygonGeoJsonGeometry={(r) =>
                  (r as (typeof meshedRegions)[number]).metadata.mesh as unknown as { type: string; coordinates: number[] }
                }
                polygonCapColor={(r) => ((r as Region) === hovered ? CAP_COLOR_HOVER : CAP_COLOR)}
                polygonSideColor={() => 'rgba(42, 120, 214, 0.25)'}
                polygonStrokeColor={() => STROKE_COLOR}
                polygonAltitude={(r) => ((r as Region) === hovered ? 0.02 : 0.008)}
                polygonLabel={(r) => (r as Region).title}
                onPolygonHover={(r) => setHovered(r as Region | null)}
                onPolygonClick={(r) => onSelect(r as Region)}
              />
            )}
          </div>

          <div className="region-list">
            {regions.length === 0 && <p className="game-status">No regions have been added yet.</p>}
            {regions.map((region) => (
              <button
                type="button"
                key={region.uuid}
                className="btn region-list-item"
                onClick={() => onSelect(region)}
              >
                {region.title}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
