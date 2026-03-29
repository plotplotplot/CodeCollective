import type { MotionStatus } from '../../../domain/motion/Motion'

type Props = { status: MotionStatus }

const MAIN_STEPS: MotionStatus[] = ['proposed', 'seconded', 'discussion', 'voting']
const TERMINAL_BRANCH: MotionStatus[] = ['tabled', 'withdrawn']

const STEP_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  seconded: 'Seconded',
  discussion: 'Discussion',
  voting: 'Voting',
  passed: 'Passed',
  failed: 'Failed',
}

export function MotionTimeline({ status }: Props) {
  const isBranch = TERMINAL_BRANCH.includes(status)
  const mainIndex = MAIN_STEPS.indexOf(status)
  const isFinal = status === 'passed' || status === 'failed'

  // Determine which main steps are "reached"
  const reachedIndex = isBranch
    ? MAIN_STEPS.indexOf(status === 'tabled' ? 'discussion' : 'proposed')
    : isFinal
      ? MAIN_STEPS.length - 1
      : mainIndex

  // Build the display steps: main steps + final outcome
  const finalStep = isFinal ? status : 'passed'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
        {MAIN_STEPS.map((step, i) => {
          const reached = i <= reachedIndex
          return (
            <div key={step} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    backgroundColor: reached ? 'var(--primary, #2563eb)' : '#d1d5db',
                    border: `2px solid ${reached ? 'var(--primary, #2563eb)' : '#d1d5db'}`,
                    transition: 'background-color 0.2s',
                  }}
                />
                <span
                  style={{
                    fontSize: 10,
                    marginTop: 4,
                    color: reached ? 'var(--text-primary, #0b1a33)' : '#9ca3af',
                    fontWeight: reached ? 600 : 400,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {STEP_LABELS[step]}
                </span>
              </div>
              {i < MAIN_STEPS.length - 1 && (
                <div
                  style={{
                    width: 32,
                    height: 2,
                    backgroundColor: i < reachedIndex ? 'var(--primary, #2563eb)' : '#d1d5db',
                    marginBottom: 18,
                  }}
                />
              )}
            </div>
          )
        })}
        {/* Final outcome dot */}
        <div
          style={{
            width: 32,
            height: 2,
            backgroundColor: isFinal ? 'var(--primary, #2563eb)' : '#d1d5db',
            marginBottom: 18,
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div
            style={{
              width: 16,
              height: 16,
              borderRadius: '50%',
              backgroundColor: isFinal
                ? status === 'passed'
                  ? '#16a34a'
                  : '#dc2626'
                : '#d1d5db',
              border: `2px solid ${isFinal ? (status === 'passed' ? '#16a34a' : '#dc2626') : '#d1d5db'}`,
            }}
          />
          <span
            style={{
              fontSize: 10,
              marginTop: 4,
              color: isFinal ? 'var(--text-primary, #0b1a33)' : '#9ca3af',
              fontWeight: isFinal ? 600 : 400,
              whiteSpace: 'nowrap',
            }}
          >
            {STEP_LABELS[finalStep]}
          </span>
        </div>
      </div>

      {/* Branch indicator for tabled / withdrawn */}
      {isBranch && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            marginLeft: reachedIndex * 48 + 4,
            marginTop: 2,
          }}
        >
          <div
            style={{
              width: 2,
              height: 14,
              backgroundColor: '#f59e0b',
            }}
          />
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: '#fbbf24',
              border: '2px solid #f59e0b',
            }}
          />
          <span style={{ fontSize: 10, fontWeight: 600, color: '#92400e' }}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        </div>
      )}
    </div>
  )
}
