import { useEffect, useMemo, useState } from 'react'
import Globe from 'react-globe.gl'
import { fetchRegions } from '../api/regionApi'
import type { Region, RegionMesh, User } from '../api/types'
import { normalizeMeshWinding } from '../geo'
import { useContainerSize } from '../useContainerSize'
import { LevelBadge } from './LevelBadge'
import './RegionSelectScreen.css'

const CAP_COLOR = 'rgba(42, 120, 214, 0.55)'
const CAP_COLOR_HOVER = 'rgba(233, 168, 47, 0.75)'
const STROKE_COLOR = 'rgba(255, 255, 255, 0.85)'

export default function RegionSelectScreen({
  user,
  onSelect,
  onOpenAdmin,
  onOpenTeam,
  onOpenStats,
  onOpenQuests,
  onLogout,
}: {
  user: User
  onSelect: (region: Region) => void
  onOpenAdmin: () => void
  onOpenTeam: () => void
  onOpenStats: () => void
  onOpenQuests: () => void
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
        <LevelBadge exp={user.exp} />
        {user.role !== 'annotator' && (
          <button type="button" className="back-link" onClick={onOpenAdmin}>
            Admin
          </button>
        )}
        <button type="button" className="back-link" onClick={onOpenStats}>
          My Stats
        </button>
        <button type="button" className="back-link" onClick={onOpenQuests}>
          Daily Quests
        </button>
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
