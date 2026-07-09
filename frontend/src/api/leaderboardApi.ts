import { apiFetch } from './client'

/** Mirrors `LeaderboardEntry` from `backend/src/models/annotate.py`. */
export interface LeaderboardEntry {
  /** 1-based position in the overall ranking, highest exp first. */
  rank: number
  uuid: string
  username: string
  exp: number
}

/** Mirrors `LeaderboardResponse` from `backend/src/models/annotate.py`. */
export interface LeaderboardPage {
  entries: LeaderboardEntry[]
  /** Total number of players, so the client knows when it has paged to the end. */
  total: number
}

/** How many entries the leaderboard loads per page / scroll. */
export const LEADERBOARD_PAGE_SIZE = 50

/**
 * Real endpoint: GET /api/v1/annotate/leaderboard. Returns one page of the
 * global ranking by experience points, highest first. Page with
 * `limit`/`offset`; `total` tells the caller when to stop.
 */
export function fetchLeaderboard(offset = 0, limit = LEADERBOARD_PAGE_SIZE): Promise<LeaderboardPage> {
  return apiFetch<LeaderboardPage>(`/api/v1/annotate/leaderboard?limit=${limit}&offset=${offset}`)
}
