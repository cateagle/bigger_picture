import { useEffect, useState } from 'react'
import { fetchDailyQuests } from '../api/questApi'

/**
 * The "Daily Quests" account-bar link, shared by HomeScreen and
 * RegionSelectScreen. Shows a checkmark once every one of today's quests is
 * completed, so a player can tell at a glance whether there's anything left
 * to do without opening the page. Refetches on every mount, which happens
 * naturally on navigating back from the quests page (route change).
 */
export default function DailyQuestsMenuLink({ onClick }: { onClick: () => void }) {
  const [allCompleted, setAllCompleted] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchDailyQuests()
      .then((data) => {
        if (!cancelled) setAllCompleted(data.quests.length > 0 && data.quests.every((q) => q.completed))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <button type="button" className="back-link" onClick={onClick}>
      Daily Quests
      {allCompleted && <span className="menu-link-check"> ✓</span>}
    </button>
  )
}
