type Props = {
  originalText: string
  proposedText: string
}

export function AmendmentDiff({ originalText, proposedText }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        borderRadius: 'var(--radius-lg, 12px)' as string,
        border: '1px solid var(--border-subtle, rgba(12, 30, 60, 0.12))',
        overflow: 'hidden',
      }}
    >
      {/* Original */}
      <div style={{ padding: 16, backgroundColor: '#fef2f2' }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#991b1b',
            marginBottom: 8,
          }}
        >
          Original
        </div>
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.6,
            color: '#0b1a33',
            whiteSpace: 'pre-wrap',
          }}
        >
          {originalText}
        </div>
      </div>

      {/* Proposed */}
      <div style={{ padding: 16, backgroundColor: '#f0fdf4' }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#166534',
            marginBottom: 8,
          }}
        >
          Proposed
        </div>
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.6,
            color: '#0b1a33',
            whiteSpace: 'pre-wrap',
          }}
        >
          {proposedText}
        </div>
      </div>
    </div>
  )
}
