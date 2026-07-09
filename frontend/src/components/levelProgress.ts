export interface LevelProgress {
  level: number
  /** Exp earned since entering the current level. */
  currentLevelExp: number
  /** Exp needed, from the start of the current level, to reach the next one. */
  expToNextLevel: number
  /** `currentLevelExp / expToNextLevel`, in [0, 1]. */
  progressFraction: number
}

/**
 * Exp needed to advance from `level` to `level + 1`. Level 1 -> 2 costs a
 * flat 25; every level after that costs `level * 5` more than the last.
 */
function levelUpCost(level: number): number {
  return level === 1 ? 25 : level * 5
}

/** Derives the user's level and progress toward the next one from their total exp. */
export function computeLevelProgress(exp: number): LevelProgress {
  let level = 1
  let remaining = Math.max(0, exp)
  let cost = levelUpCost(level)

  while (remaining >= cost) {
    remaining -= cost
    level += 1
    cost = levelUpCost(level)
  }

  return {
    level,
    currentLevelExp: remaining,
    expToNextLevel: cost,
    progressFraction: cost > 0 ? remaining / cost : 0,
  }
}
