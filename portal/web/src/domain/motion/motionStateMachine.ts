import type { Motion, MotionStatus } from './Motion'

const VALID_TRANSITIONS: Record<MotionStatus, MotionStatus[]> = {
  proposed: ['seconded', 'withdrawn'],
  seconded: ['discussion'],
  discussion: ['voting', 'tabled'],
  voting: ['passed', 'failed'],
  tabled: ['discussion'],
  passed: [],
  failed: [],
  withdrawn: [],
}

export function canSecond(motion: Motion, userId: string): boolean {
  return motion.status === 'proposed' && motion.proposerId !== userId
}

export function canVote(motion: Motion, userId: string): boolean {
  return (
    motion.status === 'voting' &&
    !motion.votes.some((v) => v.voterId === userId)
  )
}

export function canWithdraw(motion: Motion, userId: string): boolean {
  return motion.status === 'proposed' && motion.proposerId === userId
}

export function canTable(motion: Motion): boolean {
  return motion.status === 'discussion'
}

export function canOpenVoting(motion: Motion, amendments?: Motion[]): boolean {
  if (motion.status !== 'discussion') return false
  if (amendments && amendments.some((a) => !isTerminalStatus(a.status))) {
    return false
  }
  return true
}

export function isTerminalStatus(status: MotionStatus): boolean {
  return VALID_TRANSITIONS[status].length === 0
}

export function isValidTransition(from: MotionStatus, to: MotionStatus): boolean {
  return VALID_TRANSITIONS[from].includes(to)
}

export function getValidTransitions(motion: Motion): MotionStatus[] {
  return VALID_TRANSITIONS[motion.status]
}
