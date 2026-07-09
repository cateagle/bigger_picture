import { Link } from 'react-router-dom'
import './Footer.css'

const GITHUB_URL = 'https://github.com/paschoentag/bigger_picture'

export default function Footer({ showTeamLink }: { showTeamLink: boolean }) {
  return (
    <footer className="app-footer">
      <p>Thanks for helping build reliable training data. ❤️</p>
      <nav className="app-footer-links">
        {showTeamLink && <Link to="/team">Team</Link>}
        <a href={GITHUB_URL} target="_blank" rel="noreferrer">
          GitHub
        </a>
      </nav>
    </footer>
  )
}
