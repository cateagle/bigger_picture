import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import AdminScreen from './components/AdminScreen'
import AnnotateGame from './components/AnnotateGame'
import OverlapGame from './components/OverlapGame'
import VerifyGame from './components/VerifyGame'
import DailyQuestsScreen from './components/DailyQuestsScreen'
import Footer from './components/Footer'
import HomeScreen from './components/HomeScreen'
import LoginScreen from './components/LoginScreen'
import MyStatsScreen from './components/MyStatsScreen'
import RegionSelectScreen from './components/RegionSelectScreen'
import TeamScreen from './components/TeamScreen'
import { logout, me } from './api/authApi'
import { fetchRegions } from './api/regionApi'
import type { Region, User } from './api/types'

function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null)

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  /** Re-fetches the logged-in user so exp/level stay current after game actions. */
  const refreshUser = useCallback(() => {
    me()
      .then(setUser)
      .catch(() => {})
  }, [])

  let content
  if (user === undefined) {
    content = <p className="game-status">Loading…</p>
  } else if (user === null) {
    content = <LoginScreen onLoggedIn={setUser} />
  } else {
    content = (
      <AppRoutes
        user={user}
        selectedRegion={selectedRegion}
        setSelectedRegion={setSelectedRegion}
        refreshUser={refreshUser}
        onLoggedOut={() => {
          setUser(null)
          setSelectedRegion(null)
        }}
      />
    )
  }

  return (
    <BrowserRouter>
      {content}
      <Footer showTeamLink={!!user} />
    </BrowserRouter>
  )
}

interface AppRoutesProps {
  user: User
  selectedRegion: Region | null
  setSelectedRegion: (region: Region | null) => void
  refreshUser: () => void
  onLoggedOut: () => void
}

/** The authenticated route table. Lives inside <BrowserRouter> so it can use navigation hooks. */
function AppRoutes({ user, selectedRegion, setSelectedRegion, refreshUser, onLoggedOut }: AppRoutesProps) {
  const navigate = useNavigate()

  const handleLogout = () => {
    logout().finally(() => {
      onLoggedOut()
      navigate('/')
    })
  }

  const selectRegion = (region: Region) => {
    setSelectedRegion(region)
    navigate(`/region/${region.uuid}`)
  }

  return (
    <Routes>
      <Route
        path="/"
        element={
          <RegionSelectScreen
            user={user}
            onSelect={selectRegion}
            onOpenAdmin={() => navigate('/admin')}
            onOpenStats={() => navigate('/stats')}
            onOpenQuests={() => navigate('/quests')}
            onLogout={handleLogout}
          />
        }
      />
      <Route path="/admin" element={<AdminScreen user={user} onBack={() => navigate('/')} />} />
      <Route path="/team" element={<TeamScreen onBack={() => navigate('/')} />} />
      <Route path="/stats" element={<MyStatsScreen user={user} onBack={() => navigate('/')} />} />
      <Route
        path="/quests"
        element={<DailyQuestsScreen user={user} onBack={() => navigate('/')} onUserRefresh={refreshUser} />}
      />
      <Route
        path="/region/:uuid"
        element={
          <RegionGate selectedRegion={selectedRegion} setSelectedRegion={setSelectedRegion}>
            {(region) => (
              <HomeScreen
                onPlay={(id) => navigate(`/region/${region.uuid}/${id}`)}
                user={user}
                region={region}
                onChangeRegion={() => {
                  setSelectedRegion(null)
                  navigate('/')
                }}
                onOpenAdmin={() => navigate('/admin')}
                onOpenStats={() => navigate('/stats')}
                onOpenQuests={() => navigate('/quests')}
                onLogout={handleLogout}
              />
            )}
          </RegionGate>
        }
      />
      <Route
        path="/region/:uuid/:game"
        element={
          <RegionGate selectedRegion={selectedRegion} setSelectedRegion={setSelectedRegion}>
            {(region) => (
              <GameRoute
                region={region}
                user={user}
                onUserRefresh={refreshUser}
                onBack={() => navigate(`/region/${region.uuid}`)}
              />
            )}
          </RegionGate>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

interface RegionGateProps {
  selectedRegion: Region | null
  setSelectedRegion: (region: Region | null) => void
  children: (region: Region) => ReactNode
}

/**
 * Ensures `selectedRegion` matches the `:uuid` in the URL before rendering region-scoped
 * screens. This makes region routes deep-linkable and reload-safe: if state was lost (e.g.
 * a hard refresh), the region is resolved from the API by uuid. Unknown uuids redirect home.
 */
function RegionGate({ selectedRegion, setSelectedRegion, children }: RegionGateProps) {
  const { uuid } = useParams()
  const [notFound, setNotFound] = useState(false)

  const matches = selectedRegion?.uuid === uuid

  useEffect(() => {
    if (matches) return
    let cancelled = false
    setNotFound(false)
    fetchRegions()
      .then((regions) => {
        if (cancelled) return
        const found = regions.find((r) => r.uuid === uuid)
        if (found) setSelectedRegion(found)
        else setNotFound(true)
      })
      .catch(() => {
        if (!cancelled) setNotFound(true)
      })
    return () => {
      cancelled = true
    }
  }, [uuid, matches, setSelectedRegion])

  if (notFound) return <Navigate to="/" replace />
  if (!matches || !selectedRegion) return <p className="game-status">Loading…</p>
  return <>{children(selectedRegion)}</>
}

interface GameRouteProps {
  region: Region
  user: User
  onUserRefresh: () => void
  onBack: () => void
}

/** Dispatches to the right game component based on the `:game` URL segment. */
function GameRoute({ region, user, onUserRefresh, onBack }: GameRouteProps) {
  const { game } = useParams()
  const props = { region, user, onUserRefresh, onBack }
  if (game === 'overlap') return <OverlapGame {...props} />
  if (game === 'annotate') return <AnnotateGame {...props} />
  if (game === 'verify') return <VerifyGame {...props} />
  return <Navigate to={`/region/${region.uuid}`} replace />
}

export default App
