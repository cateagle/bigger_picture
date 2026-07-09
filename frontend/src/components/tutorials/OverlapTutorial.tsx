import { useState } from 'react'
import type { NormalizedPoint } from '../../api/types'
import { SceneBackground } from './ExampleScene'
import type { SceneVariant } from './ExampleScene'
import './tutorialShell.css'

type Stage = 'same' | 'different' | 'wrap'

// Placeholder target, positioned against the stylized reef in ExampleScene's
// SceneBackground. Swap alongside real example imagery later.
const ROCK: NormalizedPoint = { x: 0.28, y: 0.75 }

const NARRATION: Record<Stage, { title: string; body: string }> = {
  same: {
    title: 'Look for a shared landmark',
    body: 'These two photos share the same rock — just seen from a different angle. Ignore fish, bubbles and lighting changes; focus on fixed structure. Is this the same physical scene?',
  },
  different: {
    title: 'Now a different pair',
    body: 'This time nothing lines up: different rock, different coral, different seabed. Is this the same physical scene?',
  },
  wrap: {
    title: 'You’re ready',
    body: 'Toggle the grid overlay to help line up landmarks, and use Skip whenever you genuinely can’t tell — a confident guess from someone else beats a coin flip.',
  },
}

const SCENE_B_VARIANT: Record<'same' | 'different', SceneVariant> = {
  same: 'angled',
  different: 'different',
}

const INCORRECT_FEEDBACK: Record<'same' | 'different', string> = {
  same: 'Look again — the same rock and coral heads appear in both, which makes this the same scene.',
  different: 'Look again — nothing here matches: different rock, different coral, different water color.',
}

/**
 * A guided, action-driven first-play tutorial for the Overlap game. Puts the
 * reader in front of the real two-image layout and has them make the actual
 * call — first on a pair that's the same scene from a different angle, then
 * on a pair that's genuinely different — before playing for real.
 */
export default function OverlapTutorial({ onComplete }: { onComplete: () => void }) {
  const [stage, setStage] = useState<Stage>('same')
  const [hint, setHint] = useState<string | null>(null)

  const choose = (chosenSame: boolean) => {
    if (stage === 'wrap') return
    const correct = chosenSame === (stage === 'same')
    if (correct) {
      setHint(null)
      setStage(stage === 'same' ? 'different' : 'wrap')
    } else {
      setHint(INCORRECT_FEEDBACK[stage])
    }
  }

  const narration = NARRATION[stage]

  return (
    <div className="tut-backdrop" data-game="overlap">
      <div className="tut-modal" role="dialog" aria-modal="true" aria-labelledby="overlap-tut-title">
        <button type="button" className="tut-skip" onClick={onComplete}>
          Skip tutorial
        </button>
        <h2 id="overlap-tut-title">{narration.title}</h2>
        <p className="tut-body">{narration.body}</p>

        {stage !== 'wrap' && (
          <>
            <div className="tut-scene-row">
              <div className="tut-scene">
                <SceneBackground />
                {stage === 'same' && (
                  <div className="tut-hint" style={{ left: `${ROCK.x * 100}%`, top: `${ROCK.y * 100}%` }} />
                )}
              </div>
              <div className="tut-scene">
                <SceneBackground variant={SCENE_B_VARIANT[stage]} />
                {stage === 'same' && (
                  <div className="tut-hint" style={{ left: `${ROCK.x * 100}%`, top: `${ROCK.y * 100}%` }} />
                )}
              </div>
            </div>

            <div className="tut-choice-buttons">
              <button type="button" className="btn" onClick={() => choose(false)}>
                Different scene
              </button>
              <button type="button" className="btn btn-primary" onClick={() => choose(true)}>
                Same scene
              </button>
            </div>
          </>
        )}

        {hint && <p className="tut-feedback tut-feedback-bad">{hint}</p>}

        {stage === 'wrap' && (
          <footer className="tut-footer">
            <button type="button" className="btn btn-primary tut-start" onClick={onComplete}>
              Start playing
            </button>
          </footer>
        )}
      </div>
    </div>
  )
}
