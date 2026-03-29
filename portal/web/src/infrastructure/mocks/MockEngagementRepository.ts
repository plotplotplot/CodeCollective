import type { EngagementRepository, CreateCommentInput } from '../../application/ports/EngagementRepository'
import type { VoteDirection, Comment } from '../../domain/motion/Motion'

const VOTES_KEY = 'demo.engagement.votes'
const COMMENTS_KEY = 'demo.engagement.comments'

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

  async upvote(motionId: string, userId: string): Promise<{ score: number; userVote: VoteDirection | null }> {
    const votes = readVotes()
    if (!votes[motionId]) votes[motionId] = {}

    const current = votes[motionId][userId]
    if (current === 'up') {
      delete votes[motionId][userId]
    } else {
      votes[motionId][userId] = 'up'
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
}
