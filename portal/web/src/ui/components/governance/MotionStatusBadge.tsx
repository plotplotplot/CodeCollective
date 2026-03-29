import type { MotionStatus } from '../../../domain/motion/Motion'

const STATUS_STYLES: Record<MotionStatus, { bg: string; text: string; dot: string }> = {
  proposed: { bg: 'var(--accent-amber-bg)', text: 'var(--accent-amber)', dot: 'var(--accent-amber)' },
  seconded: { bg: 'var(--accent-blue-bg)', text: 'var(--accent-blue)', dot: 'var(--accent-blue)' },
  discussion: { bg: 'var(--accent-teal-bg)', text: 'var(--accent-teal)', dot: 'var(--accent-teal)' },
  voting: { bg: 'var(--accent-purple-bg)', text: 'var(--accent-purple)', dot: 'var(--accent-purple)' },
  passed: { bg: 'var(--accent-green-bg)', text: 'var(--accent-green)', dot: 'var(--accent-green)' },
  failed: { bg: 'var(--accent-red-bg)', text: 'var(--accent-red)', dot: 'var(--accent-red)' },
  tabled: { bg: 'var(--panel-2)', text: 'var(--text-muted)', dot: 'var(--text-muted)' },
  withdrawn: { bg: 'var(--surface)', text: 'var(--text-muted)', dot: 'var(--text-muted)' },
}

type Props = { status: MotionStatus }

export function MotionStatusBadge({ status }: Props) {
  const s = STATUS_STYLES[status]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 10px',
        fontSize: 11,
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        lineHeight: '20px',
        borderRadius: 999,
        backgroundColor: s.bg,
        color: s.text,
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: s.dot,
          flexShrink: 0,
        }}
      />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}
