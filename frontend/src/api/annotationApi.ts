import { apiFetch } from './client'
import { delay } from './mockDelay'
import type { Correspondence, ImagePair, Label } from './types'

/** Real endpoint: GET /api/v1/annotate/labels. */
export function fetchLabels(): Promise<Label[]> {
  return apiFetch<{ labels: Label[] }>('/api/v1/annotate/labels').then((res) => res.labels)
}

/**
 * Mock stand-in for fetching a Stage 2 (Annotating) image pair to work on.
 * The backend has no endpoint to fetch/list image pairs yet (only
 * `/api/v1/annotate/points/create` and `/batch/create`, which require
 * already knowing a real, `open`-status image pair's image uuids), so this
 * still simulates network latency and serves a fixed rotation of image
 * pairs. Swap this for a real `fetch()` once the backend exposes a
 * fetch-next-pair endpoint; `submitAnnotation` below already calls the real
 * backend.
 */

const MOCK_PAIRS: ImagePair[] = [
  {
    pairId: 'pair-1',
    imageA: '/mock-images/pair-1/a.jpg',
    imageB: '/mock-images/pair-1/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000001',
    imageBUuid: '00000000-0000-4000-8000-000000000002',
  },
  {
    pairId: 'pair-2',
    imageA: '/mock-images/pair-2/a.jpg',
    imageB: '/mock-images/pair-2/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000003',
    imageBUuid: '00000000-0000-4000-8000-000000000004',
  },
  {
    pairId: 'pair-3',
    imageA: '/mock-images/pair-3/a.jpg',
    imageB: '/mock-images/pair-3/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000005',
    imageBUuid: '00000000-0000-4000-8000-000000000006',
  },
  {
    pairId: 'pair-4',
    imageA: '/mock-images/pair-4/a.jpg',
    imageB: '/mock-images/pair-4/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000007',
    imageBUuid: '00000000-0000-4000-8000-000000000008',
  },
  {
    pairId: 'pair-5',
    imageA: '/mock-images/pair-5/a.jpg',
    imageB: '/mock-images/pair-5/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000009',
    imageBUuid: '00000000-0000-4000-8000-00000000000a',
  },
]

let nextPairIndex = 0

export async function fetchImagePair(): Promise<ImagePair> {
  await delay(400)
  const pair = MOCK_PAIRS[nextPairIndex % MOCK_PAIRS.length]
  nextPairIndex += 1
  return pair
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
