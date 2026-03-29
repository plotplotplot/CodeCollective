import type { EngagementRepository, CreateCommentInput, UserProfile, RankedMotion } from '../../application/ports/EngagementRepository'
import type { Motion, VoteDirection, Comment } from '../../domain/motion/Motion'

const VOTES_KEY = 'demo.engagement.votes'
const COMMENTS_KEY = 'demo.engagement.comments'
const PROFILE_KEY = 'demo.engagement.profiles'

type VotesStore = Record<string, Record<string, VoteDirection>>

function readVotes(): VotesStore {
  const raw = localStorage.getItem(VOTES_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw) as VotesStore
  } catch {
    return {}
  }
}

function writeVotes(votes: VotesStore) {
  localStorage.setItem(VOTES_KEY, JSON.stringify(votes))
}

function readComments(): Comment[] {
  const raw = localStorage.getItem(COMMENTS_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as Comment[]
  } catch {
    return []
  }
}

function writeComments(comments: Comment[]) {
  localStorage.setItem(COMMENTS_KEY, JSON.stringify(comments))
}

function computeScore(votes: VotesStore, motionId: string): number {
  const motionVotes = votes[motionId]
  if (!motionVotes) return 0
  let score = 0
  for (const dir of Object.values(motionVotes)) {
    if (dir === 'up') score++
    else if (dir === 'down') score--
  }
  return score
}

type ProfileStore = Record<string, UserProfile>

function readProfiles(): ProfileStore {
  const raw = localStorage.getItem(PROFILE_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw) as ProfileStore
  } catch {
    return {}
  }
}

function writeProfiles(profiles: ProfileStore) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profiles))
}

function getOrCreateProfile(userId: string): UserProfile {
  const profiles = readProfiles()
  if (profiles[userId]) return profiles[userId]
  return { userId, interactedMotionIds: [], preferredStatuses: {}, totalInteractions: 0 }
}

function recordInteraction(userId: string, motionId: string, motionStatus: string) {
  const profiles = readProfiles()
  const profile = profiles[userId] ?? { userId, interactedMotionIds: [], preferredStatuses: {}, totalInteractions: 0 }
  if (!profile.interactedMotionIds.includes(motionId)) {
    profile.interactedMotionIds.push(motionId)
  }
  profile.preferredStatuses[motionStatus] = (profile.preferredStatuses[motionStatus] ?? 0) + 1
  profile.totalInteractions += 1
  profiles[userId] = profile
  writeProfiles(profiles)
}

/**
 * Ranking algorithm inspired by Reddit's Hot sort.
 *
 * rank = voteWeight + engagementWeight + recencyWeight + affinityBoost
 *
 * - voteWeight: log10(max(|score|, 1)) * sign(score)  — logarithmic so first votes matter most
 * - engagementWeight: log10(commentCount + 1) * 0.5    — comments signal active discussion
 * - recencyWeight: ageHours / -12                      — lose 1 point per 12 hours of age
 * - affinityBoost: 0-2 points if user's profile shows preference for this motion's status
 */
function computeRank(
  motion: Motion,
  commentCount: number,
  profile: UserProfile,
): number {
  // Vote weight (logarithmic)
  const sign = motion.score > 0 ? 1 : motion.score < 0 ? -1 : 0
  const voteWeight = Math.log10(Math.max(Math.abs(motion.score), 1)) * sign * 4

  // Engagement weight
  const engagementWeight = Math.log10(commentCount + 1) * 2

  // Recency: hours since creation
  const ageMs = Date.now() - new Date(motion.createdAtISO).getTime()
  const ageHours = ageMs / (1000 * 60 * 60)
  const recencyWeight = -ageHours / 12

  // Affinity: boost if user engages with this status type
  let affinityBoost = 0
  if (profile.totalInteractions > 0) {
    const statusCount = profile.preferredStatuses[motion.status] ?? 0
    const ratio = statusCount / profile.totalInteractions
    affinityBoost = ratio * 2
  }

  return voteWeight + engagementWeight + recencyWeight + affinityBoost
}

function ensureSeeded(): void {
  if (localStorage.getItem(VOTES_KEY)) return

  const votes: VotesStore = {
    motion_seed_1: {
      user_voter_a: 'up',
      user_voter_b: 'up',
      user_voter_c: 'up',
      user_voter_d: 'down',
    },
    motion_seed_2: {
      user_voter_a: 'up',
    },
    motion_seed_3: {
      user_voter_a: 'up',
      user_voter_b: 'up',
      user_voter_c: 'up',
      user_voter_d: 'up',
      user_voter_e: 'up',
    },
  }
  writeVotes(votes)

  const now = new Date()
  const comments: Comment[] = [
    {
      id: 'comment_seed_1',
      motionId: 'motion_seed_1',
      authorId: 'user_bob',
      authorName: 'Bob Martinez',
      body: 'I think ranked-choice voting would be a great improvement. It really does reduce the spoiler effect in elections.',
      createdAtISO: new Date(now.getTime() - 20 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'comment_seed_2',
      motionId: 'motion_seed_1',
      authorId: 'user_carol',
      authorName: 'Carol Davis',
      body: 'Has anyone looked into the implementation cost? We should make sure our voting platform supports RCV before committing.',
      createdAtISO: new Date(now.getTime() - 12 * 60 * 60 * 1000).toISOString(),
    },
  ]
  writeComments(comments)
}

export class MockEngagementRepository implements EngagementRepository {
  constructor() {
    ensureSeeded()
  }

  private getMotionStatus(motionId: string): string {
    const raw = localStorage.getItem('demo.motions')
    if (!raw) return 'proposed'
    try {
      const motions = JSON.parse(raw) as Motion[]
      return motions.find((m) => m.id === motionId)?.status ?? 'proposed'
    } catch {
      return 'proposed'
    }
  }

  async upvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    const votes = readVotes()
    if (!votes[motionId]) votes[motionId] = {}

    const current = votes[motionId][userId]
    if (current === 'up') {
      delete votes[motionId][userId]
    } else {
      votes[motionId][userId] = 'up'
      recordInteraction(userId, motionId, this.getMotionStatus(motionId))
    }

    writeVotes(votes)
    const userVote = votes[motionId][userId] ?? null
    return { score: computeScore(votes, motionId), userVote }
  }

  async downvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    const votes = readVotes()
    if (!votes[motionId]) votes[motionId] = {}

    const current = votes[motionId][userId]
    if (current === 'down') {
      delete votes[motionId][userId]
    } else {
      votes[motionId][userId] = 'down'
      recordInteraction(userId, motionId, this.getMotionStatus(motionId))
    }

    writeVotes(votes)
    const userVote = votes[motionId][userId] ?? null
    return { score: computeScore(votes, motionId), userVote }
  }

  async getUserVote(motionId: string, userId: string): Promise<VoteDirection | null> {
    const votes = readVotes()
    return votes[motionId]?.[userId] ?? null
  }

  async listComments(motionId: string): Promise<Comment[]> {
    const comments = readComments()
    return comments
      .filter((c) => c.motionId === motionId)
      .sort((a, b) => a.createdAtISO.localeCompare(b.createdAtISO))
  }

  async addComment(input: CreateCommentInput): Promise<Comment> {
    const comment: Comment = {
      id: `comment_${Math.random().toString(16).slice(2)}`,
      motionId: input.motionId,
      authorId: input.authorId,
      authorName: input.authorName,
      body: input.body,
      createdAtISO: new Date().toISOString(),
    }
    const all = readComments()
    all.push(comment)
    writeComments(all)
    return comment
  }

  async trackView(motionId: string, userId: string): Promise<void> {
    // We need the motion status to record properly, but just record the interaction ID
    const profiles = readProfiles()
    const profile = profiles[userId] ?? { userId, interactedMotionIds: [], preferredStatuses: {}, totalInteractions: 0 }
    if (!profile.interactedMotionIds.includes(motionId)) {
      profile.interactedMotionIds.push(motionId)
      profile.totalInteractions += 1
      profiles[userId] = profile
      writeProfiles(profiles)
    }
  }

  async getUserProfile(userId: string): Promise<UserProfile> {
    return getOrCreateProfile(userId)
  }

  async rankMotions(motions: Motion[], userId: string): Promise<RankedMotion[]> {
    const profile = getOrCreateProfile(userId)
    const comments = readComments()

    return motions
      .map((motion) => {
        const commentCount = comments.filter((c) => c.motionId === motion.id).length
        const rank = computeRank(motion, commentCount, profile)
        return { ...motion, rank, commentCount }
      })
      .sort((a, b) => b.rank - a.rank)
  }
}
