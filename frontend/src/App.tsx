import { useEffect, useState } from 'react'
import AdminScreen from './components/AdminScreen'
import AnnotateGame from './components/AnnotateGame'
import OverlapGame from './components/OverlapGame'
import VerifyGame from './components/VerifyGame'
import HomeScreen from './components/HomeScreen'
import LoginScreen from './components/LoginScreen'
import RegionSelectScreen from './components/RegionSelectScreen'
import type { GameId } from './components/HomeScreen'
import { logout, me } from './api/authApi'
import type { Region, User } from './api/types'

function App() {
  const [screen, setScreen] = useState<GameId | 'home' | 'admin'>('home')
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null)

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const handleLogout = () => {
    logout().finally(() => {
      setUser(null)
      setScreen('home')
      setSelectedRegion(null)
    })
  }

  if (user === undefined) {
    return <p className="game-status">Loading…</p>
  }

  if (user === null) {
    return <LoginScreen onLoggedIn={setUser} />
  }

  if (screen === 'admin') {
    return <AdminScreen user={user} onBack={() => setScreen('home')} />
  }

  if (selectedRegion === null) {
    return (
      <RegionSelectScreen
        user={user}
        onSelect={setSelectedRegion}
        onOpenAdmin={() => setScreen('admin')}
        onLogout={handleLogout}
      />
    )
  }

  if (screen === 'overlap') {
    return <OverlapGame region={selectedRegion} onBack={() => setScreen('home')} />
  }

  if (screen === 'annotate') {
    return <AnnotateGame region={selectedRegion} onBack={() => setScreen('home')} />
  }

  if (screen === 'verify') {
    return <VerifyGame region={selectedRegion} onBack={() => setScreen('home')} />
  }

  return (
    <HomeScreen
      onPlay={setScreen}
      user={user}
      region={selectedRegion}
      onChangeRegion={() => setSelectedRegion(null)}
      onOpenAdmin={() => setScreen('admin')}
      onLogout={handleLogout}
    />
  )
}

export default App
