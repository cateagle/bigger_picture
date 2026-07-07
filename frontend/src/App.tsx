import { useEffect, useState } from 'react'
import AnnotateGame from './components/AnnotateGame'
import OverlapGame from './components/OverlapGame'
import VerifyGame from './components/VerifyGame'
import HomeScreen from './components/HomeScreen'
import LoginScreen from './components/LoginScreen'
import type { GameId } from './components/HomeScreen'
import { logout, me } from './api/authApi'
import type { User } from './api/types'

function App() {
  const [screen, setScreen] = useState<GameId | 'home'>('home')
  const [user, setUser] = useState<User | null | undefined>(undefined)

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const handleLogout = () => {
    logout().finally(() => {
      setUser(null)
      setScreen('home')
    })
  }

  if (user === undefined) {
    return <p className="game-status">Loading…</p>
  }

  if (user === null) {
    return <LoginScreen onLoggedIn={setUser} />
  }

  if (screen === 'overlap') {
    return <OverlapGame onBack={() => setScreen('home')} />
  }

  if (screen === 'annotate') {
    return <AnnotateGame onBack={() => setScreen('home')} />
  }

  if (screen === 'verify') {
    return <VerifyGame onBack={() => setScreen('home')} />
  }

  return <HomeScreen onPlay={setScreen} user={user} onLogout={handleLogout} />
}

export default App
