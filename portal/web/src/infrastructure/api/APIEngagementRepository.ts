import type { EngagementRepository, CreateCommentInput, UserProfile, RankedMotion, VoteCounts } from '../../application/ports/EngagementRepository'
import type { Motion, VoteDirection, Comment } from '../../domain/motion/Motion'

/**
 * API Error Classes for proper error handling
 */
export class APIError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
    public readonly responseBody?: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

export class AuthenticationError extends APIError {
  constructor(message = 'Authentication required') {
    super(message, 401)
    this.name = 'AuthenticationError'
  }
}

export class NotFoundError extends APIError {
  constructor(resource: string) {
    super(`${resource} not found`, 404)
    this.name = 'NotFoundError'
  }
}

/**
 * API Configuration
 */
const API_BASE = '/api/governance'
const REQUEST_TIMEOUT_MS = 30000

/**
 * Logger utility
 */
const logger = {
  debug: (message: string, ...args: unknown[]) => {
    if (import.meta.env.DEV) {
      console.debug(`[APIEngagement] ${message}`, ...args)
    }
  },
  error: (message: string, ...args: unknown[]) => {
    console.error(`[APIEngagement] ${message}`, ...args)
  }
}

/**
 * Get authentication headers from session storage
 */
function getAuthHeaders(): HeadersInit {
  const token = sessionStorage.getItem('pidp.token')
  if (!token) {
    throw new AuthenticationError()
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    })
    return response
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new APIError(`Request timeout after ${timeoutMs}ms`, 408)
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * Handle API response with proper error handling
 */
async function handleResponse<T>(resp: Response, context: string): Promise<T> {
  if (resp.ok) {
    return resp.json() as Promise<T>
  }
  
  const text = await resp.text().catch(() => 'Unknown error')
  
  switch (resp.status) {
    case 401:
      logger.error(`Authentication failed: ${context}`, { status: resp.status })
      throw new AuthenticationError()
    case 404:
      logger.error(`Resource not found: ${context}`, { status: resp.status })
      throw new NotFoundError(context)
    case 429:
      logger.error(`Rate limited: ${context}`, { status: resp.status })
      throw new APIError('Too many requests. Please try again later.', 429)
    default:
      logger.error(`API error: ${context}`, { status: resp.status, body: text })
      throw new APIError(
        `API error (${resp.status}): ${text || 'Unknown error'}`,
        resp.status,
        text
      )
  }
}

/**
 * API Response types matching backend
 */
interface CommentResponse {
  id: string
  motion_id: string
  author_id: string
  author_name: string
  body: string
  created_at: string
}

interface VoteResponse {
  score: number
  user_vote: VoteDirection | null
}

interface UserVoteResponse {
  user_vote: VoteDirection | null
}

/**
 * Convert API comment to domain comment
 */
function mapCommentResponse(data: CommentResponse): Comment {
  return {
    id: String(data.id),
    motionId: data.motion_id,
    authorId: data.author_id,
    authorName: data.author_name,
    body: data.body,
    createdAtISO: data.created_at,
  }
}

/**
 * Repository implementation using backend API
 */
export class APIEngagementRepository implements EngagementRepository {
  private readonly baseUrl: string

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  async upvote(motionId: string, _userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    logger.debug(`Upvoting motion: ${motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(motionId)}/upvote`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    )
    
    const data = await handleResponse<VoteResponse>(resp, `upvote motion ${motionId}`)
    return { score: data.score, userVote: data.user_vote }
  }

  async downvote(motionId: string, _userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    logger.debug(`Downvoting motion: ${motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(motionId)}/downvote`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    )
    
    const data = await handleResponse<VoteResponse>(resp, `downvote motion ${motionId}`)
    return { score: data.score, userVote: data.user_vote }
  }

  async getUserVote(motionId: string, _userId: string): Promise<VoteDirection | null> {
    logger.debug(`Getting user vote for motion: ${motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(motionId)}/user-vote`,
      {
        headers: getAuthHeaders(),
      }
    )
    
    const data = await handleResponse<UserVoteResponse>(resp, `get user vote for ${motionId}`)
    return data.user_vote
  }

  async listComments(motionId: string): Promise<Comment[]> {
    logger.debug(`Listing comments for motion: ${motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(motionId)}/comments`,
      {
        method: 'GET',
      }
    )
    
    if (resp.status === 404) {
      return []
    }
    
    const data = await handleResponse<CommentResponse[]>(resp, `list comments for ${motionId}`)
    return data.map(mapCommentResponse)
  }

  async addComment(input: CreateCommentInput): Promise<Comment> {
    logger.debug(`Adding comment to motion: ${input.motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(input.motionId)}/comments`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ body: input.body }),
      }
    )
    
    const data = await handleResponse<CommentResponse>(resp, `add comment to ${input.motionId}`)
    return mapCommentResponse(data)
  }

  async getVoteCounts(motionId: string): Promise<VoteCounts> {
    logger.debug(`Getting vote counts for motion: ${motionId}`)
    
    const resp = await fetchWithTimeout(
      `${this.baseUrl}/motions/${encodeURIComponent(motionId)}/vote-counts`,
      {
        method: 'GET',
      }
    )
    
    return handleResponse<VoteCounts>(resp, `get vote counts for ${motionId}`)
  }

  async trackView(_motionId: string, _userId: string): Promise<void> {
    // Not implemented in API yet - would need backend endpoint
    // For now, this is a no-op
    logger.debug(`Track view not implemented: ${_motionId}`)
  }

  async getUserProfile(_userId: string): Promise<UserProfile> {
    // Not implemented in API yet - would need backend endpoint
    // Return a default profile for now
    logger.debug(`Get user profile not implemented: ${_userId}`)
    return {
      userId: _userId,
      interactedMotionIds: [],
      preferredStatuses: {},
      totalInteractions: 0,
    }
  }

  async rankMotions(motions: Motion[], _userId: string): Promise<RankedMotion[]> {
    logger.debug(`Ranking ${motions.length} motions`)
    
    // Get vote counts and comment counts for all motions in parallel
    const rankedMotions = await Promise.all(
      motions.map(async (motion) => {
        try {
          const [voteCounts, comments] = await Promise.all([
            this.getVoteCounts(motion.id),
            this.listComments(motion.id),
          ])

          const commentCount = comments.length

          // Reddit-style ranking algorithm
          // rank = voteWeight + engagementWeight + recencyWeight + affinityBoost
          const sign = voteCounts.score > 0 ? 1 : voteCounts.score < 0 ? -1 : 0
          const voteWeight = Math.log10(Math.max(Math.abs(voteCounts.score), 1)) * sign * 4
          const engagementWeight = Math.log10(commentCount + 1) * 2
          const ageMs = Date.now() - new Date(motion.createdAtISO).getTime()
          const ageHours = ageMs / (1000 * 60 * 60)
          const recencyWeight = -ageHours / 12

          // No affinity boost since we don't have user profile from API yet
          const rank = voteWeight + engagementWeight + recencyWeight

          return {
            ...motion,
            rank,
            commentCount,
            voteCounts,
          }
        } catch (error) {
          logger.error(`Failed to rank motion ${motion.id}`, error)
          // Return motion with default values on error
          return {
            ...motion,
            rank: 0,
            commentCount: 0,
            voteCounts: { up: 0, down: 0, score: 0 },
          }
        }
      })
    )

    return rankedMotions.sort((a, b) => b.rank - a.rank)
  }
}
