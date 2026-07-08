import { apiFetch, assetUrl } from './client'
import type { NormalizedPoint, PendingVerification } from './types'

/** Mirrors `NextPairImageResponse` from `backend/src/models/annotate.py` (only the fields used here). */
interface ReviewImage {
  uuid: string
  filepath: string
  size_x: number
  size_y: number
}

/** Mirrors `PointAnnotationReviewResponse` from `backend/src/models/annotate.py` (only the fields used here). */
interface PointAnnotationReview {
  uuid: string
  image_a: ReviewImage
  image_b: ReviewImage
  x1: number
  y1: number
  x2: number
  y2: number
}

/**
 * How many pending points to pull per fetch. The review-queue endpoint
 * returns individual points, not grouped by pair, so this needs to be large
 * enough to reliably capture every point belonging to the first pair in the
 * batch (see `groupByPair`).
 */
const REVIEW_BATCH_SIZE = 25

function toNormalizedPoint(x: number, y: number, image: ReviewImage): NormalizedPoint {
  return { x: x / image.size_x, y: y / image.size_y }
}

/** Keeps only the points belonging to the same image pair as the first item, so a whole annotated pair is reviewed together. */
function groupByPair(items: PointAnnotationReview[]): PointAnnotationReview[] {
  if (items.length === 0) return []
  const [first] = items
  return items.filter((item) => item.image_a.uuid === first.image_a.uuid && item.image_b.uuid === first.image_b.uuid)
}

/**
 * Real endpoint: GET /api/v1/annotate/points/review/next/{dive_uuid}/{n}.
 * Groups the fetched points by image pair and returns the first pair's
 * points as one verification item (all its correspondences reviewed
 * together), converting pixel coordinates back to the [0, 1] normalized
 * space the UI works in. Resolves `null` once there's nothing pending.
 */
export async function fetchNextPendingVerification(diveUuid: string): Promise<PendingVerification | null> {
  const items = await apiFetch<PointAnnotationReview[]>(
    `/api/v1/annotate/points/review/next/${diveUuid}/${REVIEW_BATCH_SIZE}`,
  )
  const group = groupByPair(items)
  if (group.length === 0) return null

  const { image_a, image_b } = group[0]
  return {
    annotationId: `${image_a.uuid}:${image_b.uuid}`,
    imageA: assetUrl(image_a.filepath),
    imageB: assetUrl(image_b.filepath),
    correspondences: group.map((item) => ({
      pointUuid: item.uuid,
      pointA: toNormalizedPoint(item.x1, item.y1, image_a),
      pointB: toNormalizedPoint(item.x2, item.y2, image_b),
    })),
  }
}

/** Real endpoint: POST /api/v1/annotate/points/review/{uuid}/approve|fail, one call per point. */
export function submitVerification(item: PendingVerification, approved: boolean): Promise<void> {
  const action = approved ? 'approve' : 'fail'
  return Promise.all(
    item.correspondences.map((c) =>
      apiFetch<unknown>(`/api/v1/annotate/points/review/${c.pointUuid}/${action}`, { method: 'POST' }),
    ),
  ).then(() => undefined)
}
