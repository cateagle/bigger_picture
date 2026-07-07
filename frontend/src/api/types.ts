export type Role = 'annotator' | 'scientist' | 'admin'

/** Mirrors `UserResponse` from `backend/src/models/auth.py`. */
export interface User {
  id: number
  uuid: string
  username: string
  role: Role
  expert_level: number
  created_at: number
}

/** Mirrors `UserSummary` from `backend/src/models/admin.py`. */
export interface UserSummary {
  id: number
  username: string
  role: Role
  expert_level: number
}

/** Mirrors `LabelResponse` from `backend/src/models/annotate.py`. */
export interface Label {
  id: number
  scope: string
  title: string
  description: string | null
}

/** Mirrors `DatasetSummaryResponse` from `backend/src/models/dataset.py`. */
export interface DatasetSummary {
  dive_count: number
  image_count: number
  image_pair_count: number
}

export interface ImagePair {
  pairId: string
  imageA: string
  imageB: string
}

/** A click location, normalized to the image's own [0, 1] x [0, 1] space. */
export interface NormalizedPoint {
  x: number
  y: number
}

export interface Correspondence {
  pointA: NormalizedPoint
  pointB: NormalizedPoint
}
