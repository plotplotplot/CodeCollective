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
import { APIEngagementRepository } from '../infrastructure/api/APIEngagementRepository'

/**
 * Application services container
 */
export type AppServices = {
  initiativeRepository: InitiativeRepository
  signatureRepository: SignatureRepository
  motionRepository: MotionRepository
  voteRepository: VoteRepository
  engagementRepository: EngagementRepository
}

/**
 * Configuration options for creating services
 */
export type ServicesConfig = {
  /** Data source type: 'mock' for localStorage, 'api' for backend */
  dataSource: 'mock' | 'api'
  /** API base URL (required when dataSource is 'api') */
  apiBaseUrl?: string
}

/**
 * Get configuration from environment variables
 */
function getConfig(): ServicesConfig {
  const env = (import.meta as any).env
  const dataSourceEnv = env?.VITE_DATA_SOURCE as string | undefined
  const dataSource =
    dataSourceEnv === 'api'
      ? 'api'
      : dataSourceEnv === 'mock'
      ? 'mock'
      : env?.PROD
      ? 'api'
      : 'mock'
  
  return {
    dataSource,
    apiBaseUrl: env?.VITE_API_BASE_URL || '/api/governance',
  }
}

/**
 * Factory functions for creating repositories
 * 
 * Following the Factory Method pattern to allow swapping implementations
 * without touching use cases or UI components.
 */

function createInitiativeRepository(_config: ServicesConfig): InitiativeRepository {
  // Currently only mock implementation available
  // TODO: Create APIInitiativeRepository when backend endpoints are ready
  return new MockInitiativeRepository()
}

function createSignatureRepository(_config: ServicesConfig): SignatureRepository {
  // Currently only mock implementation available
  return new MockSignatureRepository()
}

function createMotionRepository(_config: ServicesConfig): MotionRepository {
  // Currently only mock implementation available
  return new MockMotionRepository()
}

function createVoteRepository(_config: ServicesConfig): VoteRepository {
  // Currently only mock implementation available
  return new MockVoteRepository()
}

function createEngagementRepository(config: ServicesConfig): EngagementRepository {
  if (config.dataSource === 'api') {
    if (!config.apiBaseUrl) {
      throw new Error('API base URL is required when using api data source')
    }
    return new APIEngagementRepository(config.apiBaseUrl)
  }
  
  return new MockEngagementRepository()
}

/**
 * Create application services container
 * 
 * Usage:
 *   const services = createServices() // Uses env configuration
 *   
 *   // Or with explicit config:
 *   const services = createServices({ dataSource: 'api', apiBaseUrl: '/api' })
 */
export function createServices(config?: Partial<ServicesConfig>): AppServices {
  const finalConfig = { ...getConfig(), ...config }
  
  return {
    initiativeRepository: createInitiativeRepository(finalConfig),
    signatureRepository: createSignatureRepository(finalConfig),
    motionRepository: createMotionRepository(finalConfig),
    voteRepository: createVoteRepository(finalConfig),
    engagementRepository: createEngagementRepository(finalConfig),
  }
}

/**
 * Create services for testing
 * 
 * All repositories use mock implementations with isolated storage.
 */
export function createTestServices(): AppServices {
  return {
    initiativeRepository: new MockInitiativeRepository(),
    signatureRepository: new MockSignatureRepository(),
    motionRepository: new MockMotionRepository(),
    voteRepository: new MockVoteRepository(),
    engagementRepository: new MockEngagementRepository(),
  }
}
