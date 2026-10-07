import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import { createAnswerClient } from './api/answers'
import { createMockAnswerClient } from './api/mockAnswers'
import './styles.css'

const askQuestion =
  import.meta.env.VITE_API_MODE === 'live'
    ? createAnswerClient()
    : createMockAnswerClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App askQuestion={askQuestion} />
  </StrictMode>,
)
