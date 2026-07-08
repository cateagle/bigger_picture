import { apiFetch } from './client'
import type { Region, RegionMesh } from './types'

/** Real endpoint: GET /api/v1/annotate/regions. */
export function fetchRegions(): Promise<Region[]> {
  return apiFetch<{ regions: Region[] }>('/api/v1/annotate/regions').then((res) => res.regions)
}

export interface RegionMetadataInput {
  mesh?: RegionMesh
  [key: string]: unknown
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/regions/create. */
export function createRegion(input: {
  title: string
  description?: string | null
  metadata?: RegionMetadataInput | null
}): Promise<Region> {
  return apiFetch<Region>('/api/v1/dataset/regions/create', {
    method: 'POST',
    body: JSON.stringify({ uuid: crypto.randomUUID(), ...input }),
  })
}

/** Scientist/admin only - real endpoint: POST /api/v1/dataset/regions/update. */
export function updateRegion(
  uuid: string,
  input: { title?: string; description?: string | null; metadata?: RegionMetadataInput | null },
): Promise<Region> {
  return apiFetch<Region>('/api/v1/dataset/regions/update', {
    method: 'POST',
    body: JSON.stringify({ uuid, ...input }),
  })
}
