import { Check, FileText, ShieldCheck, Sparkles } from 'lucide-react'

export function LegalIntelligenceVisual() {
  return (
    <div className="legal-visual" aria-label="Illustration du moteur documentaire de Julia">
      <div className="legal-visual__halo" aria-hidden="true" />
      <svg
        className="knowledge-map"
        viewBox="0 0 560 520"
        role="img"
        aria-labelledby="knowledge-title knowledge-description"
      >
        <title id="knowledge-title">Réseau de recherche juridique Julia</title>
        <desc id="knowledge-description">
          Julia relie la question aux textes, articles et procédures du corpus.
        </desc>
        <defs>
          <linearGradient id="orb-fill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#7ea2ff" />
            <stop offset=".5" stopColor="#315efb" />
            <stop offset="1" stopColor="#2446c7" />
          </linearGradient>
          <radialGradient id="orb-glow">
            <stop offset="0" stopColor="#6f95ff" stopOpacity=".35" />
            <stop offset="1" stopColor="#315efb" stopOpacity="0" />
          </radialGradient>
          <filter id="soft-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="7" />
          </filter>
        </defs>

        <circle cx="280" cy="245" r="168" className="knowledge-map__orbit knowledge-map__orbit--outer" />
        <circle cx="280" cy="245" r="119" className="knowledge-map__orbit knowledge-map__orbit--inner" />
        <circle cx="280" cy="245" r="87" fill="url(#orb-glow)" filter="url(#soft-glow)" />

        <path d="M280 128C200 130 148 164 112 215" className="knowledge-map__path" />
        <path d="M360 160c61 20 93 58 102 106" className="knowledge-map__path knowledge-map__path--delay" />
        <path d="M221 327c-42 25-66 59-72 101" className="knowledge-map__path knowledge-map__path--delay-two" />
        <path d="M346 324c45 20 70 51 76 91" className="knowledge-map__path" />

        <g className="knowledge-map__node knowledge-map__node--one">
          <circle cx="104" cy="225" r="9" />
          <circle cx="104" cy="225" r="17" className="knowledge-map__node-ring" />
        </g>
        <g className="knowledge-map__node knowledge-map__node--two">
          <circle cx="463" cy="274" r="9" />
          <circle cx="463" cy="274" r="17" className="knowledge-map__node-ring" />
        </g>
        <g className="knowledge-map__node knowledge-map__node--three">
          <circle cx="146" cy="430" r="9" />
          <circle cx="146" cy="430" r="17" className="knowledge-map__node-ring" />
        </g>
        <g className="knowledge-map__node knowledge-map__node--four">
          <circle cx="424" cy="417" r="9" />
          <circle cx="424" cy="417" r="17" className="knowledge-map__node-ring" />
        </g>

        <g className="knowledge-map__core">
          <circle cx="280" cy="245" r="58" fill="url(#orb-fill)" />
          <path d="M258 225h44M280 216v55M267 271h26" />
          <path d="m264 227-12 23h24l-12-23Zm32 0-12 23h24l-12-23Z" />
          <path d="M251 250c1 7 5.5 10 13 10s12-3 13-10M283 250c1 7 5.5 10 13 10s12-3 13-10" />
        </g>
      </svg>

      <div className="visual-chip visual-chip--question">
        <span><Sparkles size={15} /></span>
        <div><small>Question comprise</small><strong>Intention juridique analysée</strong></div>
      </div>
      <div className="visual-chip visual-chip--corpus">
        <span><FileText size={15} /></span>
        <div><small>Corpus interrogé</small><strong>Textes et procédures</strong></div>
      </div>
      <div className="visual-chip visual-chip--answer">
        <span><Check size={15} /></span>
        <div><small>Réponse structurée</small><strong>Sources prêtes à vérifier</strong></div>
      </div>
      <div className="legal-visual__trust"><ShieldCheck size={16} /> Traçabilité à chaque étape</div>
    </div>
  )
}
