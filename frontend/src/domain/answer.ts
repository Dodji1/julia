export interface AnswerSource {
  citationId: string
  documentId: string
  title: string
  article?: string
  page?: number
  version?: string
  status: 'en_vigueur' | 'archive' | 'a_verifier'
  excerpt: string
  documentUrl: string
  isOcr: boolean
}

export interface AnswerResponse {
  requestId: string
  conversationId: string
  status: 'answered' | 'insufficient_sources' | 'clarification_required'
  answerMarkdown: string
  sources: AnswerSource[]
}

export interface AskQuestionInput {
  question: string
  filters: {
    domain: 'fiscal'
    jurisdiction: 'BJ'
  }
}

export type AskQuestion = (input: AskQuestionInput) => Promise<AnswerResponse>

export type FeedbackRating = 'up' | 'down'

export type SendFeedback = (input: {
  requestId: string
  rating: FeedbackRating
}) => Promise<void>
