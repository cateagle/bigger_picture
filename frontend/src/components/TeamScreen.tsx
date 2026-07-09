import './TeamScreen.css'

interface TeamMember {
  name: string
  githubHandle: string
}

/**
 * Pulled from the project's git history (`git log --format="%an <%ae>"`),
 * since there's no dedicated contributors list elsewhere in the repo.
 */
const TEAM: TeamMember[] = [
  { name: 'Sascha Mahmood', githubHandle: 'savenger' },
  { name: 'paschoentag', githubHandle: 'paschoentag' },
  { name: 'cateagle', githubHandle: 'cateagle' },
  { name: 'Paul C. Busch', githubHandle: 'chaosbit' },
  { name: 'Wiebke Engler', githubHandle: 'Wiebke-Engler' },
]

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export default function TeamScreen({ onBack }: { onBack: () => void }) {
  return (
    <div className="team-screen">
      <button type="button" className="back-link" onClick={onBack}>
        ← Back
      </button>

      <header className="team-header">
        <p className="team-eyebrow">Journey of the Eel</p>
        <h1>Team</h1>
        <p>The people who built Bigger Picture.</p>
      </header>

      <div className="team-photo" aria-hidden="true">
        {TEAM.map((member) => (
          <div key={member.githubHandle} className="team-avatar">
            {initials(member.name)}
          </div>
        ))}
      </div>
      <p className="team-photo-caption">No group photo yet — placeholder avatars shown above.</p>

      <ul className="team-list">
        {TEAM.map((member) => (
          <li key={member.githubHandle} className="team-list-item">
            <span className="team-name">{member.name}</span>
            <a
              className="team-contact"
              href={`https://github.com/${member.githubHandle}`}
              target="_blank"
              rel="noreferrer"
            >
              @{member.githubHandle}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
