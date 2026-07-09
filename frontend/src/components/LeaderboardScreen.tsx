import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchLeaderboard, LEADERBOARD_PAGE_SIZE } from '../api/leaderboardApi'
import type { LeaderboardEntry } from '../api/leaderboardApi'
import type { User } from '../api/types'
import { computeLevelProgress } from './levelProgress'
import './LeaderboardScreen.css'

/** Medal glyph for the top three ranks; plain number otherwise. */
function rankMark(rank: number): string {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return `${rank}`
}

export default function LeaderboardScreen({ user, onBack }: { user: User; onBack: () => void }) {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // A ref mirrors `loading` so the IntersectionObserver callback (a stable
  // closure) can guard against firing overlapping loads without re-subscribing.
  const loadingRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const loadMore = useCallback(() => {
    if (loadingRef.current) return
    loadingRef.current = true
    setLoading(true)
    setError(null)
    // Offset is simply how many rows we already hold; the list only ever grows.
    setEntries((current) => {
      fetchLeaderboard(current.length, LEADERBOARD_PAGE_SIZE)
        .then((page) => {
          setTotal(page.total)
          // Append by rank so a concurrent signup can't duplicate a row already shown.
          setEntries((prev) => {
            const seen = new Set(prev.map((e) => e.rank))
            return [...prev, ...page.entries.filter((e) => !seen.has(e.rank))]
          })
        })
        .catch(() => setError('Could not load the leaderboard. Please try again.'))
        .finally(() => {
          loadingRef.current = false
          setLoading(false)
        })
      return current
    })
  }, [])

  // Initial page.
  useEffect(() => {
    loadMore()
  }, [loadMore])

  const hasMore = total === null || entries.length < total

  // Load the next page whenever the bottom sentinel scrolls into view.
  useEffect(() => {
    const node = sentinelRef.current
    if (!node || !hasMore) return
    const observer = new IntersectionObserver(
      (observed) => {
        if (observed[0]?.isIntersecting) loadMore()
      },
      { rootMargin: '200px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [hasMore, loadMore])

  return (
    <div className="game-screen">
      <header className="game-header">
        <div className="game-header-top">
          <button type="button" className="back-link" onClick={onBack}>
            ← Back to games
          </button>
        </div>
        <h1>Leaderboard</h1>
        <p>Every player ranked by experience points{total !== null ? ` · ${total} players` : ''}.</p>
      </header>

      <ol className="leaderboard-list">
        {entries.map((entry) => {
          const isMe = entry.uuid === user.uuid
          const { level } = computeLevelProgress(entry.exp)
          return (
            <li
              key={entry.uuid}
              className={`leaderboard-row${isMe ? ' leaderboard-row-me' : ''}${entry.rank <= 3 ? ' leaderboard-row-top' : ''}`}
            >
              <span className="leaderboard-rank">{rankMark(entry.rank)}</span>
              <span className="leaderboard-name">
                {entry.username}
                {isMe && <span className="leaderboard-you">You</span>}
              </span>
              <span className="leaderboard-level">Lvl {level}</span>
              <span className="leaderboard-exp">
                {entry.exp.toLocaleString()} <span className="leaderboard-exp-unit">XP</span>
              </span>
            </li>
          )
        })}
      </ol>

      {error && <p className="game-status game-status-error">{error}</p>}
      {loading && <p className="game-status">Loading…</p>}
      {!error && !loading && entries.length === 0 && <p className="game-status">No players yet.</p>}
      {!error && !hasMore && entries.length > 0 && (
        <p className="game-status leaderboard-end">You've reached the end.</p>
      )}

      {/* Sentinel: when it scrolls into view, the next page loads. */}
      <div ref={sentinelRef} aria-hidden="true" />
    </div>
  )
}
