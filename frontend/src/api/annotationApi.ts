import type { Correspondence, ImagePair } from './types'

/**
 * Mock stand-in for the Stage 2 (Annotating) backend endpoints. No backend
 * exists yet (see README) - this simulates network latency and serves a
 * fixed rotation of pre-generated overlapping image pairs from
 * `public/mock-images`, so the game screen can be built and played against
 * a realistic async contract. Swap the bodies of these two functions for
 * real `fetch()` calls once the backend exists; callers don't need to change.
 */

const MOCK_PAIRS: ImagePair[] = [
  { pairId: 'pair-1', imageA: '/mock-images/pair-1/a.jpg', imageB: '/mock-images/pair-1/b.jpg' },
  { pairId: 'pair-2', imageA: '/mock-images/pair-2/a.jpg', imageB: '/mock-images/pair-2/b.jpg' },
  { pairId: 'pair-3', imageA: '/mock-images/pair-3/a.jpg', imageB: '/mock-images/pair-3/b.jpg' },
  { pairId: 'pair-4', imageA: '/mock-images/pair-4/a.jpg', imageB: '/mock-images/pair-4/b.jpg' },
  { pairId: 'pair-5', imageA: '/mock-images/pair-5/a.jpg', imageB: '/mock-images/pair-5/b.jpg' },
]

let nextPairIndex = 0

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function fetchImagePair(): Promise<ImagePair> {
  await delay(400)
  const pair = MOCK_PAIRS[nextPairIndex % MOCK_PAIRS.length]
  nextPairIndex += 1
  return pair
}

export async function submitAnnotation(
  pairId: string,
  correspondences: Correspondence[],
): Promise<{ ok: true }> {
  await delay(300)
  console.info(`[mock backend] annotation submitted for ${pairId}:`, correspondences)
  return { ok: true }
}
