import { useEffect, useState } from 'react'
import { fetchNextImagePair } from '../api/annotationApi'
import { fetchDivesForRegion } from '../api/diveApi'
import { fetchNextCandidatePair } from '../api/overlapApi'
import type { Region, User } from '../api/types'
import { fetchNextPendingVerification } from '../api/verifyApi'
import DailyQuestsMenuLink from './DailyQuestsMenuLink'
import { LevelBadge } from './LevelBadge'
import './HomeScreen.css'
import glass_eel_2 from '../../images/glass_eel_2.png'
import yellow_eel from '../../images/yellow_eel.png'
import silver_eel_2 from '../../images/silver_eel_2.png'

export type GameId = 'overlap' | 'annotate' | 'verify'

interface GameCard {
  id: GameId
  league: string
  title: string
  flavor: string
  description: string
  image: string
  active: boolean
}

const GAMES: GameCard[] = [
  {
    id: 'overlap',
    league: 'Glass Eel League',
    title: 'Finding Overlap',
    flavor: 'A glass eel drifts in from the open ocean, scanning the coastline for familiar water.',
    image: glass_eel_2,
    description: 'Look at two marine images and decide whether they show the same physical scene.',
    active: true,
  },
  {
    id: 'annotate',
    league: 'Yellow Eel League',
    title: 'Annotating',
    flavor: 'For years, a yellow eel learns every rock and reed of its river home by heart.',
    image: yellow_eel,
    description: 'Click matching points between two overlapping images to build ground-truth correspondences.',
    active: true,
  },
  {
    id: 'verify',
    league: 'Silver Eel League',
    title: 'Verification',
    image: silver_eel_2,
    flavor: 'Before the long migration back to sea, a silver eel double-checks its bearings.',
    description: "Review another player's annotation and flag it if it doesn't look right.",
    active: true,
  },
]

export default function HomeScreen({
  onPlay,
  user,
  region,
  onChangeRegion,
  onOpenAdmin,
  onOpenTeam,
  onOpenStats,
  onOpenQuests,
  onLogout,
}: {
  onPlay: (id: GameId) => void
  user: User
  region: Region
  onChangeRegion: () => void
  onOpenAdmin: () => void
  onOpenTeam: () => void
  onOpenStats: () => void
  onOpenQuests: () => void
  onLogout: () => void
}) {
  // Per-game availability for this region: `undefined` while we're still probing;
  // otherwise `true` if the game has something to serve, `false` if it's empty.
  // A region can have dives but no candidate/image pairs for a given stage (or the
  // player may have already worked through them), so we probe each game the same
  // way the game screen does — resolve a dive, then ask that stage's "next" endpoint.
  const [availability, setAvailability] = useState<Record<GameId, boolean> | undefined>(undefined)

  useEffect(() => {
    let cancelled = false
    setAvailability(undefined)

    async function probe(diveUuid: string): Promise<Record<GameId, boolean>> {
      const [overlap, annotate, verify] = await Promise.all([
        fetchNextCandidatePair(diveUuid),
        fetchNextImagePair(diveUuid),
        fetchNextPendingVerification(diveUuid),
      ])
      return { overlap: overlap !== null, annotate: annotate !== null, verify: verify !== null }
    }

    fetchDivesForRegion(region.uuid)
      .then((dives) => {
        const dive = dives[0]
        if (!dive) return { overlap: false, annotate: false, verify: false }
        return probe(dive.uuid)
      })
      // On a fetch error we can't be sure the region is empty, so leave every game
      // playable and let the game screen surface the failure itself.
      .catch(() => ({ overlap: true, annotate: true, verify: true }))
      .then((result) => {
        if (!cancelled) setAvailability(result)
      })

    return () => {
      cancelled = true
    }
  }, [region.uuid])

  const tooltip = `There's nothing to play in this stage for ${region.title} right now — it has no imagery for this stage yet, or you've already worked through it. Try another region.`

  return (
    <div className="home-screen">
      <div className="account-bar">
        <span>
          Signed in as <strong>{user.username}</strong> · Region: <strong>{region.title}</strong>
        </span>
        <LevelBadge exp={user.exp} />
        <button type="button" className="back-link" onClick={onChangeRegion}>
          Change region
        </button>
        {user.role !== 'annotator' && (
          <button type="button" className="back-link" onClick={onOpenAdmin}>
            Admin
          </button>
        )}
        <button type="button" className="back-link" onClick={onOpenStats}>
          My Stats
        </button>
        <DailyQuestsMenuLink onClick={onOpenQuests} />
        <button type="button" className="back-link" onClick={onOpenTeam}>
          Team
        </button>
        <button type="button" className="back-link" onClick={onLogout}>
          Log out
        </button>
      </div>

      <header className="home-header">
        <p className="home-eyebrow">Journey of the Eel</p>
        <h1>Sea the Bigger Picture</h1>
        <p>
          Every year, European eels leave the rivers where they grew up and swim thousands of kilometres back to
          the Sargasso Sea to spawn — a route no one has ever fully mapped. Play through three leagues of the
          eel's life to help scientists retrace it, one matched image at a time.
        </p>
      </header>

      <div className="game-card-row">
        {GAMES.map((game) => {
          // `undefined` availability = still probing; treat as playable so the
          // buttons don't flash disabled on every home visit.
          const noData = game.active && availability?.[game.id] === false
          const disabled = !game.active || noData
          return (
            <article
              className={`game-card${disabled ? ' game-card-locked' : ''}${noData ? ' game-card-nodata' : ''}`}
              data-game={game.id}
              key={game.id}
            >
              <span className="game-card-league">{game.league}</span>
              <h2>{game.title}</h2>
              <p className="game-card-flavor">{game.flavor}</p>
              <img
                src={game.image}
                alt={game.title}
                className="game-card-image"
              />
              <p>{game.description}</p>
              <button
                type="button"
                className="btn btn-primary"
                disabled={disabled}
                onClick={() => onPlay(game.id)}
              >
                {!game.active ? 'Coming soon' : noData ? 'No data yet' : 'Play'}
              </button>
              {noData && (
                <span className="game-card-tooltip" role="tooltip">
                  {tooltip}
                </span>
              )}
            </article>
          )
        })}
      </div>
    </div>
  )
}
