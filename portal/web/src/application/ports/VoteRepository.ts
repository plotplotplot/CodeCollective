import type { Vote, VoteChoice, VoteResult } from '../../domain/motion/Motion'

export interface VoteRepository {
  castVote(motionId: string, voterId: string, voterName: string, choice: VoteChoice): Promise<Vote>
  getResults(motionId: string): Promise<VoteResult>
}
