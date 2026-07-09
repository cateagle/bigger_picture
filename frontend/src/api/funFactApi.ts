import { ApiError, apiFetch } from './client'
import type { FunFact } from './types'

/**
 * How many times a single fact may be shown to a player before it stops being
 * eligible. Passed as `max_seen` to the random endpoint.
 */
export const FUN_FACT_MAX_SEEN = 3

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/fun-facts. */
export function fetchFunFacts(): Promise<FunFact[]> {
  return apiFetch<{ fun_facts: FunFact[]; total: number }>('/api/v1/dataset/fun-facts').then(
    (res) => res.fun_facts,
  )
}

/**
 * Fetch a random fun fact eligible for the current player (real endpoint:
 * GET /api/v1/annotate/fun-facts/random) and record it as seen server-side.
 *
 * Passing `region` biases towards facts tied to the region the player is
 * working in (region-agnostic facts stay eligible too). Resolves to `null`
 * when nothing is currently eligible — e.g. the player has seen everything at
 * their level `FUN_FACT_MAX_SEEN` times already — rather than throwing, so the
 * caller can simply skip showing a fact.
 */
export function getRandomFunFact(region?: string | null): Promise<FunFact | null> {
  const params = new URLSearchParams({ max_seen: String(FUN_FACT_MAX_SEEN) })
  if (region) params.set('region', region)
  return apiFetch<FunFact>(`/api/v1/annotate/fun-facts/random?${params.toString()}`).catch(
    (err) => {
      if (err instanceof ApiError && err.status === 404) return null
      throw err
    },
  )
}

/**
 * Scientist/admin only - real endpoint: POST /api/v1/dataset/fun-facts/create.
 *
 * `image` is base64-encoded raw image bytes, deduplicated by content into a helper image on the
 * backend; `image_filename` is required whenever `image` is set.
 */
export function createFunFact(input: {
  title: string
  fact: unknown
  region?: string | null
  image?: string | null
  image_filename?: string | null
}): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/**
 * Scientist/admin only - real endpoint: POST /api/v1/dataset/fun-facts/update.
 *
 * At most one of `image` (with `image_filename`) or `clear_image` may be set per call: upload new
 * bytes and attach them, or detach the current image. Omit both to leave the image unchanged.
 */
export function updateFunFact(
  uuid: string,
  input: {
    title?: string
    fact?: unknown
    region?: string | null
    image?: string | null
    image_filename?: string | null
    clear_image?: boolean
  },
): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
