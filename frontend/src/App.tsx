import { useState } from 'react'

import { ChatPage } from './components/ChatPage'
import { LandingPage } from './components/LandingPage'
import type { AskQuestion, SendFeedback } from './domain/answer'

export interface AppProps {
  askQuestion: AskQuestion
  sendFeedback?: SendFeedback
  initialView?: 'landing' | 'chat'
}

export function App({ askQuestion, sendFeedback, initialView = 'landing' }: AppProps) {
  const [view, setView] = useState<'landing' | 'chat'>(initialView)

  if (view === 'chat') {
    return (
      <ChatPage askQuestion={askQuestion} sendFeedback={sendFeedback} onBack={() => setView('landing')} />
    )
  }

  return <LandingPage onStart={() => setView('chat')} />
}
