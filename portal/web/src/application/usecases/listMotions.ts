import type { MotionRepository, MotionListQuery } from '../ports/MotionRepository'

export async function listMotions(repo: MotionRepository, query?: MotionListQuery) {
  return repo.list(query)
}
