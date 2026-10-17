import { describe, expect, it, vi } from 'vitest'

import { ApiRequestError, getClientId, toApiError } from './client'
import { createFeedbackClient } from './feedback'

function memoryStorage(): Storage {
  const values = new Map<string, string>()
  return {
    get length() {
      return values.size
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => void values.delete(key),
    setItem: (key, value) => void values.set(key, value),
  }
}

describe('client identifier', () => {
  it('is generated once, stored and reused', () => {
    const storage = memoryStorage()

    const first = getClientId(storage)

    expect(first).toMatch(/^[A-Za-z0-9-]{8,64}$/)
    expect(getClientId(storage)).toBe(first)
    expect(storage.getItem('julia-client-id')).toBe(first)
  })

  it('keeps an identifier already stored by the browser', () => {
    const storage = memoryStorage()
    storage.setItem('julia-client-id', 'navigateur-existant-01')

    expect(getClientId(storage)).toBe('navigateur-existant-01')
  })
})

describe('API errors', () => {
  it('exposes the message written by the API for the user', async () => {
    const response = new Response(
      JSON.stringify({ error: { code: 'RATE_LIMITED', message: 'Réessayez dans 30 s.', request_id: 'r1' } }),
      { status: 429 },
    )

    const error = await toApiError(response)

    expect(error).toBeInstanceOf(ApiRequestError)
    expect(error).toMatchObject({ message: 'Réessayez dans 30 s.', status: 429, code: 'RATE_LIMITED' })
  })

  it('falls back to a generic message when the body is not the API format', async () => {
    const error = await toApiError(new Response('Bad gateway', { status: 502 }))

    expect(error.message).toBe('La requête a échoué (502).')
  })
})

describe('feedback client', () => {
  it('sends the rating of an answer to the API', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))

    await createFeedbackClient(fetcher)({ requestId: 'req-9', rating: 'down' })

    const [url, init] = fetcher.mock.calls[0]
    expect(url).toBe('/api/v1/feedback')
    expect(JSON.parse(init.body)).toEqual({ request_id: 'req-9', rating: 'down' })
    expect(init.headers['X-Client-Id']).toMatch(/^[A-Za-z0-9-]{8,64}$/)
  })
})
