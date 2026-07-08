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
  /** Real backend image uuids for `image_a`/`image_b` in `PointAnnotationCreateRequest`. */
  imageAUuid: string
  imageBUuid: string
}

export interface CandidatePair {
  candidateId: string
  imageA: string
  imageB: string
  /** Real backend image uuids for `image_a`/`image_b` in `CandidateAnnotationCreateRequest`. */
  imageAUuid: string
  imageBUuid: string
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

/** A single already-submitted correspondence awaiting Stage 3 review. */
export interface VerificationPoint extends Correspondence {
  /** Real backend `PointAnnotation.uuid`, the id `points/review/{uuid}/...` acts on. */
  pointUuid: string
}

/** A Stage 2 annotation awaiting Stage 3 review. */
export interface PendingVerification {
  annotationId: string
  imageA: string
  imageB: string
  correspondences: VerificationPoint[]
}
