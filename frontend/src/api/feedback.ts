import type { SendFeedback } from '../domain/answer'
import { type Fetcher, getClientId, toApiError } from './client'

export function createFeedbackClient(fetcher: Fetcher = fetch): SendFeedback {
  return async ({ requestId, rating }) => {
    const response = await fetcher('/api/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Client-Id': getClientId() },
      body: JSON.stringify({ request_id: requestId, rating }),
    })

    if (!response.ok) {
      throw await toApiError(response)
    }
  }
}
