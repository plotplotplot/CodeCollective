import type { MotionStatus } from '../../../domain/motion/Motion'

const STATUS_COLORS: Record<MotionStatus, { bg: string; text: string }> = {
  proposed: { bg: '#fef3c7', text: '#92400e' },
  seconded: { bg: '#dbeafe', text: '#1e40af' },
  discussion: { bg: '#ccfbf1', text: '#0f766e' },
  voting: { bg: '#ede9fe', text: '#6d28d9' },
  passed: { bg: '#dcfce7', text: '#166534' },
  failed: { bg: '#fee2e2', text: '#991b1b' },
  tabled: { bg: '#e5e7eb', text: '#374151' },
  withdrawn: { bg: '#f3f4f6', text: '#6b7280' },
}

type Props = { status: MotionStatus }

export function MotionStatusBadge({ status }: Props) {
  const colors = STATUS_COLORS[status]
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        fontSize: 11,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        lineHeight: '20px',
        borderRadius: 9999,
        backgroundColor: colors.bg,
        color: colors.text,
      }}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}
