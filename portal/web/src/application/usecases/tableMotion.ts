import type { MotionRepository } from '../ports/MotionRepository'
import { canTable } from '../../domain/motion/motionStateMachine'

export async function tableMotion(repo: MotionRepository, motionId: string) {
  const motion = await repo.getById(motionId)
  if (!motion) return { ok: false as const, errors: ['Motion not found'] }
  if (!canTable(motion)) return { ok: false as const, errors: ['Cannot table this motion'] }

  const updated = await repo.table(motionId)
  return { ok: true as const, motion: updated }
}
