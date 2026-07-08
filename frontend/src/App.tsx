import { useEffect, useState } from 'react'
import AdminScreen from './components/AdminScreen'
import AnnotateGame from './components/AnnotateGame'
import OverlapGame from './components/OverlapGame'
import VerifyGame from './components/VerifyGame'
import Footer from './components/Footer'
import HomeScreen from './components/HomeScreen'
import LoginScreen from './components/LoginScreen'
import RegionSelectScreen from './components/RegionSelectScreen'
import TeamScreen from './components/TeamScreen'
import type { GameId } from './components/HomeScreen'
import { logout, me } from './api/authApi'
import type { Region, User } from './api/types'

function App() {
  const [screen, setScreen] = useState<GameId | 'home' | 'admin' | 'team'>('home')
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

  let content
  if (user === undefined) {
    content = <p className="game-status">Loading…</p>
  } else if (user === null) {
    content = <LoginScreen onLoggedIn={setUser} />
  } else if (screen === 'admin') {
    content = <AdminScreen user={user} onBack={() => setScreen('home')} />
  } else if (screen === 'team') {
    content = <TeamScreen onBack={() => setScreen('home')} />
  } else if (selectedRegion === null) {
    content = (
      <RegionSelectScreen
        user={user}
        onSelect={setSelectedRegion}
        onOpenAdmin={() => setScreen('admin')}
        onOpenTeam={() => setScreen('team')}
        onLogout={handleLogout}
      />
    )
  } else if (screen === 'overlap') {
    content = <OverlapGame region={selectedRegion} onBack={() => setScreen('home')} />
  } else if (screen === 'annotate') {
    content = <AnnotateGame region={selectedRegion} onBack={() => setScreen('home')} />
  } else if (screen === 'verify') {
    content = <VerifyGame region={selectedRegion} onBack={() => setScreen('home')} />
  } else {
    content = (
      <HomeScreen
        onPlay={setScreen}
        user={user}
        region={selectedRegion}
        onChangeRegion={() => setSelectedRegion(null)}
        onOpenAdmin={() => setScreen('admin')}
        onOpenTeam={() => setScreen('team')}
        onLogout={handleLogout}
      />
    )
  }

  return (
    <>
      {content}
      <Footer />
    </>
  )
}

export default App
