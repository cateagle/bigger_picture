import { apiFetch } from './client'
import type { AnnotationSummary, CandidatePairSummary, DatasetImage, DatasetSummary, ImagePairSummary } from './types'

export interface PaginatedResult<T> {
  items: T[]
  total: number
}

/** Mirrors `DatasetImportCounts` from `backend/src/models/dataset.py`. */
export interface DatasetImportCounts {
  labels: number
  cameras: number
  regions: number
  dives: number
  images: number
  candidate_pairs: number
  image_pairs: number
}

/** Scientist/admin only - counts of dives, images, and image pairs in the dataset. */
export function fetchDatasetSummary(): Promise<DatasetSummary> {
  return apiFetch<DatasetSummary>('/api/v1/dataset/summary')
}

/** Scientist only - real endpoint: POST /api/v1/dataset/zip-upload (multipart/form-data, field "file"). */
export function uploadDatasetZip(file: File): Promise<DatasetImportCounts> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<{ created: DatasetImportCounts }>('/api/v1/dataset/zip-upload', {
    method: 'POST',
    body: formData,
  }).then((res) => res.created)
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/images?dive={uuid}&page={page}&page_size={pageSize}. */
export function fetchImagesForDive(
  diveUuid: string,
  page: number,
  pageSize: number,
): Promise<PaginatedResult<DatasetImage>> {
  return apiFetch<{ images: DatasetImage[]; total: number }>(
    `/api/v1/dataset/images?dive=${diveUuid}&page=${page}&page_size=${pageSize}`,
  ).then((res) => ({ items: res.images, total: res.total }))
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/candidates?dive={uuid}&page={page}&page_size={pageSize}. */
export function fetchCandidatePairsForDive(
  diveUuid: string,
  page: number,
  pageSize: number,
): Promise<PaginatedResult<CandidatePairSummary>> {
  return apiFetch<{ candidates: CandidatePairSummary[]; total: number }>(
    `/api/v1/dataset/candidates?dive=${diveUuid}&page=${page}&page_size=${pageSize}`,
  ).then((res) => ({ items: res.candidates, total: res.total }))
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/pairs?dive={uuid}&page={page}&page_size={pageSize}. */
export function fetchImagePairsForDive(
  diveUuid: string,
  page: number,
  pageSize: number,
): Promise<PaginatedResult<ImagePairSummary>> {
  return apiFetch<{ pairs: ImagePairSummary[]; total: number }>(
    `/api/v1/dataset/pairs?dive=${diveUuid}&page=${page}&page_size=${pageSize}`,
  ).then((res) => ({ items: res.pairs, total: res.total }))
}

/** Scientist/admin only - real endpoint: GET /api/v1/dataset/annotations?dive={uuid}. */
export function fetchAnnotationsForDive(diveUuid: string): Promise<AnnotationSummary[]> {
  return apiFetch<{ annotations: AnnotationSummary[] }>(`/api/v1/dataset/annotations?dive=${diveUuid}`).then(
    (res) => res.annotations,
  )
}
