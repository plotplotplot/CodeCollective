import { Pool } from 'pg'
import type { EngagementRepository, CreateCommentInput, UserProfile, RankedMotion, VoteCounts } from '../../application/ports/EngagementRepository'
import type { Motion, VoteDirection, Comment } from '../../domain/motion/Motion'

export class PostgreSQLEngagementRepository implements EngagementRepository {
  private pool: Pool

  constructor(databaseUrl: string) {
    this.pool = new Pool({
      connectionString: databaseUrl,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
    })

    // Initialize tables if they don't exist
    this.initializeTables()
  }

  private async initializeTables(): Promise<void> {
    const schema = `
      CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

      CREATE TABLE IF NOT EXISTS comments (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          motion_id VARCHAR(255) NOT NULL,
          author_id VARCHAR(255) NOT NULL,
          author_name VARCHAR(255) NOT NULL,
          body TEXT NOT NULL,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS votes (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          motion_id VARCHAR(255) NOT NULL,
          user_id VARCHAR(255) NOT NULL,
          direction VARCHAR(10) NOT NULL CHECK (direction IN ('up', 'down')),
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (motion_id, user_id)
      );

      CREATE TABLE IF NOT EXISTS user_profiles (
          user_id VARCHAR(255) PRIMARY KEY,
          interacted_motion_ids JSONB DEFAULT '[]'::jsonb,
          preferred_statuses JSONB DEFAULT '{}'::jsonb,
          total_interactions INTEGER DEFAULT 0,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS motion_views (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          motion_id VARCHAR(255) NOT NULL,
          user_id VARCHAR(255) NOT NULL,
          viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
      );

      CREATE INDEX IF NOT EXISTS idx_comments_motion_id ON comments(motion_id);
      CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
      CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);
      CREATE INDEX IF NOT EXISTS idx_votes_motion_id ON votes(motion_id);
      CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes(user_id);
      CREATE INDEX IF NOT EXISTS idx_motion_views_motion_id ON motion_views(motion_id);
      CREATE INDEX IF NOT EXISTS idx_motion_views_user_id ON motion_views(user_id);
    `

    try {
      await this.pool.query(schema)
    } catch (error) {
      console.error('Failed to initialize governance tables:', error)
    }
  }

  async upvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    const client = await this.pool.connect()
    try {
      await client.query('BEGIN')

      // Remove any existing vote
      await client.query('DELETE FROM votes WHERE motion_id = $1 AND user_id = $2', [motionId, userId])

      // Insert upvote
      await client.query(
        'INSERT INTO votes (motion_id, user_id, direction) VALUES ($1, $2, $3)',
        [motionId, userId, 'up']
      )

      await client.query('COMMIT')

      const result = await this.getVoteCounts(motionId)
      return { score: result.score, userVote: 'up' }
    } catch (error) {
      await client.query('ROLLBACK')
      throw error
    } finally {
      client.release()
    }
  }

  async downvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    const client = await this.pool.connect()
    try {
      await client.query('BEGIN')

      // Remove any existing vote
      await client.query('DELETE FROM votes WHERE motion_id = $1 AND user_id = $2', [motionId, userId])

      // Insert downvote
      await client.query(
        'INSERT INTO votes (motion_id, user_id, direction) VALUES ($1, $2, $3)',
        [motionId, userId, 'down']
      )

      await client.query('COMMIT')

      const result = await this.getVoteCounts(motionId)
      return { score: result.score, userVote: 'down' }
    } catch (error) {
      await client.query('ROLLBACK')
      throw error
    } finally {
      client.release()
    }
  }

  async getUserVote(motionId: string, userId: string): Promise<VoteDirection | null> {
    const result = await this.pool.query(
      'SELECT direction FROM votes WHERE motion_id = $1 AND user_id = $2',
      [motionId, userId]
    )
    return result.rows.length > 0 ? result.rows[0].direction as VoteDirection : null
  }

  async listComments(motionId: string): Promise<Comment[]> {
    const result = await this.pool.query(
      'SELECT id, motion_id as "motionId", author_id as "authorId", author_name as "authorName", body, created_at as "createdAtISO" FROM comments WHERE motion_id = $1 ORDER BY created_at ASC',
      [motionId]
    )

    return result.rows.map(row => ({
      ...row,
      createdAtISO: row.createdAtISO.toISOString()
    }))
  }

  async addComment(input: CreateCommentInput): Promise<Comment> {
    const result = await this.pool.query(
      'INSERT INTO comments (motion_id, author_id, author_name, body) VALUES ($1, $2, $3, $4) RETURNING id, motion_id as "motionId", author_id as "authorId", author_name as "authorName", body, created_at as "createdAtISO"',
      [input.motionId, input.authorId, input.authorName, input.body]
    )

    const row = result.rows[0]
    return {
      ...row,
      createdAtISO: row.createdAtISO.toISOString()
    }
  }

  async getVoteCounts(motionId: string): Promise<VoteCounts> {
    const result = await this.pool.query(
      'SELECT direction, COUNT(*) as count FROM votes WHERE motion_id = $1 GROUP BY direction',
      [motionId]
    )

    let up = 0
    let down = 0

    for (const row of result.rows) {
      if (row.direction === 'up') up = parseInt(row.count)
      if (row.direction === 'down') down = parseInt(row.count)
    }

    return { up, down, score: up - down }
  }

  async trackView(motionId: string, userId: string): Promise<void> {
    try {
      await this.pool.query(
        'INSERT INTO motion_views (motion_id, user_id) VALUES ($1, $2)',
        [motionId, userId]
      )
    } catch (error) {
      // Ignore duplicate view tracking errors
      if (!error.message.includes('duplicate key')) {
        throw error
      }
    }
  }

  async getUserProfile(userId: string): Promise<UserProfile> {
    const result = await this.pool.query(
      'SELECT user_id as "userId", interacted_motion_ids as "interactedMotionIds", preferred_statuses as "preferredStatuses", total_interactions as "totalInteractions" FROM user_profiles WHERE user_id = $1',
      [userId]
    )

    if (result.rows.length === 0) {
      // Create default profile
      await this.pool.query(
        'INSERT INTO user_profiles (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING',
        [userId]
      )
      return {
        userId,
        interactedMotionIds: [],
        preferredStatuses: {},
        totalInteractions: 0
      }
    }

    const row = result.rows[0]
    return {
      userId: row.userId,
      interactedMotionIds: row.interactedMotionIds || [],
      preferredStatuses: row.preferredStatuses || {},
      totalInteractions: row.totalInteractions || 0
    }
  }

  async rankMotions(motions: Motion[], userId: string): Promise<RankedMotion[]> {
    const profile = await this.getUserProfile(userId)

    // Get comment counts and vote counts for all motions
    const motionIds = motions.map(m => m.id)
    const placeholders = motionIds.map((_, i) => `$${i + 1}`).join(',')

    const commentsResult = await this.pool.query(
      `SELECT motion_id, COUNT(*) as count FROM comments WHERE motion_id IN (${placeholders}) GROUP BY motion_id`,
      motionIds
    )

    const commentCounts: Record<string, number> = {}
    for (const row of commentsResult.rows) {
      commentCounts[row.motion_id] = parseInt(row.count)
    }

    const voteResults = await Promise.all(motionIds.map(id => this.getVoteCounts(id)))
    const voteCounts: Record<string, VoteCounts> = {}
    motionIds.forEach((id, index) => {
      voteCounts[id] = voteResults[index]
    })

    return motions.map(motion => {
      const commentCount = commentCounts[motion.id] || 0
      const vc = voteCounts[motion.id]

      // Reddit-style ranking algorithm
      const sign = vc.score > 0 ? 1 : vc.score < 0 ? -1 : 0
      const voteWeight = Math.log10(Math.max(Math.abs(vc.score), 1)) * sign * 4

      const engagementWeight = Math.log10(commentCount + 1) * 2

      const ageMs = Date.now() - new Date(motion.createdAtISO).getTime()
      const ageHours = ageMs / (1000 * 60 * 60)
      const recencyWeight = -ageHours / 12

      let affinityBoost = 0
      if (profile.totalInteractions > 0) {
        const statusCount = profile.preferredStatuses[motion.status] || 0
        const ratio = statusCount / profile.totalInteractions
        affinityBoost = ratio * 2
      }

      const rank = voteWeight + engagementWeight + recencyWeight + affinityBoost

      return {
        ...motion,
        rank,
        commentCount,
        voteCounts: vc
      }
    }).sort((a, b) => b.rank - a.rank)
  }

  async close(): Promise<void> {
    await this.pool.end()
  }
}