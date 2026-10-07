import { describe, expect, it } from 'vitest'

import { createMockAnswerClient } from './mockAnswers'

describe('demo answer client', () => {
  it('returns a clearly sourced fiscal demonstration answer', async () => {
    const askQuestion = createMockAnswerClient({ delayMs: 0 })

    const answer = await askQuestion({
      question: 'Quel est le régime fiscal des petites entreprises ?',
      filters: { domain: 'fiscal', jurisdiction: 'BJ' },
    })

    expect(answer.status).toBe('answered')
    expect(answer.answerMarkdown).toContain('démonstration')
    expect(answer.sources).toEqual([
      expect.objectContaining({
        documentId: 'benin-code-general-des-impots-2026',
        isOcr: false,
        status: 'en_vigueur',
      }),
    ])
  })
})
