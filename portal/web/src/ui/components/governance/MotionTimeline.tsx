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

  const reachedIndex = isBranch
    ? MAIN_STEPS.indexOf(status === 'tabled' ? 'discussion' : 'proposed')
    : isFinal
      ? MAIN_STEPS.length - 1
      : mainIndex

  const finalStep = isFinal ? status : 'passed'

  const allSteps = [...MAIN_STEPS, finalStep]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start' }}>
        {allSteps.map((step, i) => {
          const isLast = i === allSteps.length - 1
          const isFinalDot = i >= MAIN_STEPS.length
          const reached = isFinalDot ? isFinal : i <= reachedIndex
          const isActive = isFinalDot
            ? isFinal && status === step
            : step === status && !isBranch && !isFinal

          const dotColor = isFinalDot
            ? isFinal
              ? status === 'passed'
                ? 'var(--accent-green)'
                : 'var(--accent-red)'
              : 'var(--border)'
            : reached
              ? 'var(--primary)'
              : 'var(--border)'

          const lineColor = isFinalDot
            ? isFinal
              ? 'var(--primary)'
              : 'var(--border)'
            : i < reachedIndex || (i === reachedIndex && isFinal)
              ? 'var(--primary)'
              : 'var(--border)'

          return (
            <div
              key={`${step}-${i}`}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                flex: isLast ? '0 0 auto' : 1,
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 56 }}>
                <div
                  style={{
                    width: isActive ? 28 : 22,
                    height: isActive ? 28 : 22,
                    borderRadius: '50%',
                    backgroundColor: reached ? dotColor : 'var(--panel)',
                    border: `2.5px solid ${dotColor}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                    flexShrink: 0,
                  }}
                >
                  {reached && (
                    <span style={{
                      color: '#fff',
                      fontSize: isActive ? 12 : 10,
                      fontWeight: 700,
                      lineHeight: 1,
                    }}>
                      {isFinalDot ? (isFinal ? (status === 'passed' ? '\u2713' : '\u2717') : '') : i + 1}
                    </span>
                  )}
                  {!reached && (
                    <span style={{
                      color: 'var(--text-muted)',
                      fontSize: 10,
                      fontWeight: 600,
                      lineHeight: 1,
                    }}>
                      {isFinalDot ? '' : i + 1}
                    </span>
                  )}
                </div>
                <span
                  style={{
                    fontSize: 10,
                    marginTop: 6,
                    color: reached ? 'var(--text-primary)' : 'var(--text-muted)',
                    fontWeight: reached ? 700 : 400,
                    whiteSpace: 'nowrap',
                    textAlign: 'center',
                  }}
                >
                  {STEP_LABELS[step]}
                </span>
              </div>
              {!isLast && (
                <div
                  style={{
                    flex: 1,
                    height: 2.5,
                    backgroundColor: lineColor,
                    marginTop: isActive ? 13 : 10,
                    borderRadius: 2,
                    transition: 'background-color 0.2s',
                  }}
                />
              )}
            </div>
          )
        })}
      </div>

      {isBranch && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            marginTop: 4,
            padding: '4px 12px',
            borderRadius: 999,
            backgroundColor: 'var(--accent-amber-bg)',
            alignSelf: 'flex-start',
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: 'var(--accent-amber)',
            }}
          />
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent-amber)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        </div>
      )}
    </div>
  )
}
