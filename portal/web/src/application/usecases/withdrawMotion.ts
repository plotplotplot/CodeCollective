import type { MotionRepository } from '../ports/MotionRepository'
import { canWithdraw } from '../../domain/motion/motionStateMachine'

export async function withdrawMotion(repo: MotionRepository, motionId: string, userId: string) {
  const motion = await repo.getById(motionId)
  if (!motion) return { ok: false as const, errors: ['Motion not found'] }
  if (!canWithdraw(motion, userId)) return { ok: false as const, errors: ['Cannot withdraw this motion'] }

  const updated = await repo.withdraw(motionId, userId)
  return { ok: true as const, motion: updated }
}
