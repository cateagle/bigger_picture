import { apiFetch, assetUrl } from './client'
import type { CandidatePair } from './types'

/** Mirrors `NextPairImageResponse` from `backend/src/models/annotate.py` (only the fields used here). */
interface NextCandidateImage {
  uuid: string
  filepath: string
}

/** Mirrors `NextCandidateResponse` from `backend/src/models/annotate.py`. */
interface NextCandidateResponse {
  image1: NextCandidateImage
  image2: NextCandidateImage
  status: string | null
}

function toCandidatePair(candidate: NextCandidateResponse): CandidatePair {
  return {
    candidateId: `${candidate.image1.uuid}:${candidate.image2.uuid}`,
    imageA: assetUrl(candidate.image1.filepath),
    imageB: assetUrl(candidate.image2.filepath),
    imageAUuid: candidate.image1.uuid,
    imageBUuid: candidate.image2.uuid,
  }
}

/**
 * Real endpoint: GET /api/v1/annotate/candidate/next/{dive_uuid}. Resolves
 * `null` once there are no more open, unannotated candidate pairs left for
 * this player in the dive.
 */
export async function fetchNextCandidatePair(diveUuid: string): Promise<CandidatePair | null> {
  const candidates = await apiFetch<NextCandidateResponse[]>(`/api/v1/annotate/candidate/next/${diveUuid}`)
  return candidates.length > 0 ? toCandidatePair(candidates[0]) : null
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
