import { useState } from 'react'
import AnnotateGame from './components/AnnotateGame'
import OverlapGame from './components/OverlapGame'
import VerifyGame from './components/VerifyGame'
import HomeScreen from './components/HomeScreen'
import type { GameId } from './components/HomeScreen'

function App() {
  const [screen, setScreen] = useState<GameId | 'home'>('home')

  if (screen === 'overlap') {
    return <OverlapGame onBack={() => setScreen('home')} />
  }

  if (screen === 'annotate') {
    return <AnnotateGame onBack={() => setScreen('home')} />
  }

  if (screen === 'verify') {
    return <VerifyGame onBack={() => setScreen('home')} />
  }

  return <HomeScreen onPlay={setScreen} />
}

export default App
