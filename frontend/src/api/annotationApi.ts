import { apiFetch, assetUrl } from './client'
import type { Correspondence, ImagePair } from './types'

/** Mirrors `NextPairImageResponse` from `backend/src/models/annotate.py` (only the fields used here). */
interface NextPairImage {
  uuid: string
  filepath: string
}

/** Mirrors `NextPairResponse` from `backend/src/models/annotate.py`. */
interface NextPairResponse {
  image1: NextPairImage
  image2: NextPairImage
  difficulty: number | null
  priority: number | null
  status: string | null
}

function toImagePair(pair: NextPairResponse): ImagePair {
  return {
    pairId: `${pair.image1.uuid}:${pair.image2.uuid}`,
    imageA: assetUrl(pair.image1.filepath),
    imageB: assetUrl(pair.image2.filepath),
    imageAUuid: pair.image1.uuid,
    imageBUuid: pair.image2.uuid,
  }
}

/**
 * Real endpoint: GET /api/v1/annotate/points/next/{dive_uuid}. Resolves
 * `null` once there are no more open, unannotated image pairs left for this
 * player in the dive (or none within their expert level).
 */
export async function fetchNextImagePair(diveUuid: string): Promise<ImagePair | null> {
  const pairs = await apiFetch<NextPairResponse[]>(`/api/v1/annotate/points/next/${diveUuid}`)
  return pairs.length > 0 ? toImagePair(pairs[0]) : null
}

/** Pixel dimensions of the two rendered images, needed to convert normalized clicks to the pixel coordinates the backend expects. */
export interface ImagePairDimensions {
  widthA: number
  heightA: number
  widthB: number
  heightB: number
}

/** Real endpoint: POST /api/v1/annotate/points/batch/create. */
export function submitAnnotation(
  pair: ImagePair,
  correspondences: Correspondence[],
  dimensions: ImagePairDimensions,
): Promise<{ created: number }> {
  const points = correspondences.map((c) => ({
    uuid: crypto.randomUUID(),
    image_a: pair.imageAUuid,
    image_b: pair.imageBUuid,
    x1: Math.round(c.pointA.x * dimensions.widthA),
    y1: Math.round(c.pointA.y * dimensions.heightA),
    x2: Math.round(c.pointB.x * dimensions.widthB),
    y2: Math.round(c.pointB.y * dimensions.heightB),
  }))

  return apiFetch<{ created: number }>('/api/v1/annotate/points/batch/create', {
    method: 'POST',
    body: JSON.stringify(points),
  })
}
