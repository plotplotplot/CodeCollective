import type { Motion, VoteDirection, Comment } from '../../domain/motion/Motion'

export type CreateCommentInput = {
  motionId: string
  authorId: string
  authorName: string
  body: string
}

export type UserProfile = {
  userId: string
  /** Motion IDs the user has interacted with (upvoted, commented, viewed) */
  interactedMotionIds: string[]
  /** Status types the user engages with most */
  preferredStatuses: Record<string, number>
  /** How many total interactions */
  totalInteractions: number
}

export type VoteCounts = {
  up: number
  down: number
  score: number
}

export type RankedMotion = Motion & {
  rank: number
  commentCount: number
  voteCounts: VoteCounts
}

export interface EngagementRepository {
  upvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }>
  downvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }>
  getUserVote(motionId: string, userId: string): Promise<VoteDirection | null>
  listComments(motionId: string): Promise<Comment[]>
  addComment(input: CreateCommentInput): Promise<Comment>
  getVoteCounts(motionId: string): Promise<VoteCounts>
  trackView(motionId: string, userId: string): Promise<void>
  getUserProfile(userId: string): Promise<UserProfile>
  rankMotions(motions: Motion[], userId: string): Promise<RankedMotion[]>
}
