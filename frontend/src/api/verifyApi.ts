import { delay } from './mockDelay'
import type { PendingVerification } from './types'

/**
 * Mock stand-in for the Stage 3 (Verification) backend endpoints. The
 * backend's `point_annotations` table has a `status_id`/`reviewed_by`
 * pair meant for exactly this review step (see
 * backend/src/schema/point_annotations.py) but no API route exposing
 * pending annotations yet, so this simulates network latency and serves a
 * fixed rotation of already-annotated pairs to approve or flag - most with
 * plausible matching points, one with an obviously mismatched point. Swap
 * the bodies of these two functions for real `fetch()` calls once the
 * backend exposes a review-queue endpoint; callers don't need to change.
 */

const MOCK_VERIFICATIONS: PendingVerification[] = [
  {
    annotationId: 'verify-1',
    imageA: '/mock-images/pair-1/a.jpg',
    imageB: '/mock-images/pair-1/b.jpg',
    correspondences: [
      { pointA: { x: 0.22, y: 0.35 }, pointB: { x: 0.2, y: 0.33 } },
      { pointA: { x: 0.55, y: 0.6 }, pointB: { x: 0.52, y: 0.58 } },
      { pointA: { x: 0.75, y: 0.25 }, pointB: { x: 0.72, y: 0.23 } },
      { pointA: { x: 0.4, y: 0.8 }, pointB: { x: 0.38, y: 0.78 } },
    ],
  },
  {
    annotationId: 'verify-2',
    imageA: '/mock-images/pair-2/a.jpg',
    imageB: '/mock-images/pair-2/b.jpg',
    correspondences: [
      { pointA: { x: 0.3, y: 0.4 }, pointB: { x: 0.28, y: 0.38 } },
      { pointA: { x: 0.6, y: 0.3 }, pointB: { x: 0.58, y: 0.28 } },
      { pointA: { x: 0.5, y: 0.7 }, pointB: { x: 0.1, y: 0.15 } }, // deliberately mismatched
      { pointA: { x: 0.2, y: 0.6 }, pointB: { x: 0.18, y: 0.58 } },
    ],
  },
  {
    annotationId: 'verify-3',
    imageA: '/mock-images/pair-3/a.jpg',
    imageB: '/mock-images/pair-3/b.jpg',
    correspondences: [
      { pointA: { x: 0.35, y: 0.45 }, pointB: { x: 0.33, y: 0.43 } },
      { pointA: { x: 0.65, y: 0.35 }, pointB: { x: 0.62, y: 0.33 } },
      { pointA: { x: 0.5, y: 0.75 }, pointB: { x: 0.48, y: 0.73 } },
    ],
  },
  {
    annotationId: 'verify-4',
    imageA: '/mock-images/pair-4/a.jpg',
    imageB: '/mock-images/pair-4/b.jpg',
    correspondences: [
      { pointA: { x: 0.25, y: 0.3 }, pointB: { x: 0.23, y: 0.28 } },
      { pointA: { x: 0.5, y: 0.5 }, pointB: { x: 0.48, y: 0.48 } },
      { pointA: { x: 0.7, y: 0.6 }, pointB: { x: 0.68, y: 0.58 } },
      { pointA: { x: 0.45, y: 0.2 }, pointB: { x: 0.43, y: 0.18 } },
    ],
  },
  {
    annotationId: 'verify-5',
    imageA: '/mock-images/pair-5/a.jpg',
    imageB: '/mock-images/pair-5/b.jpg',
    correspondences: [
      { pointA: { x: 0.4, y: 0.4 }, pointB: { x: 0.38, y: 0.38 } },
      { pointA: { x: 0.6, y: 0.6 }, pointB: { x: 0.58, y: 0.58 } },
    ],
  },
]

let nextVerificationIndex = 0

export async function fetchPendingVerification(): Promise<PendingVerification> {
  await delay(400)
  const item = MOCK_VERIFICATIONS[nextVerificationIndex % MOCK_VERIFICATIONS.length]
  nextVerificationIndex += 1
  return item
}

export async function submitVerification(annotationId: string, approved: boolean): Promise<{ ok: true }> {
  await delay(300)
  console.info(`[mock backend] verification for ${annotationId}: ${approved ? 'approved' : 'flagged'}`)
  return { ok: true }
}
