import {
  ArrowRight,
  BookOpenCheck,
  Check,
  FileCheck2,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

import { Brand } from './Brand'

interface LandingPageProps {
  onStart: () => void
}

const benefits = [
  {
    icon: Search,
    title: 'Recherche accélérée',
    text: 'Interrogez des centaines de pages en langage naturel et trouvez rapidement les passages utiles.',
  },
  {
    icon: FileCheck2,
    title: 'Réponses vérifiables',
    text: 'Chaque affirmation est reliée au texte, à l’article, à la version et à la page qui la fondent.',
  },
  {
    icon: BookOpenCheck,
    title: 'Raisonnement lisible',
    text: 'Julia sépare la règle, son analyse et les points à faire valider par un professionnel.',
  },
]

const domains = [
  ['Fiscalité béninoise', 'Code général des impôts, arrêtés et procédures DGI', true],
  ['Droit OHADA', 'Actes uniformes et droit des affaires', false],
  ['Droit social', 'Code du travail et textes sociaux', false],
  ['Comptabilité', 'SYSCOHADA et référentiels comptables', false],
] as const

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="container site-header__inner">
          <a href="#top" className="brand-link" aria-label="Vitalia, accueil">
            <Brand inverted />
          </a>
          <nav aria-label="Navigation principale">
            <a href="#plateforme">Plateforme</a>
            <a href="#domaines">Domaines</a>
            <a href="#confiance">Confiance</a>
          </nav>
          <button className="button button--header" type="button" onClick={onStart}>
            Essayer Julia <ArrowRight size={16} />
          </button>
        </div>
      </header>

      <main>
        <section className="hero" id="top">
          <div className="hero__glow hero__glow--one" />
          <div className="hero__glow hero__glow--two" />
          <div className="container hero__grid">
            <div className="hero__content">
              <div className="eyebrow">
                <Sparkles size={15} /> Une IA juridique pensée pour l’Afrique
              </div>
              <h1>L'intelligence juridique au service du droit africain.</h1>
              <p className="hero__lead">
                Recherchez, comprenez et vérifiez les textes fiscaux béninois avec
                Julia, l’assistante qui cite précisément ses sources.
              </p>
              <div className="hero__actions">
                <button className="button button--primary" type="button" onClick={onStart}>
                  Poser une question <ArrowRight size={18} />
                </button>
                <a className="button button--ghost" href="#plateforme">
                  Découvrir la plateforme
                </a>
              </div>
              <div className="hero__proof">
                <span><Check size={14} /> Sources officielles</span>
                <span><Check size={14} /> Références vérifiables</span>
                <span><Check size={14} /> Données maîtrisées</span>
              </div>
            </div>

            <div className="answer-preview" aria-label="Aperçu d’une réponse sourcée">
              <div className="answer-preview__top">
                <div className="avatar avatar--julia">J</div>
                <div><strong>Julia</strong><small>Assistante juridique</small></div>
                <span className="live-pill"><i /> Aperçu de l’interface</span>
              </div>
              <p className="answer-preview__question">
                Comment Julia présente-t-elle une réponse juridique ?
              </p>
              <div className="answer-preview__answer">
                <span className="answer-label">Format de réponse</span>
                <p>
                  Une synthèse concise, suivie des textes qui permettent de vérifier
                  chaque affirmation.
                </p>
                <div className="citation-line">
                  <span>1</span>
                  <div>
                    <strong>Source officielle retournée par Julia</strong>
                    <small>Article · version · page · statut</small>
                  </div>
                  <ArrowRight size={16} />
                </div>
              </div>
              <p className="answer-preview__foot">
                <ShieldCheck size={15} /> Pas de source, pas d’affirmation juridique.
              </p>
            </div>
          </div>
        </section>

        <section className="section section--light" id="plateforme">
          <div className="container">
            <div className="section-heading">
              <span className="section-kicker">Une recherche plus fiable</span>
              <h2>Du texte officiel à une réponse exploitable.</h2>
              <p>
                Julia transforme un corpus juridique complexe en réponses claires,
                tout en vous laissant le contrôle de la vérification.
              </p>
            </div>
            <div className="benefit-grid">
              {benefits.map(({ icon: Icon, title, text }, index) => (
                <article className="benefit-card" key={title}>
                  <span className="benefit-card__index">0{index + 1}</span>
                  <span className="benefit-card__icon"><Icon size={22} /></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section section--domains" id="domaines">
          <div className="container domains-layout">
            <div className="section-heading section-heading--left">
              <span className="section-kicker">Corpus maîtrisé</span>
              <h2>Nous ouvrons chaque domaine après vérification.</h2>
              <p>
                La fiscalité béninoise constitue le premier périmètre. Les autres
                domaines seront activés progressivement.
              </p>
            </div>
            <div className="domain-list">
              {domains.map(([title, text, active]) => (
                <article className={`domain-row${active ? ' domain-row--active' : ''}`} key={title}>
                  <span className="domain-row__state">{active ? <Check size={17} /> : null}</span>
                  <div><h3>{title}</h3><p>{text}</p></div>
                  <span className="domain-row__badge">{active ? 'Disponible' : 'Bientôt'}</span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="trust-section" id="confiance">
          <div className="container trust-section__grid">
            <div>
              <span className="section-kicker section-kicker--dark">Notre principe</span>
              <h2>Des réponses fondées sur les textes, pas sur des suppositions.</h2>
            </div>
            <div className="trust-rules">
              <div><strong>01</strong><p>Sans passage pertinent dans le corpus, Julia refuse de conclure.</p></div>
              <div><strong>02</strong><p>La règle juridique est distinguée de l’analyse produite par l’IA.</p></div>
              <div><strong>03</strong><p>Les extraits cités sont relus depuis la base documentaire.</p></div>
            </div>
          </div>
        </section>

        <section className="cta-section">
          <div className="container cta-card">
            <div><span>Julia est prête</span><h2>Posez votre première question juridique.</h2></div>
            <button className="button button--primary" type="button" onClick={onStart}>
              Démarrer la recherche <ArrowRight size={18} />
            </button>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="container site-footer__inner">
          <Brand />
          <p>Outil d’aide à la recherche — ne remplace pas le conseil d’un professionnel.</p>
          <span>© 2026 Vitalia</span>
        </div>
      </footer>
    </div>
  )
}
