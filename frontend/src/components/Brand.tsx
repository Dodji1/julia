interface BrandProps {
  inverted?: boolean
}

export function Brand({ inverted = false }: BrandProps) {
  return (
    <span className={`brand${inverted ? ' brand--inverted' : ''}`}>
      <span className="brand__mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" focusable="false">
          <path d="M8 8.5h16M16 5v20M11 25h10" />
          <path d="m10 9-4 8h8l-4-8Zm12 0-4 8h8l-4-8Z" />
          <path d="M5.8 17c.5 2.1 2 3.2 4.2 3.2s3.7-1.1 4.2-3.2M17.8 17c.5 2.1 2 3.2 4.2 3.2s3.7-1.1 4.2-3.2" />
        </svg>
      </span>
      <span>
        <strong>Vitalia</strong>
        <small>Intelligence juridique</small>
      </span>
    </span>
  )
}
