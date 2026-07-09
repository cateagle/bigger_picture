import { computeLevelProgress } from './levelProgress'

export function LevelBadge({ exp }: { exp: number }) {
  const { level, currentLevelExp, expToNextLevel, progressFraction } = computeLevelProgress(exp)

  return (
    <span className="level-badge" title={`${currentLevelExp} / ${expToNextLevel} XP to level ${level + 1}`}>
      <span className="level-badge-label">Level {level}</span>
      <span className="level-badge-bar">
        <span className="level-badge-bar-fill" style={{ width: `${progressFraction * 100}%` }} />
      </span>
      <span className="level-badge-exp">
        {currentLevelExp}/{expToNextLevel} XP
      </span>
    </span>
  )
}
