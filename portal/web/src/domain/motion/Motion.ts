export type MotionStatus = 'proposed' | 'seconded' | 'discussion' | 'voting' | 'passed' | 'failed' | 'tabled' | 'withdrawn'
export type MotionType = 'main' | 'amendment'
export type VoteChoice = 'yea' | 'nay' | 'abstain'

export type Motion = {
  id: string
  type: MotionType
  parentMotionId?: string        // set when type === 'amendment'
  title: string
  body: string                   // motion text (markdown)
  proposedBodyDiff?: string      // for amendments: the proposed replacement text
  status: MotionStatus
  proposerId: string
  proposerName: string
  seconderId?: string
  seconderName?: string
  createdAtISO: string
  updatedAtISO: string
  discussionDeadlineISO?: string
  votingDeadlineISO?: string
  quorumRequired: number
  votes: Vote[]
  result?: VoteResult
  score: number
}

export type Vote = {
  id: string
  motionId: string
  voterId: string
  voterName: string
  choice: VoteChoice
  castAtISO: string
}

export type VoteResult = {
  yea: number
  nay: number
  abstain: number
  totalEligible: number
  quorumMet: boolean
  passed: boolean
}

export type VoteDirection = 'up' | 'down'

export type Comment = {
  id: string
  motionId: string
  authorId: string
  authorName: string
  body: string
  createdAtISO: string
}
