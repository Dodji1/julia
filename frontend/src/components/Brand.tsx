import { Scale } from 'lucide-react'

interface BrandProps {
  inverted?: boolean
}

export function Brand({ inverted = false }: BrandProps) {
  return (
    <span className={`brand${inverted ? ' brand--inverted' : ''}`}>
      <span className="brand__mark" aria-hidden="true">
        <Scale size={18} strokeWidth={2.1} />
      </span>
      <span>
        <strong>Vitalia</strong>
        <small>Intelligence juridique</small>
      </span>
    </span>
  )
}
