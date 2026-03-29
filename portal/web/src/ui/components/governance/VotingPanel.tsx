import type { Motion, VoteChoice } from '../../../domain/motion/Motion'
import { canVote } from '../../../domain/motion/motionStateMachine'

type Props = {
  motion: Motion
  currentUserId: string
  onVote: (choice: VoteChoice) => void
}

const CHOICE_CONFIG: Record<VoteChoice, { color: string; bg: string; icon: string }> = {
  yea: { color: 'var(--accent-green)', bg: 'var(--accent-green-bg)', icon: '\u2713' },
  nay: { color: 'var(--accent-red)', bg: 'var(--accent-red-bg)', icon: '\u2717' },
  abstain: { color: 'var(--text-muted)', bg: 'var(--surface)', icon: '\u2014' },
}

export function VotingPanel({ motion, currentUserId, onVote }: Props) {
  const userCanVote = canVote(motion, currentUserId)
  const { result } = motion

  const tallies = result ?? countVotes(motion)
  const totalCast = tallies.yea + tallies.nay + tallies.abstain

  if (result) {
    return (
      <div style={panelStyle}>
        <div style={{ marginBottom: 16, fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
          Vote Result
        </div>
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: result.passed ? 'var(--accent-green-bg)' : 'var(--accent-red-bg)',
            color: result.passed ? 'var(--accent-green)' : 'var(--accent-red)',
            fontWeight: 700,
            fontSize: 14,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ fontSize: 18 }}>{result.passed ? '\u2713' : '\u2717'}</span>
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
      <div style={{ marginBottom: 16, fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
        Cast Your Vote
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        {(['yea', 'nay', 'abstain'] as const).map((choice) => {
          const cfg = CHOICE_CONFIG[choice]
          return (
            <button
              key={choice}
              disabled={!userCanVote}
              onClick={() => onVote(choice)}
              style={{
                flex: 1,
                padding: '10px 0',
                fontSize: 13,
                fontWeight: 700,
                border: 'none',
                borderRadius: 999,
                cursor: userCanVote ? 'pointer' : 'not-allowed',
                backgroundColor: userCanVote ? cfg.color : 'var(--surface)',
                color: userCanVote ? '#fff' : 'var(--text-muted)',
                opacity: userCanVote ? 1 : 0.5,
                transition: 'transform 0.15s, opacity 0.15s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <span style={{ fontSize: 15 }}>{cfg.icon}</span>
              {choice.charAt(0).toUpperCase() + choice.slice(1)}
            </button>
          )
        })}
      </div>
      {renderBars(countVotes(motion), totalCast)}
      {renderTotal(totalCast, motion.quorumRequired)}
    </div>
  )
}

const panelStyle: React.CSSProperties = {
  padding: 20,
  borderRadius: 'var(--radius-lg)' as string,
  border: '1px solid var(--border-subtle)' as string,
  backgroundColor: 'var(--panel-2)' as string,
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
  const barConfig: Record<string, string> = {
    yea: 'var(--accent-green)',
    nay: 'var(--accent-red)',
    abstain: 'var(--text-muted)',
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
      {(['yea', 'nay', 'abstain'] as const).map((key) => {
        const count = tallies[key]
        const pct = total > 0 ? (count / total) * 100 : 0
        return (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 56, fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
              {key}
            </span>
            <div
              style={{
                flex: 1,
                height: 10,
                borderRadius: 5,
                backgroundColor: 'var(--surface)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  borderRadius: 5,
                  backgroundColor: barConfig[key],
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
            <span style={{ width: 36, fontSize: 12, fontWeight: 600, textAlign: 'right', color: 'var(--text-primary)' }}>
              {count}
            </span>
            <span style={{ width: 36, fontSize: 11, textAlign: 'right', color: 'var(--text-muted)' }}>
              {total > 0 ? `${Math.round(pct)}%` : '0%'}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function renderTotal(totalCast: number, quorumRequired: number) {
  return (
    <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{totalCast}</span> vote{totalCast !== 1 ? 's' : ''} cast
      <span style={{ color: 'var(--border)' }}>/</span>
      <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>{quorumRequired}</span> required for quorum
    </div>
  )
}
