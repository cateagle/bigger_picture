import { useEffect, useState } from 'react'
import { fetchMyStats } from '../api/statsApi'
import type { AccuracyStat, MyStats } from '../api/statsApi'
import type { User } from '../api/types'
import './MyStatsScreen.css'

/** Format an accuracy fraction as a percentage, or "n/a" when nothing is reviewed yet. */
function formatAccuracy(stat: AccuracyStat): string {
  if (stat.accuracy === null) return 'n/a'
  return `${Math.round(stat.accuracy * 100)}%`
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat-cell">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function AccuracyRow({ window, allTime, windowed }: { window: number; allTime: AccuracyStat; windowed: AccuracyStat }) {
  return (
    <div className="stat-accuracy-row">
      <div className="stat-cell">
        <span className="stat-value">{formatAccuracy(allTime)}</span>
        <span className="stat-label">Accuracy (all time)</span>
        <span className="stat-sub">{allTime.correct}/{allTime.reviewed} reviewed</span>
      </div>
      <div className="stat-cell">
        <span className="stat-value">{formatAccuracy(windowed)}</span>
        <span className="stat-label">Accuracy (last {window})</span>
        <span className="stat-sub">{windowed.correct}/{windowed.reviewed} reviewed</span>
      </div>
    </div>
  )
}

export default function MyStatsScreen({ user, onBack }: { user: User; onBack: () => void }) {
  const [stats, setStats] = useState<MyStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMyStats()
      .then(setStats)
      .catch(() => setError('Could not load your statistics.'))
  }, [])

  return (
    <div className="game-screen">
      <header className="game-header">
        <button type="button" className="back-link" onClick={onBack}>
          ← Back to games
        </button>
        <h1>My Stats</h1>
        <p>Your contributions and accuracy across the three leagues, {user.username}.</p>
      </header>

      {error && <p className="game-status game-status-error">{error}</p>}
      {!error && !stats && <p className="game-status">Loading…</p>}

      {stats && (
        <>
          <section className="stat-section">
            <h2>Finding Overlap</h2>
            <div className="stat-grid">
              <Stat label="Pairs marked" value={stats.overlap.pairs_marked} />
              <Stat label="Overlaps found" value={stats.overlap.overlaps_found} />
              <Stat label="Overlapping pairs overall" value={stats.overlap.overall_pairs_with_overlap} />
            </div>
            <AccuracyRow
              window={stats.window}
              allTime={stats.overlap.accuracy_all_time}
              windowed={stats.overlap.accuracy_window}
            />
          </section>

          <section className="stat-section">
            <h2>Annotating</h2>
            <div className="stat-grid">
              <Stat label="Annotations" value={stats.annotate.annotations} />
              <Stat label="Annotations verified" value={stats.annotate.annotations_verified} />
              <Stat label="Pairs marked" value={stats.annotate.pairs_marked} />
              <Stat label="Pairs verified" value={stats.annotate.pairs_verified} />
            </div>
            <AccuracyRow
              window={stats.window}
              allTime={stats.annotate.accuracy_all_time}
              windowed={stats.annotate.accuracy_window}
            />
          </section>

          <section className="stat-section">
            <h2>Verification</h2>
            <div className="stat-grid">
              <Stat label="Reviews done" value={stats.verify.verified} />
              <Stat label="Accepted" value={stats.verify.accepted} />
              <Stat label="Faults found" value={stats.verify.faulty_found} />
            </div>
          </section>
        </>
      )}
    </div>
  )
}
