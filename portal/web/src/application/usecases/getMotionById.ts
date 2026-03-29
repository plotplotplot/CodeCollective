import type { MotionRepository } from '../ports/MotionRepository'

export async function getMotionById(repo: MotionRepository, id: string) {
  return repo.getById(id)
}
