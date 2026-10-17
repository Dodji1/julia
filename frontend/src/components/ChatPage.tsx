import {
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  ArrowLeft,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Copy,
  ExternalLink,
  FileText,
  Menu,
  MessageSquareText,
  Plus,
  Scale,
  Search,
  ShieldAlert,
  ThumbsDown,
  ThumbsUp,
  X,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'

import { ApiRequestError } from '../api/client'
import type {
  AnswerResponse,
  AnswerSource,
  AskQuestion,
  FeedbackRating,
  SendFeedback,
} from '../domain/answer'
import { Brand } from './Brand'

interface ChatPageProps {
  askQuestion: AskQuestion
  sendFeedback?: SendFeedback
  onBack: () => void
}

const suggestions = [
  'Quel est le régime fiscal des petites entreprises ?',
  'Comment fonctionne le remboursement d’un crédit de TVA ?',
  'Quelles sont les obligations liées aux factures normalisées ?',
]

const sourceStatus = {
  en_vigueur: { label: 'En vigueur', className: 'source-status--active' },
  archive: { label: 'Archivé', className: 'source-status--archived' },
  a_verifier: { label: 'À vérifier', className: 'source-status--review' },
} as const

export function ChatPage({ askQuestion, sendFeedback, onBack }: ChatPageProps) {
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null)
  const [answer, setAnswer] = useState<AnswerResponse | null>(null)
  const [selectedSource, setSelectedSource] = useState<AnswerSource | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<FeedbackRating | null>(null)
  const questionRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => questionRef.current?.focus(), [])

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    const value = question.trim()
    if (value.length < 3 || isLoading) return

    setIsLoading(true)
    setError(null)
    setSelectedSource(null)
    setCopied(false)

    try {
      const response = await askQuestion({
        question: value,
        filters: { domain: 'fiscal', jurisdiction: 'BJ' },
      })
      setSubmittedQuestion(value)
      setAnswer(response)
      setFeedback(null)
      setQuestion('')
    } catch (caught) {
      // Les erreurs de l'API (limite atteinte, service indisponible) portent un message lisible.
      setError(
        caught instanceof ApiRequestError
          ? caught.message
          : 'Impossible de joindre le service juridique. Vérifiez votre connexion et réessayez.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  function handleComposerKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submitQuestion()
    }
  }

  useEffect(() => {
    if (!selectedSource) return

    function closeSourceDrawer(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') setSelectedSource(null)
    }

    document.addEventListener('keydown', closeSourceDrawer)
    return () => document.removeEventListener('keydown', closeSourceDrawer)
  }, [selectedSource])

  function startNewChat() {
    setSubmittedQuestion(null)
    setAnswer(null)
    setError(null)
    setSelectedSource(null)
    setQuestion('')
    setCopied(false)
    setFeedback(null)
    setSidebarOpen(false)
    requestAnimationFrame(() => questionRef.current?.focus())
  }

  async function copyAnswer() {
    if (!answer) return
    await navigator.clipboard.writeText(answer.answerMarkdown)
    setCopied(true)
  }

  async function rateAnswer(rating: FeedbackRating) {
    if (!answer || feedback) return
    setFeedback(rating)
    try {
      await sendFeedback?.({ requestId: answer.requestId, rating })
    } catch (caught) {
      // L'avis est facultatif : son échec ne doit pas gêner la lecture de la réponse.
      console.warn('Avis non enregistré', caught)
    }
  }

  return (
    <div className="chat-shell">
      <aside className={`chat-sidebar${sidebarOpen ? ' chat-sidebar--open' : ''}`}>
        <div className="chat-sidebar__top">
          <button className="brand-button" type="button" onClick={onBack} aria-label="Retour à l’accueil">
            <Brand inverted />
          </button>
          <button className="mobile-close" type="button" onClick={() => setSidebarOpen(false)} aria-label="Fermer le menu"><X size={20} /></button>
        </div>
        <button className="new-chat" type="button" onClick={startNewChat}>
          <Plus size={18} /> Nouvelle conversation
        </button>
        <div className="history-search">
          <Search size={16} />
          <span>Rechercher</span>
          <kbd>⌘ K</kbd>
        </div>
        <div className="sidebar-label">Aujourd’hui</div>
        <button className="history-item history-item--active" type="button">
          <MessageSquareText size={16} />
          <span>{submittedQuestion ?? 'Nouvelle recherche juridique'}</span>
        </button>
        <div className="chat-sidebar__spacer" />
        <div className="corpus-state">
          <div><CheckCircle2 size={17} /><strong>Corpus fiscal actif</strong></div>
          <p>Bénin · Mise à jour 2026</p>
        </div>
        <div className="profile-row">
          <span>JD</span>
          <div><strong>Juriste démo</strong><small>Version congrès</small></div>
          <ChevronRight size={16} />
        </div>
      </aside>

      {sidebarOpen && <button className="sidebar-scrim" type="button" aria-label="Fermer le menu" onClick={() => setSidebarOpen(false)} />}

      <main className="chat-main">
        <header className="chat-header">
          <button className="icon-button menu-button" type="button" onClick={() => setSidebarOpen(true)} aria-label="Ouvrir le menu"><Menu size={20} /></button>
          <div className="chat-header__title">
            <span className="julia-mark"><Scale size={17} /></span>
            <div><h1>Julia</h1><p><i /> Assistante juridique sourcée</p></div>
          </div>
          <div className="chat-context"><BookOpen size={15} /> Fiscalité · Bénin</div>
          <button className="back-button" type="button" onClick={onBack}><ArrowLeft size={16} /> <span>Retour au site</span></button>
        </header>

        <div className="chat-feed">
          <div className="chat-feed__inner">
            {!submittedQuestion && !isLoading && !error && (
              <section className="chat-welcome">
                <div className="welcome-mark"><Scale size={28} /></div>
                <span className="welcome-kicker">Assistant juridique Vitalia</span>
                <h2>Que souhaitez-vous vérifier ?</h2>
                <p>
                  Posez une question précise. Julia recherche dans les textes fiscaux
                  béninois et vous répond avec leurs références.
                </p>
                <div className="suggestion-list">
                  {suggestions.map((suggestion) => (
                    <button type="button" key={suggestion} onClick={() => { setQuestion(suggestion); questionRef.current?.focus() }}>
                      <span>{suggestion}</span><ArrowUp size={16} />
                    </button>
                  ))}
                </div>
              </section>
            )}

            {submittedQuestion && (
              <article className="user-message" aria-label="Votre question">
                {submittedQuestion}
              </article>
            )}

            {isLoading && (
              <div className="assistant-message assistant-message--loading" role="status">
                <div className="assistant-message__identity"><span>J</span><strong>Julia recherche dans les textes</strong></div>
                <div className="thinking-line"><i /><i /><i /></div>
                <p>Analyse de la question et vérification des passages pertinents…</p>
              </div>
            )}

            {error && (
              <div className="error-message" role="alert">
                <ShieldAlert size={20} /><div><strong>La recherche n’a pas abouti</strong><p>{error}</p></div>
              </div>
            )}

            {answer && !isLoading && (
              <article className="assistant-message" aria-label="Réponse de Julia">
                <div className="assistant-message__identity"><span>J</span><div><strong>Julia</strong><small>Réponse fondée sur le corpus</small></div></div>
                {answer.status === 'insufficient_sources' && (
                  <div className="source-warning" role="status">
                    <ShieldAlert size={18} />
                    <span>Aucune source juridique suffisamment pertinente n’a été trouvée.</span>
                  </div>
                )}
                <div className="answer-body"><ReactMarkdown>{answer.answerMarkdown}</ReactMarkdown></div>
                {answer.sources.length > 0 && (
                  <div className="sources-block">
                    <div className="sources-block__title"><FileText size={16} /><strong>Sources citées</strong><span>{answer.sources.length}</span></div>
                    <div className="sources-grid">
                      {answer.sources.map((source) => (
                        <button key={source.citationId} className="source-card" type="button" aria-label={`Source ${source.citationId}`} onClick={() => setSelectedSource(source)}>
                          <span className="source-card__number">{source.citationId}</span>
                          <span className="source-card__content">
                            <strong>{source.title}</strong>
                            <small>{[source.article && `Article ${source.article}`, source.page && `Page ${source.page}`, source.version].filter(Boolean).join(' · ')}</small>
                          </span>
                          <ChevronRight size={17} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div className="answer-actions">
                  <button type="button" onClick={() => void copyAnswer()}>
                    {copied ? <CheckCircle2 size={15} /> : <Copy size={15} />}
                    {copied ? 'Copiée' : 'Copier'}
                  </button>
                  <span />
                  {feedback && <small className="feedback-thanks">Merci pour votre avis</small>}
                  <button
                    type="button"
                    aria-label="Réponse utile"
                    aria-pressed={feedback === 'up'}
                    disabled={feedback !== null}
                    onClick={() => void rateAnswer('up')}
                  >
                    <ThumbsUp size={15} />
                  </button>
                  <button
                    type="button"
                    aria-label="Réponse à améliorer"
                    aria-pressed={feedback === 'down'}
                    disabled={feedback !== null}
                    onClick={() => void rateAnswer('down')}
                  >
                    <ThumbsDown size={15} />
                  </button>
                </div>
              </article>
            )}
          </div>
        </div>

        <div className="composer-wrap">
          <form className="composer" onSubmit={submitQuestion}>
            <textarea
              id="question"
              ref={questionRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              rows={2}
              placeholder="Posez votre question juridique…"
              aria-label="Votre question juridique"
            />
            <div className="composer__bottom">
              <span className="scope-pill"><i /> Fiscalité béninoise</span>
              <span className="composer__hint">Entrée pour envoyer · Maj + Entrée pour une ligne</span>
              <button className="send-button" type="submit" disabled={question.trim().length < 3 || isLoading} aria-label="Envoyer">
                {isLoading ? <span className="spinner" /> : <ArrowUp size={18} />}
              </button>
            </div>
          </form>
          <p className="legal-note">Julia peut commettre des erreurs. Vérifiez les sources citées avant toute décision.</p>
        </div>
      </main>

      {selectedSource && (
        <>
          <button className="source-scrim" type="button" aria-label="Fermer le détail de la source" onClick={() => setSelectedSource(null)} />
          <aside className="source-drawer" aria-label="Détail de la source">
            <div className="source-drawer__header">
              <div><span>Source {selectedSource.citationId}</span><h2>{selectedSource.title}</h2></div>
              <button className="icon-button" type="button" onClick={() => setSelectedSource(null)} aria-label="Fermer"><X size={20} /></button>
            </div>
            <div className="source-meta">
              {selectedSource.article && <div><small>Référence</small><strong>Article {selectedSource.article}</strong></div>}
              {selectedSource.page && <div><small>Localisation</small><strong>Page {selectedSource.page}</strong></div>}
              {selectedSource.version && <div><small>Version</small><strong>{selectedSource.version}</strong></div>}
              <div>
                <small>Statut</small>
                <strong className={`source-status ${sourceStatus[selectedSource.status].className}`}>
                  <i /> {sourceStatus[selectedSource.status].label}
                </strong>
              </div>
            </div>
            <div className="source-excerpt">
              <span>Extrait du texte</span>
              <blockquote>{selectedSource.excerpt}</blockquote>
            </div>
            {selectedSource.isOcr && <div className="ocr-warning"><ShieldAlert size={17} /> Ce passage provient d’un OCR. Vérifiez-le sur l’original.</div>}
            <a className="document-link" href={selectedSource.documentUrl} target="_blank" rel="noreferrer">
              Voir le document original <ExternalLink size={16} />
            </a>
          </aside>
        </>
      )}
    </div>
  )
}
