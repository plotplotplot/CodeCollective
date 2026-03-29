import type { Motion, VoteChoice } from '../../../domain/motion/Motion'
import { canVote } from '../../../domain/motion/motionStateMachine'

type Props = {
  motion: Motion
  currentUserId: string
  onVote: (choice: VoteChoice) => void
}

const CHOICE_COLORS: Record<VoteChoice, string> = {
  yea: '#16a34a',
  nay: '#dc2626',
  abstain: '#6b7280',
}

export function VotingPanel({ motion, currentUserId, onVote }: Props) {
  const userCanVote = canVote(motion, currentUserId)
  const { result } = motion

  const tallies = result ?? countVotes(motion)
  const totalCast = tallies.yea + tallies.nay + tallies.abstain

  if (result) {
    return (
      <div style={panelStyle}>
        <div style={{ marginBottom: 12, fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
          Vote Result
        </div>
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            backgroundColor: result.passed ? '#dcfce7' : '#fee2e2',
            color: result.passed ? '#166534' : '#991b1b',
            fontWeight: 600,
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {result.passed ? 'Motion Passed' : 'Motion Failed'}
          {result.quorumMet ? '' : ' (quorum not met)'}
        </div>
        {renderBars(tallies, totalCast)}
        {renderTotal(totalCast, motion.quorumRequired)}
      </div>
    )
  }

  return (
    <div style={panelStyle}>
      <div style={{ marginBottom: 12, fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
        Cast Your Vote
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {(['yea', 'nay', 'abstain'] as const).map((choice) => (
          <button
            key={choice}
            disabled={!userCanVote}
            onClick={() => onVote(choice)}
            style={{
              flex: 1,
              padding: '8px 0',
              fontSize: 13,
              fontWeight: 600,
              border: 'none',
              borderRadius: 8,
              cursor: userCanVote ? 'pointer' : 'not-allowed',
              backgroundColor: userCanVote ? CHOICE_COLORS[choice] : '#e5e7eb',
              color: userCanVote ? '#fff' : '#9ca3af',
              opacity: userCanVote ? 1 : 0.6,
              transition: 'opacity 0.15s',
            }}
          >
            {choice.charAt(0).toUpperCase() + choice.slice(1)}
          </button>
        ))}
      </div>
      {renderBars(countVotes(motion), totalCast)}
      {renderTotal(totalCast, motion.quorumRequired)}
    </div>
  )
}

const panelStyle: React.CSSProperties = {
  padding: 16,
  borderRadius: 'var(--radius-lg, 12px)' as string,
  border: '1px solid var(--border-subtle, rgba(12, 30, 60, 0.12))',
  backgroundColor: 'var(--panel, #fff)',
}

function countVotes(motion: Motion) {
  let yea = 0
  let nay = 0
  let abstain = 0
  for (const v of motion.votes) {
    if (v.choice === 'yea') yea++
    else if (v.choice === 'nay') nay++
    else abstain++
  }
  return { yea, nay, abstain }
}

function renderBars(tallies: { yea: number; nay: number; abstain: number }, total: number) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }}>
      {(['yea', 'nay', 'abstain'] as const).map((key) => {
        const count = tallies[key]
        const pct = total > 0 ? (count / total) * 100 : 0
        return (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 52, fontSize: 12, fontWeight: 500, color: 'var(--text-primary)' }}>
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </span>
            <div
              style={{
                flex: 1,
                height: 8,
                borderRadius: 4,
                backgroundColor: '#e5e7eb',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  borderRadius: 4,
                  backgroundColor: CHOICE_COLORS[key],
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
            <span style={{ width: 28, fontSize: 12, textAlign: 'right', color: 'var(--text-primary)' }}>
              {count}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function renderTotal(totalCast: number, quorumRequired: number) {
  return (
    <div style={{ fontSize: 12, color: '#6b7280' }}>
      {totalCast} vote{totalCast !== 1 ? 's' : ''} cast / {quorumRequired} required for quorum
    </div>
  )
}
