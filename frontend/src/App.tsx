import { useState } from 'react'
import AnnotateGame from './components/AnnotateGame'
import HomeScreen from './components/HomeScreen'
import type { GameId } from './components/HomeScreen'

function App() {
  const [screen, setScreen] = useState<GameId | 'home'>('home')

  if (screen === 'annotate') {
    return <AnnotateGame onBack={() => setScreen('home')} />
  }

  return <HomeScreen onPlay={setScreen} />
}

export default App
