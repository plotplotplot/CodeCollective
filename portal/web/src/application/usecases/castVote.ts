import type { MotionRepository } from '../ports/MotionRepository'
import type { VoteRepository } from '../ports/VoteRepository'
import type { VoteChoice } from '../../domain/motion/Motion'
import { canVote } from '../../domain/motion/motionStateMachine'

export async function castVote(
  voteRepo: VoteRepository,
  motionRepo: MotionRepository,
  motionId: string,
  voterId: string,
  voterName: string,
  choice: VoteChoice,
) {
  const motion = await motionRepo.getById(motionId)
  if (!motion) return { ok: false as const, errors: ['Motion not found'] }
  if (!canVote(motion, voterId)) return { ok: false as const, errors: ['Cannot vote on this motion'] }

  const vote = await voteRepo.castVote(motionId, voterId, voterName, choice)
  return { ok: true as const, vote }
}
