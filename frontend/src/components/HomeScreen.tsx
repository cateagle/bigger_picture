import type { Region, User } from '../api/types'
import { LevelBadge } from './LevelBadge'
import './HomeScreen.css'

export type GameId = 'overlap' | 'annotate' | 'verify'

interface GameCard {
  id: GameId
  league: string
  title: string
  flavor: string
  description: string
  active: boolean
}

const GAMES: GameCard[] = [
  {
    id: 'overlap',
    league: 'Glass Eel League',
    title: 'Finding Overlap',
    flavor: 'A glass eel drifts in from the open ocean, scanning the coastline for familiar water.',
    description: 'Look at two marine images and decide whether they show the same physical scene.',
    active: true,
  },
  {
    id: 'annotate',
    league: 'Yellow Eel League',
    title: 'Annotating',
    flavor: 'For years, a yellow eel learns every rock and reed of its river home by heart.',
    description: 'Click matching points between two overlapping images to build ground-truth correspondences.',
    active: true,
  },
  {
    id: 'verify',
    league: 'Silver Eel League',
    title: 'Verification',
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
  onLogout,
}: {
  onPlay: (id: GameId) => void
  user: User
  region: Region
  onChangeRegion: () => void
  onOpenAdmin: () => void
  onOpenTeam: () => void
  onOpenStats: () => void
  onLogout: () => void
}) {
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
        <button type="button" className="back-link" onClick={onOpenTeam}>
          Team
        </button>
        <button type="button" className="back-link" onClick={onLogout}>
          Log out
        </button>
      </div>

      <header className="home-header">
        <p className="home-eyebrow">Journey of the Eel</p>
        <h1>Bigger Picture</h1>
        <p>
          Every year, European eels leave the rivers where they grew up and swim thousands of kilometres back to
          the Sargasso Sea to spawn — a route no one has ever fully mapped. Play through three leagues of the
          eel's life to help scientists retrace it, one matched image at a time.
        </p>
      </header>

      <div className="game-card-row">
        {GAMES.map((game) => (
          <article className={`game-card${game.active ? '' : ' game-card-locked'}`} key={game.id}>
            <span className="game-card-league">{game.league}</span>
            <h2>{game.title}</h2>
            <p className="game-card-flavor">{game.flavor}</p>
            <p>{game.description}</p>
            <button type="button" className="btn btn-primary" disabled={!game.active} onClick={() => onPlay(game.id)}>
              {game.active ? 'Play' : 'Coming soon'}
            </button>
          </article>
        ))}
      </div>
    </div>
  )
}
