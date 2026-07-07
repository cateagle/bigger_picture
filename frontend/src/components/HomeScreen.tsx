import './HomeScreen.css'

export type GameId = 'overlap' | 'annotate' | 'verify'

interface GameCard {
  id: GameId
  stage: number
  title: string
  description: string
  active: boolean
}

const GAMES: GameCard[] = [
  {
    id: 'overlap',
    stage: 1,
    title: 'Finding Overlap',
    description: 'Look at two marine images and decide whether they show the same physical scene.',
    active: true,
  },
  {
    id: 'annotate',
    stage: 2,
    title: 'Annotating',
    description: 'Click matching points between two overlapping images to build ground-truth correspondences.',
    active: true,
  },
  {
    id: 'verify',
    stage: 3,
    title: 'Verification',
    description: "Review another player's annotation and flag it if it doesn't look right.",
    active: true,
  },
]

export default function HomeScreen({ onPlay }: { onPlay: (id: GameId) => void }) {
  return (
    <div className="home-screen">
      <header className="home-header">
        <h1>Bigger Picture</h1>
        <p>
          Help build a ground-truth dataset of marine images by playing short rounds. Pick a stage below to get
          started.
        </p>
      </header>

      <div className="game-card-row">
        {GAMES.map((game) => (
          <article className={`game-card${game.active ? '' : ' game-card-locked'}`} key={game.id}>
            <span className="game-card-stage">Stage {game.stage}</span>
            <h2>{game.title}</h2>
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
