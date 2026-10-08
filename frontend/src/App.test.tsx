import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { App } from './App'

describe('Julia frontend', () => {
  it('opens the legal assistant from the landing page', async () => {
    const user = userEvent.setup()

    render(<App askQuestion={vi.fn()} />)

    expect(
      screen.getByRole('heading', {
        name: /l'intelligence juridique au service du droit africain/i,
      }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /poser une question/i }))

    expect(
      screen.getByRole('textbox', { name: /votre question juridique/i }),
    ).toHaveFocus()
  })

  it('renders a sourced answer and opens its citation details', async () => {
    const user = userEvent.setup()
    const askQuestion = vi.fn().mockResolvedValue({
      requestId: 'req-1',
      conversationId: 'conv-1',
      status: 'answered',
      answerMarkdown:
        "Le délai de déclaration est fixé par l'article applicable. [1]",
      sources: [
        {
          citationId: '1',
          documentId: 'cgi-2026',
          title: 'Code général des impôts du Bénin 2026',
          article: '123',
          page: 87,
          version: '2026',
          status: 'archive',
          excerpt: 'La déclaration doit être déposée dans le délai prévu.',
          documentUrl: '/api/v1/documents/cgi-2026?page=87',
          isOcr: false,
        },
      ],
    })

    render(<App askQuestion={askQuestion} initialView="chat" />)

    await user.type(
      screen.getByRole('textbox', { name: /votre question juridique/i }),
      'Quel est le délai de déclaration ?',
    )
    await user.click(screen.getByRole('button', { name: /envoyer/i }))

    expect(askQuestion).toHaveBeenCalledWith({
      question: 'Quel est le délai de déclaration ?',
      filters: { domain: 'fiscal', jurisdiction: 'BJ' },
    })
    expect(await screen.findByText(/le délai de déclaration est fixé/i)).toBeVisible()
    expect(
      screen.getByRole('article', { name: /votre question/i }),
    ).toHaveTextContent('Quel est le délai de déclaration ?')
    expect(
      screen.getByRole('textbox', { name: /votre question juridique/i }),
    ).toHaveValue('')

    await user.click(screen.getByRole('button', { name: /source 1/i }))

    const sourceDetails = screen.getByRole('complementary', {
      name: /détail de la source/i,
    })
    expect(
      within(sourceDetails).getByRole('heading', {
        name: /code général des impôts du bénin 2026/i,
      }),
    ).toBeVisible()
    expect(within(sourceDetails).getByText(/article 123/i)).toBeVisible()
    expect(within(sourceDetails).getByText(/page 87/i)).toBeVisible()
    expect(within(sourceDetails).getByText(/^archivé$/i)).toBeVisible()
    expect(within(sourceDetails).queryByText(/^en vigueur$/i)).not.toBeInTheDocument()
    expect(
      within(sourceDetails).getByText(/la déclaration doit être déposée/i),
    ).toBeVisible()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(
      screen.queryByRole('complementary', { name: /détail de la source/i }),
    ).not.toBeInTheDocument()
  })

  it('identifies an answer that has insufficient legal sources', async () => {
    const user = userEvent.setup()
    const askQuestion = vi.fn().mockResolvedValue({
      requestId: 'req-2',
      conversationId: 'conv-2',
      status: 'insufficient_sources',
      answerMarkdown:
        "Je n'ai pas trouvé de texte suffisamment pertinent pour répondre de manière fiable.",
      sources: [],
    })

    render(<App askQuestion={askQuestion} initialView="chat" />)

    await user.type(
      screen.getByRole('textbox', { name: /votre question juridique/i }),
      'Quelle règle fiscale répond à ce cas ?',
    )
    await user.click(screen.getByRole('button', { name: /envoyer/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      /aucune source juridique suffisamment pertinente/i,
    )
    expect(screen.queryByRole('button', { name: /source 1/i })).not.toBeInTheDocument()
  })

  it('keeps the question available when the API request fails', async () => {
    const user = userEvent.setup()
    const askQuestion = vi.fn().mockRejectedValue(new Error('Network error'))

    render(<App askQuestion={askQuestion} initialView="chat" />)

    const question = screen.getByRole('textbox', {
      name: /votre question juridique/i,
    })
    await user.type(question, 'La TVA est-elle applicable ?')
    await user.click(screen.getByRole('button', { name: /envoyer/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /impossible de joindre le service/i,
    )
    expect(question).toHaveValue('La TVA est-elle applicable ?')
  })

  it('copies the complete answer and confirms the action', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    const askQuestion = vi.fn().mockResolvedValue({
      requestId: 'req-copy',
      conversationId: 'conv-copy',
      status: 'answered',
      answerMarkdown: 'Réponse juridique à copier. [1]',
      sources: [],
    })

    render(<App askQuestion={askQuestion} initialView="chat" />)

    await user.type(
      screen.getByRole('textbox', { name: /votre question juridique/i }),
      'Copie cette réponse',
    )
    await user.click(screen.getByRole('button', { name: /envoyer/i }))
    await user.click(await screen.findByRole('button', { name: /^copier$/i }))

    expect(writeText).toHaveBeenCalledWith('Réponse juridique à copier. [1]')
    expect(screen.getByRole('button', { name: /copiée/i })).toBeVisible()
  })
})
