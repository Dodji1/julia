import { describe, expect, it, vi } from 'vitest'

import { createAnswerClient } from './answers'

describe('answer API client', () => {
  it('validates and maps the FastAPI response contract', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          request_id: 'req-1',
          conversation_id: 'conv-1',
          status: 'answered',
          answer_markdown: 'La réponse est fondée sur le CGI. [1]',
          sources: [
            {
              citation_id: '1',
              document_id: 'cgi-2026',
              title: 'Code général des impôts 2026',
              article: '12',
              page: 42,
              version: '2026',
              status: 'en_vigueur',
              excerpt: 'Extrait officiel.',
              document_url: '/api/v1/documents/cgi-2026?page=42',
              is_ocr: false,
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    const askQuestion = createAnswerClient(fetcher)

    const answer = await askQuestion({
      question: 'Quel est le texte applicable ?',
      filters: { domain: 'fiscal', jurisdiction: 'BJ' },
    })

    expect(fetcher).toHaveBeenCalledWith(
      '/api/v1/answers',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          question: 'Quel est le texte applicable ?',
          filters: { domain: 'fiscal', jurisdiction: 'BJ' },
        }),
      }),
    )
    expect(answer.sources[0]).toMatchObject({
      citationId: '1',
      documentId: 'cgi-2026',
      isOcr: false,
      status: 'en_vigueur',
    })
  })
})
