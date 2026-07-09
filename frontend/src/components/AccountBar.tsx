import type { Region, User } from '../api/types'
import BurgerMenu from './BurgerMenu'
import DailyQuestsMenuLink from './DailyQuestsMenuLink'
import { LevelBadge } from './LevelBadge'

/** Shared top bar for HomeScreen and RegionSelectScreen: identity, region, and account actions. */
export default function AccountBar({
  user,
  region,
  onChangeRegion,
  onOpenAdmin,
  onOpenStats,
  onOpenQuests,
  onLogout,
}: {
  user: User
  region?: Region
  onChangeRegion?: () => void
  onOpenAdmin: () => void
  onOpenStats: () => void
  onOpenQuests: () => void
  onLogout: () => void
}) {
  return (
    <div className="account-bar">
      <span>
        Signed in as <strong>{user.username}</strong>
        {region && onChangeRegion && (
          <>
            {' · '}
            <button type="button" className="region-link" onClick={onChangeRegion}>
              Region: <strong>{region.title}</strong>
            </button>
          </>
        )}
      </span>
      <LevelBadge exp={user.exp} />
      <DailyQuestsMenuLink onClick={onOpenQuests} />
      <BurgerMenu
        showAdmin={user.role !== 'annotator'}
        onOpenAdmin={onOpenAdmin}
        onOpenStats={onOpenStats}
        onLogout={onLogout}
      />
    </div>
  )
}
