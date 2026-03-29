import type { InitiativeRepository } from '../application/ports/InitiativeRepository'
import type { SignatureRepository } from '../application/ports/SignatureRepository'
import type { MotionRepository } from '../application/ports/MotionRepository'
import type { VoteRepository } from '../application/ports/VoteRepository'
import type { EngagementRepository } from '../application/ports/EngagementRepository'
import { MockInitiativeRepository } from '../infrastructure/mocks/MockInitiativeRepository'
import { MockSignatureRepository } from '../infrastructure/mocks/MockSignatureRepository'
import { MockMotionRepository } from '../infrastructure/mocks/MockMotionRepository'
import { MockVoteRepository } from '../infrastructure/mocks/MockVoteRepository'
import { MockEngagementRepository } from '../infrastructure/mocks/MockEngagementRepository'

export type AppServices = {
  initiativeRepository: InitiativeRepository
  signatureRepository: SignatureRepository
  motionRepository: MotionRepository
  voteRepository: VoteRepository
  engagementRepository: EngagementRepository
}

function createInitiativeRepository(): InitiativeRepository {
  // Factory Method seam: swap mock vs API later without touching use cases/UI.
  const source = (import.meta as any).env?.VITE_DATA_SOURCE ?? 'mock'
  if (source === 'mock') return new MockInitiativeRepository()
  return new MockInitiativeRepository()
}

function createSignatureRepository(): SignatureRepository {
  const source = (import.meta as any).env?.VITE_DATA_SOURCE ?? 'mock'
  if (source === 'mock') return new MockSignatureRepository()
  return new MockSignatureRepository()
}

function createMotionRepository(): MotionRepository {
  const source = (import.meta as any).env?.VITE_DATA_SOURCE ?? 'mock'
  if (source === 'mock') return new MockMotionRepository()
  return new MockMotionRepository()
}

function createVoteRepository(): VoteRepository {
  const source = (import.meta as any).env?.VITE_DATA_SOURCE ?? 'mock'
  if (source === 'mock') return new MockVoteRepository()
  return new MockVoteRepository()
}

function createEngagementRepository(): EngagementRepository {
  const source = (import.meta as any).env?.VITE_DATA_SOURCE ?? 'mock'
  if (source === 'mock') return new MockEngagementRepository()
  return new MockEngagementRepository()
}

export function createServices(): AppServices {
  return {
    initiativeRepository: createInitiativeRepository(),
    signatureRepository: createSignatureRepository(),
    motionRepository: createMotionRepository(),
    voteRepository: createVoteRepository(),
    engagementRepository: createEngagementRepository(),
  }
}
