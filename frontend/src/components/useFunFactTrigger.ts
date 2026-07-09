import { useCallback, useState } from 'react'
import { getRandomFunFact } from '../api/funFactApi'
import type { FunFact } from '../api/types'

// A fun fact appears after a randomized run of completed items, re-rolled each
// time so the cadence never gets predictable. The first one shows a little
// earlier so players discover the mechanic exists.
const MIN_INTERVAL = 3
const MAX_INTERVAL = 7
const FIRST_MIN_INTERVAL = 2
const FIRST_MAX_INTERVAL = 3

// Never show two facts closer together than this, no matter what the counter
// says — a fast streak of quick items shouldn't machine-gun facts.
const MIN_GAP_MS = 45_000

function rollThreshold(first: boolean): number {
  const min = first ? FIRST_MIN_INTERVAL : MIN_INTERVAL
  const max = first ? FIRST_MAX_INTERVAL : MAX_INTERVAL
  return min + Math.floor(Math.random() * (max - min + 1))
}

// Cadence lives at module scope so it is shared across every game for the
// session: a completed item in *any* game advances the same counter, and the
// counter survives switching between games (which unmounts/remounts them).
// It is intentionally ephemeral — the server tracks what's actually been seen,
// so a page reload resetting the cadence is harmless.
const cadence = {
  count: 0,
  threshold: rollThreshold(true),
  lastShownAt: 0,
}

/**
 * Drives when a fun fact interrupts the game loop. Call `recordCompletion()`
 * once per *completed unit of work* (a submitted annotation pair, an overlap
 * decision, or a fully-reviewed verification pair — never a single point), and
 * render the returned `fact` when it is non-null, dismissing via `dismiss`.
 *
 * `region` biases the fact towards the region being played.
 */
export function useFunFactTrigger(region?: string | null) {
  const [fact, setFact] = useState<FunFact | null>(null)
  const [fetching, setFetching] = useState(false)

  const recordCompletion = useCallback(() => {
    cadence.count += 1
    // Not due yet.
    if (cadence.count < cadence.threshold) return
    // A fact is already on screen or being fetched — leave the counter armed.
    if (fact || fetching) return
    // Respect the minimum gap; stay armed and try again on the next completion.
    if (Date.now() - cadence.lastShownAt < MIN_GAP_MS) return

    setFetching(true)
    getRandomFunFact(region)
      .then((next) => {
        // Nothing eligible right now (common at low levels): stay armed so the
        // fact appears at the next completion once something unlocks, instead
        // of burning the trigger on an empty modal.
        if (!next) return
        cadence.count = 0
        cadence.threshold = rollThreshold(false)
        cadence.lastShownAt = Date.now()
        setFact(next)
      })
      // A fun fact must never break the game loop — swallow failures silently.
      .catch(() => {})
      .finally(() => setFetching(false))
  }, [region, fact, fetching])

  const dismiss = useCallback(() => setFact(null), [])

  return { fact, recordCompletion, dismiss }
}
