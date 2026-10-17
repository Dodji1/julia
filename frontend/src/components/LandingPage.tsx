import {
  ArrowRight,
  BookOpenCheck,
  Check,
  FileCheck2,
  Fingerprint,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

import { Brand } from './Brand'
import { LegalIntelligenceVisual } from './LegalIntelligenceVisual'

interface LandingPageProps {
  onStart: () => void
}

const benefits = [
  {
    icon: Search,
    label: 'Trouver',
    title: 'La bonne règle, sans parcourir des centaines de pages.',
    text: 'Formulez votre situation en langage naturel. Julia identifie les passages les plus pertinents dans le corpus activé.',
  },
  {
    icon: FileCheck2,
    label: 'Vérifier',
    title: 'Chaque affirmation revient au texte qui la fonde.',
    text: 'Article, version, page et statut : la preuve reste visible, consultable et prête à être contrôlée.',
  },
  {
    icon: BookOpenCheck,
    label: 'Comprendre',
    title: 'Une lecture claire qui respecte la nuance juridique.',
    text: 'La règle, son analyse et les limites de la réponse sont présentées distinctement pour mieux décider.',
  },
]

const domains = [
  ['Fiscalité béninoise', 'Code général des impôts, arrêtés et procédures DGI', true],
  ['Droit OHADA', 'Actes uniformes et droit des affaires', false],
  ['Droit social', 'Code du travail et textes sociaux', false],
  ['Comptabilité', 'SYSCOHADA et référentiels comptables', false],
] as const

const journey = [
  ['01', 'Questionnez', 'Décrivez votre situation comme vous la présenteriez à un confrère.'],
  ['02', 'Julia recherche', 'Le moteur parcourt uniquement le corpus juridique sélectionné.'],
  ['03', 'Vérifiez', 'La réponse et ses références apparaissent ensemble, sans boîte noire.'],
] as const

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <div className="site-shell">
      <header className="site-header">
        <div className="container site-header__inner">
          <a href="#top" className="brand-link" aria-label="Vitalia, accueil"><Brand inverted /></a>
          <nav aria-label="Navigation principale">
            <a href="#plateforme">Plateforme</a>
            <a href="#experience">Expérience</a>
            <a href="#domaines">Corpus</a>
            <a href="#confiance">Confiance</a>
          </nav>
          <button className="button button--header" type="button" onClick={onStart}>
            Ouvrir Julia <ArrowRight size={16} />
          </button>
        </div>
      </header>

      <main>
        <section className="hero" id="top">
          <div className="hero__aurora" aria-hidden="true" />
          <div className="container hero__grid">
            <div className="hero__content">
              <div className="eyebrow"><Sparkles size={15} /> Conçue pour les professionnels du droit africain</div>
              <h1>L'intelligence juridique <em>au service</em> du droit africain.</h1>
              <p className="hero__lead">
                Julia transforme les textes fiscaux béninois en réponses claires,
                traçables et immédiatement vérifiables.
              </p>
              <div className="hero__actions">
                <button className="button button--primary" type="button" onClick={onStart}>
                  Poser une question <ArrowRight size={18} />
                </button>
                <a className="button button--ghost" href="#experience">Voir comment ça marche</a>
              </div>
              <div className="hero__proof" aria-label="Principes de Julia">
                <span><Check size={14} /> Corpus maîtrisé</span>
                <span><Check size={14} /> Citations précises</span>
                <span><Check size={14} /> Réponse prudente</span>
              </div>
            </div>
            <LegalIntelligenceVisual />
          </div>
          <a className="hero__scroll" href="#plateforme" aria-label="Découvrir la plateforme">
            <span>Explorer</span><i />
          </a>
        </section>

        <section className="statement-strip" aria-label="Promesse de Julia">
          <div className="container statement-strip__inner">
            <span>Une nouvelle façon de travailler</span>
            <p>Moins de temps à chercher. Plus de temps pour <em>comprendre et conseiller.</em></p>
          </div>
        </section>

        <section className="section section--platform" id="plateforme">
          <div className="container">
            <div className="section-heading">
              <span className="section-kicker">Intelligence documentaire</span>
              <h2>La puissance de l’IA.<br /><em>La rigueur du droit.</em></h2>
              <p>Une expérience pensée pour accélérer la recherche sans jamais masquer la source.</p>
            </div>
            <div className="benefit-grid">
              {benefits.map(({ icon: Icon, label, title, text }, index) => (
                <article className={`benefit-card benefit-card--${index + 1}`} key={title}>
                  <div className="benefit-card__top"><span>0{index + 1}</span><Icon size={24} /></div>
                  <span className="benefit-card__label">{label}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <div className="benefit-card__line" aria-hidden="true" />
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="experience-section" id="experience">
          <div className="container experience-grid">
            <div className="experience-copy">
              <span className="section-kicker">Simple par nature</span>
              <h2>De la question à la preuve, <em>en un seul parcours.</em></h2>
              <p>Julia garde le raisonnement lisible. Vous savez ce qui a été cherché, ce qui fonde la réponse et ce qui demande encore vérification.</p>
              <button className="text-link" type="button" onClick={onStart}>Essayer le parcours <ArrowRight size={17} /></button>
            </div>
            <div className="journey" aria-label="Les trois étapes de Julia">
              {journey.map(([number, title, text], index) => (
                <article className="journey__step" key={number}>
                  <span className="journey__number">{number}</span>
                  <div><h3>{title}</h3><p>{text}</p></div>
                  {index < journey.length - 1 && <i aria-hidden="true" />}
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section section--domains" id="domaines">
          <div className="container domains-layout">
            <div className="section-heading section-heading--left">
              <span className="section-kicker">Corpus maîtrisé</span>
              <h2>Chaque domaine s’ouvre <em>après vérification.</em></h2>
              <p>La fiscalité béninoise constitue le premier périmètre. Les prochains corpus seront activés progressivement.</p>
              <div className="corpus-seal"><Fingerprint size={24} /><div><strong>Périmètre explicite</strong><span>Vous savez toujours où Julia cherche.</span></div></div>
            </div>
            <div className="domain-list">
              {domains.map(([title, text, active], index) => (
                <article className={`domain-row${active ? ' domain-row--active' : ''}`} key={title}>
                  <span className="domain-row__number">0{index + 1}</span>
                  <div><h3>{title}</h3><p>{text}</p></div>
                  <span className="domain-row__badge">{active ? <><i /> Disponible</> : 'Prochainement'}</span>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="trust-section" id="confiance">
          <div className="trust-orb" aria-hidden="true"><ShieldCheck size={54} /></div>
          <div className="container trust-section__grid">
            <div>
              <span className="section-kicker section-kicker--dark">Confiance intégrée</span>
              <h2>La transparence n’est pas une option. <em>C’est le produit.</em></h2>
              <p>Julia vous aide à aller plus vite, tout en gardant le professionnel au centre de la décision.</p>
            </div>
            <div className="trust-rules">
              <div><strong>01</strong><p><b>Pas de source, pas de conclusion.</b><br />Julia signale quand le corpus ne suffit pas.</p></div>
              <div><strong>02</strong><p><b>Une réponse que l’on peut auditer.</b><br />Chaque citation ouvre son contexte documentaire.</p></div>
              <div><strong>03</strong><p><b>Le jugement reste humain.</b><br />L’outil éclaire la décision, il ne remplace pas le conseil.</p></div>
            </div>
          </div>
        </section>

        <section className="cta-section">
          <div className="container cta-card">
            <div className="cta-card__mark" aria-hidden="true"><Sparkles size={25} /></div>
            <div><span>Prêt à explorer ?</span><h2>Votre recherche juridique commence ici.</h2></div>
            <button className="button button--primary" type="button" onClick={onStart}>Démarrer avec Julia <ArrowRight size={18} /></button>
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
