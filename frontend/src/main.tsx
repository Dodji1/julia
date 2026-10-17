import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import { createAnswerClient } from './api/answers'
import { createFeedbackClient } from './api/feedback'
import { createMockAnswerClient } from './api/mockAnswers'
import './styles.css'

const live = import.meta.env.VITE_API_MODE === 'live'
const askQuestion = live ? createAnswerClient() : createMockAnswerClient()
const sendFeedback = live ? createFeedbackClient() : async () => {}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App askQuestion={askQuestion} sendFeedback={sendFeedback} />
  </StrictMode>,
)
