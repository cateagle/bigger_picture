import { delay } from './mockDelay'
import type { CandidatePair } from './types'

/**
 * Mock stand-in for the Stage 1 (Finding Overlap) backend endpoints. The
 * backend has `candidate_pairs`/`candidate_annotations` tables (see
 * backend/src/schema/candidate_pairs.py) but no API route exposing them
 * yet, so this simulates network latency and serves a fixed rotation of
 * pairs built from the same `public/mock-images` assets Stage 2 uses - some
 * genuinely overlapping, some mismatched - so the game can be built and
 * played against a realistic async contract. Swap the bodies of these two
 * functions for real `fetch()` calls once the backend exposes a
 * candidate-pair endpoint; callers don't need to change.
 */

const MOCK_CANDIDATES: CandidatePair[] = [
  { candidateId: 'candidate-1', imageA: '/mock-images/pair-1/a.jpg', imageB: '/mock-images/pair-1/b.jpg' },
  { candidateId: 'candidate-2', imageA: '/mock-images/pair-2/a.jpg', imageB: '/mock-images/pair-3/a.jpg' },
  { candidateId: 'candidate-3', imageA: '/mock-images/pair-2/a.jpg', imageB: '/mock-images/pair-2/b.jpg' },
  { candidateId: 'candidate-4', imageA: '/mock-images/pair-4/b.jpg', imageB: '/mock-images/pair-5/a.jpg' },
  { candidateId: 'candidate-5', imageA: '/mock-images/pair-3/a.jpg', imageB: '/mock-images/pair-3/b.jpg' },
  { candidateId: 'candidate-6', imageA: '/mock-images/pair-5/a.jpg', imageB: '/mock-images/pair-5/b.jpg' },
  { candidateId: 'candidate-7', imageA: '/mock-images/pair-1/b.jpg', imageB: '/mock-images/pair-4/a.jpg' },
  { candidateId: 'candidate-8', imageA: '/mock-images/pair-4/a.jpg', imageB: '/mock-images/pair-4/b.jpg' },
]

let nextCandidateIndex = 0

export async function fetchCandidatePair(): Promise<CandidatePair> {
  await delay(400)
  const pair = MOCK_CANDIDATES[nextCandidateIndex % MOCK_CANDIDATES.length]
  nextCandidateIndex += 1
  return pair
}

export async function submitOverlapDecision(candidateId: string, overlaps: boolean): Promise<{ ok: true }> {
  await delay(300)
  console.info(`[mock backend] overlap decision for ${candidateId}: ${overlaps ? 'same scene' : 'different scene'}`)
  return { ok: true }
}
