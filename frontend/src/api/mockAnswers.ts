import type { AskQuestion } from '../domain/answer'

interface MockAnswerOptions {
  delayMs?: number
}

export function createMockAnswerClient({ delayMs = 650 }: MockAnswerOptions = {}): AskQuestion {
  return async () => {
    if (delayMs > 0) {
      await new Promise((resolve) => window.setTimeout(resolve, delayMs))
    }

    return {
      requestId: `demo-${Date.now()}`,
      conversationId: 'demo-conversation',
      status: 'answered',
      answerMarkdown:
        '**Mode démonstration — contenu à valider juridiquement.**\n\nLe moteur RAG n’est pas encore connecté. Cette réponse illustre la présentation d’une analyse, de ses limites et de sa source. [1]',
      sources: [
        {
          citationId: '1',
          documentId: 'benin-code-general-des-impots-2026',
          title: 'Code général des impôts du Bénin 2026 — démonstration',
          version: '2026',
          status: 'en_vigueur',
          excerpt:
            'Emplacement réservé à l’extrait exact renvoyé par le backend. Aucun contenu juridique réel n’est simulé dans ce mode.',
          documentUrl: '#',
          isOcr: false,
        },
      ],
    }
  }
}
