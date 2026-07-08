import { apiFetch } from './client'
import type { FunFact } from './types'

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/fun-facts. */
export function fetchFunFacts(): Promise<FunFact[]> {
  return apiFetch<{ fun_facts: FunFact[]; total: number }>('/api/v1/dataset/fun-facts').then(
    (res) => res.fun_facts,
  )
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/fun-facts/create. */
export function createFunFact(input: { title: string; fact: unknown }): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/fun-facts/update. */
export function updateFunFact(uuid: string, input: { title?: string; fact?: unknown }): Promise<FunFact> {
  return apiFetch<FunFact>('/api/v1/dataset/fun-facts/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
