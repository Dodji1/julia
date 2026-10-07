import { z } from 'zod'

import type { AnswerResponse, AskQuestion } from '../domain/answer'

const sourceSchema = z.object({
  citation_id: z.string(),
  document_id: z.string(),
  title: z.string(),
  article: z.string().nullish(),
  page: z.number().int().positive().nullish(),
  version: z.string().nullish(),
  status: z.enum(['en_vigueur', 'archive', 'a_verifier']),
  excerpt: z.string(),
  document_url: z.string(),
  is_ocr: z.boolean().default(false),
})

const answerSchema = z.object({
  request_id: z.string(),
  conversation_id: z.string(),
  status: z.enum(['answered', 'insufficient_sources', 'clarification_required']),
  answer_markdown: z.string(),
  sources: z.array(sourceSchema),
})

type Fetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>

export function createAnswerClient(fetcher: Fetcher = fetch): AskQuestion {
  return async (input) => {
    const response = await fetcher('/api/v1/answers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })

    if (!response.ok) {
      throw new Error(`La requête a échoué (${response.status}).`)
    }

    const payload = answerSchema.parse(await response.json())

    return {
      requestId: payload.request_id,
      conversationId: payload.conversation_id,
      status: payload.status,
      answerMarkdown: payload.answer_markdown,
      sources: payload.sources.map(
        (source): AnswerResponse['sources'][number] => ({
          citationId: source.citation_id,
          documentId: source.document_id,
          title: source.title,
          article: source.article ?? undefined,
          page: source.page ?? undefined,
          version: source.version ?? undefined,
          status: source.status,
          excerpt: source.excerpt,
          documentUrl: source.document_url,
          isOcr: source.is_ocr,
        }),
      ),
    }
  }
}
