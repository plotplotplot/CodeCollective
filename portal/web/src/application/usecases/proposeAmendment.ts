import type { MotionRepository } from '../ports/MotionRepository'
import type { MotionStatus } from '../../domain/motion/Motion'

const TERMINAL_STATUSES: MotionStatus[] = ['passed', 'failed', 'withdrawn']

export type ProposeAmendmentRequest = {
  parentMotionId: string
  title: string
  body: string
  proposedBodyDiff: string
  proposerId: string
  proposerName: string
  quorumRequired: number
}

export function validateProposeAmendment(req: ProposeAmendmentRequest): string[] {
  const errors: string[] = []
  if (!req.title?.trim()) errors.push('Title is required')
  if (!req.body?.trim()) errors.push('Body is required')
  if (!req.proposedBodyDiff?.trim()) errors.push('Proposed body diff is required')
  if (req.quorumRequired < 1) errors.push('Quorum must be at least 1')
  return errors
}

export async function proposeAmendment(repo: MotionRepository, req: ProposeAmendmentRequest) {
  const errors = validateProposeAmendment(req)
  if (errors.length) return { ok: false as const, errors }

  const parent = await repo.getById(req.parentMotionId)
  if (!parent) return { ok: false as const, errors: ['Parent motion not found'] }
  if (TERMINAL_STATUSES.includes(parent.status)) {
    return { ok: false as const, errors: ['Parent motion is in a terminal state'] }
  }

  const motion = await repo.create({
    type: 'amendment',
    parentMotionId: req.parentMotionId,
    title: req.title,
    body: req.body,
    proposedBodyDiff: req.proposedBodyDiff,
    proposerId: req.proposerId,
    proposerName: req.proposerName,
    quorumRequired: req.quorumRequired,
  })
  return { ok: true as const, motion }
}
