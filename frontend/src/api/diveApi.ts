import { apiFetch } from './client'
import type { Dive } from './types'

/** Real endpoint: GET /api/v1/annotate/dives?region={uuid}. Any authenticated role. */
export function fetchDivesForRegion(regionUuid: string): Promise<Dive[]> {
  return apiFetch<{ dives: Dive[] }>(`/api/v1/annotate/dives?region=${regionUuid}`).then((res) => res.dives)
}
