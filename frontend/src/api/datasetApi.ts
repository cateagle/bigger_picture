import { apiFetch } from './client'
import type { AnnotationSummary, CandidatePairSummary, DatasetImage, DatasetSummary, ImagePairSummary } from './types'

/** Scientist/admin only - counts of dives, images, and image pairs in the dataset. */
export function fetchDatasetSummary(): Promise<DatasetSummary> {
  return apiFetch<DatasetSummary>('/api/v1/dataset/summary')
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/images?dive={uuid}. */
export function fetchImagesForDive(diveUuid: string): Promise<DatasetImage[]> {
  return apiFetch<{ images: DatasetImage[] }>(`/api/v1/dataset/images?dive=${diveUuid}`).then((res) => res.images)
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/candidates?dive={uuid}. */
export function fetchCandidatePairsForDive(diveUuid: string): Promise<CandidatePairSummary[]> {
  return apiFetch<{ candidates: CandidatePairSummary[] }>(`/api/v1/dataset/candidates?dive=${diveUuid}`).then(
    (res) => res.candidates,
  )
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/pairs?dive={uuid}. */
export function fetchImagePairsForDive(diveUuid: string): Promise<ImagePairSummary[]> {
  return apiFetch<{ pairs: ImagePairSummary[] }>(`/api/v1/dataset/pairs?dive=${diveUuid}`).then((res) => res.pairs)
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/annotations?dive={uuid}. */
export function fetchAnnotationsForDive(diveUuid: string): Promise<AnnotationSummary[]> {
  return apiFetch<{ annotations: AnnotationSummary[] }>(`/api/v1/dataset/annotations?dive=${diveUuid}`).then(
    (res) => res.annotations,
  )
}
