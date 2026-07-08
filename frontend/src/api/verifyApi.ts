import { apiFetch } from './client'
import { delay } from './mockDelay'
import type { PendingVerification } from './types'

/**
 * Mock stand-in for fetching a Stage 3 (Verification) item. The backend has
 * no endpoint to fetch/list pending annotations yet (only
 * `/api/v1/annotate/points/review/{uuid}/approve|fail`, which require
 * already knowing a real point annotation's uuid), so this still simulates
 * network latency and serves a fixed rotation of already-annotated pairs -
 * most with plausible matching points, one with an obviously mismatched
 * point. Swap this for a real `fetch()` once the backend exposes a
 * review-queue endpoint; `submitVerification` below already calls the real
 * backend.
 */

const MOCK_VERIFICATIONS: PendingVerification[] = [
  {
    annotationId: 'verify-1',
    imageA: '/mock-images/pair-1/a.jpg',
    imageB: '/mock-images/pair-1/b.jpg',
    correspondences: [
      { pointUuid: '00000000-0000-4000-9000-000000000001', pointA: { x: 0.22, y: 0.35 }, pointB: { x: 0.2, y: 0.33 } },
      { pointUuid: '00000000-0000-4000-9000-000000000002', pointA: { x: 0.55, y: 0.6 }, pointB: { x: 0.52, y: 0.58 } },
      { pointUuid: '00000000-0000-4000-9000-000000000003', pointA: { x: 0.75, y: 0.25 }, pointB: { x: 0.72, y: 0.23 } },
      { pointUuid: '00000000-0000-4000-9000-000000000004', pointA: { x: 0.4, y: 0.8 }, pointB: { x: 0.38, y: 0.78 } },
    ],
  },
  {
    annotationId: 'verify-2',
    imageA: '/mock-images/pair-2/a.jpg',
    imageB: '/mock-images/pair-2/b.jpg',
    correspondences: [
      { pointUuid: '00000000-0000-4000-9000-000000000005', pointA: { x: 0.3, y: 0.4 }, pointB: { x: 0.28, y: 0.38 } },
      { pointUuid: '00000000-0000-4000-9000-000000000006', pointA: { x: 0.6, y: 0.3 }, pointB: { x: 0.58, y: 0.28 } },
      { pointUuid: '00000000-0000-4000-9000-000000000007', pointA: { x: 0.5, y: 0.7 }, pointB: { x: 0.1, y: 0.15 } }, // deliberately mismatched
      { pointUuid: '00000000-0000-4000-9000-000000000008', pointA: { x: 0.2, y: 0.6 }, pointB: { x: 0.18, y: 0.58 } },
    ],
  },
  {
    annotationId: 'verify-3',
    imageA: '/mock-images/pair-3/a.jpg',
    imageB: '/mock-images/pair-3/b.jpg',
    correspondences: [
      { pointUuid: '00000000-0000-4000-9000-000000000009', pointA: { x: 0.35, y: 0.45 }, pointB: { x: 0.33, y: 0.43 } },
      { pointUuid: '00000000-0000-4000-9000-00000000000a', pointA: { x: 0.65, y: 0.35 }, pointB: { x: 0.62, y: 0.33 } },
      { pointUuid: '00000000-0000-4000-9000-00000000000b', pointA: { x: 0.5, y: 0.75 }, pointB: { x: 0.48, y: 0.73 } },
    ],
  },
  {
    annotationId: 'verify-4',
    imageA: '/mock-images/pair-4/a.jpg',
    imageB: '/mock-images/pair-4/b.jpg',
    correspondences: [
      { pointUuid: '00000000-0000-4000-9000-00000000000c', pointA: { x: 0.25, y: 0.3 }, pointB: { x: 0.23, y: 0.28 } },
      { pointUuid: '00000000-0000-4000-9000-00000000000d', pointA: { x: 0.5, y: 0.5 }, pointB: { x: 0.48, y: 0.48 } },
      { pointUuid: '00000000-0000-4000-9000-00000000000e', pointA: { x: 0.7, y: 0.6 }, pointB: { x: 0.68, y: 0.58 } },
      { pointUuid: '00000000-0000-4000-9000-00000000000f', pointA: { x: 0.45, y: 0.2 }, pointB: { x: 0.43, y: 0.18 } },
    ],
  },
  {
    annotationId: 'verify-5',
    imageA: '/mock-images/pair-5/a.jpg',
    imageB: '/mock-images/pair-5/b.jpg',
    correspondences: [
      { pointUuid: '00000000-0000-4000-9000-000000000010', pointA: { x: 0.4, y: 0.4 }, pointB: { x: 0.38, y: 0.38 } },
      { pointUuid: '00000000-0000-4000-9000-000000000011', pointA: { x: 0.6, y: 0.6 }, pointB: { x: 0.58, y: 0.58 } },
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

/** Real endpoint: POST /api/v1/annotate/points/review/{uuid}/approve|fail, one call per point. */
export function submitVerification(item: PendingVerification, approved: boolean): Promise<void> {
  const action = approved ? 'approve' : 'fail'
  return Promise.all(
    item.correspondences.map((c) =>
      apiFetch<unknown>(`/api/v1/annotate/points/review/${c.pointUuid}/${action}`, { method: 'POST' }),
    ),
  ).then(() => undefined)
}
