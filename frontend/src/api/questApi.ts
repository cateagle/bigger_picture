import { apiFetch } from './client'

/** Mirrors `QuestResponse` from `backend/src/models/annotate.py`. */
export interface Quest {
  key: string
  title: string
  description: string
  metric: string
  target: number
  /** Confirmed count so far today, capped at `target`. */
  progress: number
  completed: boolean
  claimed: boolean
  reward_exp: number
}

/** Mirrors `DailyQuestsResponse` from `backend/src/models/annotate.py`. */
export interface DailyQuests {
  day_start_ms: number
  quests: Quest[]
}

/** Mirrors `QuestClaimResponse` from `backend/src/models/annotate.py`. */
export interface QuestClaim {
  quest: Quest
  exp: number
  expert_level: number
}

/**
 * Real endpoint: GET /api/v1/annotate/quests/me. Returns today's daily quests
 * (the same set for every player, rotating daily) with the signed-in player's
 * confirmed progress toward each.
 */
export function fetchDailyQuests(): Promise<DailyQuests> {
  return apiFetch<DailyQuests>('/api/v1/annotate/quests/me')
}

/**
 * Real endpoint: POST /api/v1/annotate/quests/{key}/claim. Claims a completed
 * quest's XP reward (once per player per quest per day) and returns the player's
 * new total XP/level.
 */
export function claimQuest(key: string): Promise<QuestClaim> {
  return apiFetch<QuestClaim>(`/api/v1/annotate/quests/${encodeURIComponent(key)}/claim`, {
    method: 'POST',
  })
}
