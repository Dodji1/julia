import { z } from 'zod'

export type Fetcher = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>

/** Erreur renvoyée par l'API, avec le message destiné à l'utilisateur. */
export class ApiRequestError extends Error {
  readonly status: number
  readonly code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = code
  }
}

const errorSchema = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
})

export async function toApiError(response: Response): Promise<ApiRequestError> {
  try {
    const parsed = errorSchema.safeParse(await response.json())
    if (parsed.success) {
      return new ApiRequestError(parsed.data.error.message, response.status, parsed.data.error.code)
    }
  } catch {
    // Corps absent ou non JSON : message générique ci-dessous.
  }
  return new ApiRequestError(`La requête a échoué (${response.status}).`, response.status)
}

const CLIENT_ID_KEY = 'julia-client-id'
let memoryClientId: string | undefined

/**
 * Identifiant anonyme du navigateur, envoyé dans l'en-tête X-Client-Id. La limite de débit porte
 * sur le navigateur, car toute une salle peut partager la même adresse IP.
 */
export function getClientId(storage: Storage | null = defaultStorage()): string {
  try {
    const stored = storage?.getItem(CLIENT_ID_KEY)
    if (stored) return stored
  } catch {
    // Stockage indisponible (navigation privée stricte) : l'identifiant reste en mémoire.
  }
  memoryClientId ??= newClientId()
  try {
    storage?.setItem(CLIENT_ID_KEY, memoryClientId)
  } catch {
    // Même cas que ci-dessus.
  }
  return memoryClientId
}

function newClientId(): string {
  // randomUUID n'existe qu'en contexte sécurisé (HTTPS ou localhost).
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

function defaultStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}
