import { apiFetch } from './client'
import { delay } from './mockDelay'
import type { CandidatePair } from './types'

/**
 * Mock stand-in for fetching a Stage 1 (Finding Overlap) candidate pair. The
 * backend has no endpoint to fetch/list candidate pairs yet (only
 * `/api/v1/annotate/candidate/create`, which requires already knowing a real
 * candidate pair's image uuids), so this still simulates network latency and
 * serves a fixed rotation of pairs built from the `public/mock-images`
 * assets. Swap this for a real `fetch()` once the backend exposes a
 * fetch-next-candidate endpoint; `submitOverlapDecision` below already calls
 * the real backend.
 */

const MOCK_CANDIDATES: CandidatePair[] = [
  {
    candidateId: 'candidate-1',
    imageA: '/mock-images/pair-1/a.jpg',
    imageB: '/mock-images/pair-1/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000001',
    imageBUuid: '00000000-0000-4000-8000-000000000002',
  },
  {
    candidateId: 'candidate-2',
    imageA: '/mock-images/pair-2/a.jpg',
    imageB: '/mock-images/pair-3/a.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000003',
    imageBUuid: '00000000-0000-4000-8000-000000000005',
  },
  {
    candidateId: 'candidate-3',
    imageA: '/mock-images/pair-2/a.jpg',
    imageB: '/mock-images/pair-2/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000003',
    imageBUuid: '00000000-0000-4000-8000-000000000004',
  },
  {
    candidateId: 'candidate-4',
    imageA: '/mock-images/pair-4/b.jpg',
    imageB: '/mock-images/pair-5/a.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000008',
    imageBUuid: '00000000-0000-4000-8000-000000000009',
  },
  {
    candidateId: 'candidate-5',
    imageA: '/mock-images/pair-3/a.jpg',
    imageB: '/mock-images/pair-3/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000005',
    imageBUuid: '00000000-0000-4000-8000-000000000006',
  },
  {
    candidateId: 'candidate-6',
    imageA: '/mock-images/pair-5/a.jpg',
    imageB: '/mock-images/pair-5/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000009',
    imageBUuid: '00000000-0000-4000-8000-00000000000a',
  },
  {
    candidateId: 'candidate-7',
    imageA: '/mock-images/pair-1/b.jpg',
    imageB: '/mock-images/pair-4/a.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000002',
    imageBUuid: '00000000-0000-4000-8000-000000000007',
  },
  {
    candidateId: 'candidate-8',
    imageA: '/mock-images/pair-4/a.jpg',
    imageB: '/mock-images/pair-4/b.jpg',
    imageAUuid: '00000000-0000-4000-8000-000000000007',
    imageBUuid: '00000000-0000-4000-8000-000000000008',
  },
]

let nextCandidateIndex = 0

export async function fetchCandidatePair(): Promise<CandidatePair> {
  await delay(400)
  const pair = MOCK_CANDIDATES[nextCandidateIndex % MOCK_CANDIDATES.length]
  nextCandidateIndex += 1
  return pair
}

/** Real endpoint: POST /api/v1/annotate/candidate/create. */
export function submitOverlapDecision(pair: CandidatePair, overlaps: boolean): Promise<void> {
  return apiFetch<unknown>('/api/v1/annotate/candidate/create', {
    method: 'POST',
    body: JSON.stringify({
      uuid: crypto.randomUUID(),
      image_a: pair.imageAUuid,
      image_b: pair.imageBUuid,
      no_overlap: !overlaps,
    }),
  }).then(() => undefined)
}
