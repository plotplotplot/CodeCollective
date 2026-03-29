import type { MotionRepository } from '../ports/MotionRepository'
import { canSecond } from '../../domain/motion/motionStateMachine'

export async function secondMotion(
  repo: MotionRepository,
  motionId: string,
  userId: string,
  userName: string,
) {
  const motion = await repo.getById(motionId)
  if (!motion) return { ok: false as const, errors: ['Motion not found'] }
  if (!canSecond(motion, userId)) return { ok: false as const, errors: ['Cannot second this motion'] }

  const updated = await repo.second(motionId, userId, userName)
  return { ok: true as const, motion: updated }
}
