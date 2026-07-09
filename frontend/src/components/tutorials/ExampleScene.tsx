import type { NormalizedPoint } from '../../api/types'

/**
 * A demonstration point drawn over an example scene. `good` points are the
 * kind of feature to mark (rock edge, coral tip, bolt); `bad` points are the
 * kind to avoid (fish, divers, bubbles). `label` is an optional caption.
 */
export interface ExamplePoint {
  point: NormalizedPoint
  kind: 'good' | 'bad'
  label?: string
}

/** Which placeholder reef rendering to use; swapped for real photos later. */
export type SceneVariant = 'angled' | 'different'

/** A scene's backdrop (real photo or placeholder) plus its demonstration points. */
export interface SceneContent {
  image?: string
  points?: ExamplePoint[]
}

/**
 * Draws a tutorial step's example imagery with its demonstration points on top.
 * When `scene.image` is set it shows that photo; otherwise it renders a
 * stylized placeholder reef so the tutorial is self-contained until real
 * example imagery is supplied. Points are positioned in the image's normalized
 * [0,1] space, mirroring {@link Marker}.
 */
export function ExampleScene({ scene }: { scene: SceneContent }) {
  return (
    <div className="tut-scene">
      <SceneBackground image={scene.image} />
      {scene.points?.map((p, i) => (
        <div
          key={i}
          className={`tut-point tut-point-${p.kind}`}
          style={{ left: `${p.point.x * 100}%`, top: `${p.point.y * 100}%` }}
        >
          <span className="tut-point-dot" aria-hidden="true">
            {p.kind === 'bad' ? '✕' : '✓'}
          </span>
          {p.label && <span className="tut-point-label">{p.label}</span>}
        </div>
      ))}
    </div>
  )
}

/**
 * Renders a scene's backdrop only (no point overlay) — either the real photo
 * or the placeholder reef. `variant` lets a placeholder stand in for a second,
 * visually distinct example (e.g. "the same place from another angle") until
 * real photo pairs are available.
 */
export function SceneBackground({ image, variant }: { image?: string; variant?: SceneVariant }) {
  return image ? <img className="tut-scene-img" src={image} alt="" /> : <PlaceholderReef variant={variant} />
}

/** A simple, themeable underwater scene used as placeholder example art. */
function PlaceholderReef({ variant }: { variant?: SceneVariant }) {
  return (
    <svg
      className={`tut-scene-svg${variant ? ` tut-scene-svg-${variant}` : ''}`}
      viewBox="0 0 100 60"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="Illustrated underwater scene"
    >
      <defs>
        <linearGradient id="tut-water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2a6f86" />
          <stop offset="100%" stopColor="#123a4a" />
        </linearGradient>
      </defs>
      <rect width="100" height="60" fill="url(#tut-water)" />
      {/* seabed */}
      <path d="M0 52 Q25 46 50 51 T100 50 V60 H0 Z" fill="#4a3b2a" opacity="0.9" />
      {/* rock */}
      <path d="M16 52 Q20 38 30 40 Q40 42 38 52 Z" fill="#5b5750" />
      {/* coral heads */}
      <path d="M60 52 Q60 40 64 40 Q68 40 68 52 Z" fill="#b7563f" />
      <path d="M67 52 Q67 44 71 44 Q75 44 74 52 Z" fill="#c9704f" />
      {/* fish */}
      <g fill="#e0c05a">
        <ellipse cx="55" cy="20" rx="5" ry="2.4" />
        <path d="M60 20 l4 -2.5 v5 Z" />
      </g>
      {/* bubbles */}
      <g fill="#ffffff" opacity="0.5">
        <circle cx="80" cy="14" r="1.6" />
        <circle cx="83" cy="9" r="1.1" />
        <circle cx="78" cy="7" r="0.8" />
      </g>
    </svg>
  )
}
