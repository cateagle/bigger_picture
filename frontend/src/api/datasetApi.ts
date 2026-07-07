import { apiFetch } from './client'
import type { DatasetSummary } from './types'

/** Scientist/admin only - counts of dives, images, and image pairs in the dataset. */
export function fetchDatasetSummary(): Promise<DatasetSummary> {
  return apiFetch<DatasetSummary>('/api/v1/dataset/summary')
}
