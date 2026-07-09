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
 * `image` is base64-encoded image data, mirroring `ImageCreateRequest.image` on the dataset
 * images endpoint. Optional - anticipates the backend's upcoming image-upload support, not
 * live yet.
 */
export function createFunFact(input: {
  title: string
  fact: unknown
  region?: string | null
  image?: string | null
}): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/fun-facts/update. */
export function updateFunFact(
  uuid: string,
  input: { title?: string; fact?: unknown; region?: string | null },
): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}

/**
 * Scientist/admin only - anticipates a not-yet-implemented endpoint:
 * POST /api/v1/dataset/fun-facts/image. Replaces the image on an existing fact, independent of
 * its title/fact/region. `image` is base64-encoded image data.
 */
export function updateFunFactImage(uuid: string, image: string): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/image', {
    method: 'POST',
    body: JSON.stringify({ uuid, image }),
  })
}
