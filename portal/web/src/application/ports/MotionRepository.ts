import type { Motion, MotionStatus, MotionType } from '../../domain/motion/Motion'

export type MotionListQuery = {
  search?: string
  status?: MotionStatus[]
  type?: MotionType
  parentMotionId?: string
}

export type CreateMotionInput = {
  type: MotionType
  parentMotionId?: string
  title: string
  body: string
  proposedBodyDiff?: string
  proposerId: string
  proposerName: string
  quorumRequired: number
}

export interface MotionRepository {
  list(query?: MotionListQuery): Promise<Motion[]>
  getById(id: string): Promise<Motion | null>
  create(input: CreateMotionInput): Promise<Motion>
  second(motionId: string, userId: string, userName: string): Promise<Motion>
  openVoting(motionId: string): Promise<Motion>
  table(motionId: string): Promise<Motion>
  withdraw(motionId: string, userId: string): Promise<Motion>
  resolveVoting(motionId: string): Promise<Motion>
}
