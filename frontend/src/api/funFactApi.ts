import { apiFetch } from './client'
import type { FunFact } from './types'

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/fun-facts. */
export function fetchFunFacts(): Promise<FunFact[]> {
  return apiFetch<{ fun_facts: FunFact[]; total: number }>('/api/v1/dataset/fun-facts').then(
    (res) => res.fun_facts,
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
