import { apiFetch } from './client'
import type { Region } from './types'

/** Real endpoint: GET /api/v1/annotate/regions. */
export function fetchRegions(): Promise<Region[]> {
  return apiFetch<{ regions: Region[] }>('/api/v1/annotate/regions').then((res) => res.regions)
}
