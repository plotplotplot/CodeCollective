import type { VoteDirection, Comment } from '../../domain/motion/Motion'

export type CreateCommentInput = {
  motionId: string
  authorId: string
  authorName: string
  body: string
}

export interface EngagementRepository {
  upvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }>
  downvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }>
  getUserVote(motionId: string, userId: string): Promise<VoteDirection | null>
  listComments(motionId: string): Promise<Comment[]>
  addComment(input: CreateCommentInput): Promise<Comment>
}
