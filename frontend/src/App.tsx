import { useState } from 'react'

import { ChatPage } from './components/ChatPage'
import { LandingPage } from './components/LandingPage'
import type { AskQuestion } from './domain/answer'

export interface AppProps {
  askQuestion: AskQuestion
  initialView?: 'landing' | 'chat'
}

export function App({ askQuestion, initialView = 'landing' }: AppProps) {
  const [view, setView] = useState<'landing' | 'chat'>(initialView)

  if (view === 'chat') {
    return <ChatPage askQuestion={askQuestion} onBack={() => setView('landing')} />
  }

  return <LandingPage onStart={() => setView('chat')} />
}
