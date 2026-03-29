import type { MotionRepository, MotionListQuery, CreateMotionInput } from '../../application/ports/MotionRepository'
import type { Motion, VoteResult } from '../../domain/motion/Motion'

const STORAGE_KEY = 'demo.motions'

function readAll(): Motion[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as Motion[]
  } catch {
    return []
  }
}

function writeAll(items: Motion[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

function seed(): Motion[] {
  const now = new Date()
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000)

  const motions: Motion[] = [
    {
      id: 'motion_seed_1',
      type: 'main',
      title: 'Adopt Ranked-Choice Voting for Board Elections',
      body: 'This motion proposes that all future board elections use ranked-choice voting to better reflect voter preferences and reduce the spoiler effect.',
      status: 'discussion',
      proposerId: 'user_alice',
      proposerName: 'Alice Chen',
      seconderId: 'user_bob',
      seconderName: 'Bob Martinez',
      createdAtISO: twoDaysAgo.toISOString(),
      updatedAtISO: yesterday.toISOString(),
      discussionDeadlineISO: new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      quorumRequired: 5,
      votes: [],
      score: 2,
    },
    {
      id: 'motion_seed_2',
      type: 'main',
      title: 'Allocate Community Fund for Park Restoration',
      body: 'Move that $15,000 from the community improvement fund be allocated to restore Riverside Park, including new benches, path resurfacing, and native plantings.',
      status: 'proposed',
      proposerId: 'user_carol',
      proposerName: 'Carol Davis',
      createdAtISO: yesterday.toISOString(),
      updatedAtISO: yesterday.toISOString(),
      quorumRequired: 5,
      votes: [],
      score: 1,
    },
    {
      id: 'motion_seed_3',
      type: 'main',
      title: 'Approve Annual Budget Report for Fiscal Year 2025',
      body: 'Motion to accept and approve the annual budget report as presented by the treasurer for fiscal year 2025.',
      status: 'passed',
      proposerId: 'user_alice',
      proposerName: 'Alice Chen',
      seconderId: 'user_carol',
      seconderName: 'Carol Davis',
      createdAtISO: twoDaysAgo.toISOString(),
      updatedAtISO: yesterday.toISOString(),
      quorumRequired: 5,
      votes: [
        { id: 'vote_s1', motionId: 'motion_seed_3', voterId: 'user_alice', voterName: 'Alice Chen', choice: 'yea', castAtISO: yesterday.toISOString() },
        { id: 'vote_s2', motionId: 'motion_seed_3', voterId: 'user_bob', voterName: 'Bob Martinez', choice: 'yea', castAtISO: yesterday.toISOString() },
        { id: 'vote_s3', motionId: 'motion_seed_3', voterId: 'user_carol', voterName: 'Carol Davis', choice: 'yea', castAtISO: yesterday.toISOString() },
        { id: 'vote_s4', motionId: 'motion_seed_3', voterId: 'user_dave', voterName: 'Dave Wilson', choice: 'nay', castAtISO: yesterday.toISOString() },
        { id: 'vote_s5', motionId: 'motion_seed_3', voterId: 'user_eve', voterName: 'Eve Park', choice: 'abstain', castAtISO: yesterday.toISOString() },
      ],
      result: {
        yea: 3,
        nay: 1,
        abstain: 1,
        totalEligible: 5,
        quorumMet: true,
        passed: true,
      },
      score: 5,
    },
  ]

  writeAll(motions)
  return motions
}

function ensureSeeded(): Motion[] {
  const existing = readAll()
  if (existing.length) return existing
  return seed()
}

function computeResult(motion: Motion): VoteResult {
  const yea = motion.votes.filter((v) => v.choice === 'yea').length
  const nay = motion.votes.filter((v) => v.choice === 'nay').length
  const abstain = motion.votes.filter((v) => v.choice === 'abstain').length
  const totalEligible = motion.quorumRequired
  const quorumMet = motion.votes.length >= motion.quorumRequired
  const passed = quorumMet && yea > nay
  return { yea, nay, abstain, totalEligible, quorumMet, passed }
}

export class MockMotionRepository implements MotionRepository {
  async list(query?: MotionListQuery): Promise<Motion[]> {
    let items = [...ensureSeeded()]
    const q = (query?.search ?? '').trim().toLowerCase()
    if (q) {
      items = items.filter(
        (m) => m.title.toLowerCase().includes(q) || m.body.toLowerCase().includes(q),
      )
    }
    if (query?.status?.length) {
      items = items.filter((m) => query.status!.includes(m.status))
    }
    if (query?.type) {
      items = items.filter((m) => m.type === query.type)
    }
    if (query?.parentMotionId) {
      items = items.filter((m) => m.parentMotionId === query.parentMotionId)
    }
    items.sort((a, b) => b.createdAtISO.localeCompare(a.createdAtISO))
    return items
  }

  async getById(id: string): Promise<Motion | null> {
    const items = ensureSeeded()
    return items.find((m) => m.id === id) ?? null
  }

  async create(input: CreateMotionInput): Promise<Motion> {
    const now = new Date().toISOString()
    const motion: Motion = {
      id: `motion_${Math.random().toString(16).slice(2)}`,
      type: input.type,
      parentMotionId: input.parentMotionId,
      title: input.title,
      body: input.body,
      proposedBodyDiff: input.proposedBodyDiff,
      status: 'proposed',
      proposerId: input.proposerId,
      proposerName: input.proposerName,
      createdAtISO: now,
      updatedAtISO: now,
      quorumRequired: input.quorumRequired,
      votes: [],
      score: 0,
    }
    const all = ensureSeeded()
    all.unshift(motion)
    writeAll(all)
    return motion
  }

  async second(motionId: string, userId: string, userName: string): Promise<Motion> {
    const all = ensureSeeded()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]
    if (motion.status !== 'proposed') throw new Error(`Motion must be in 'proposed' status to second`)
    motion.seconderId = userId
    motion.seconderName = userName
    motion.status = 'discussion'
    motion.updatedAtISO = new Date().toISOString()
    writeAll(all)
    return motion
  }

  async openVoting(motionId: string): Promise<Motion> {
    const all = ensureSeeded()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]
    motion.status = 'voting'
    motion.votingDeadlineISO = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    motion.updatedAtISO = new Date().toISOString()
    writeAll(all)
    return motion
  }

  async table(motionId: string): Promise<Motion> {
    const all = ensureSeeded()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]
    motion.status = 'tabled'
    motion.updatedAtISO = new Date().toISOString()
    writeAll(all)
    return motion
  }

  async withdraw(motionId: string, userId: string): Promise<Motion> {
    const all = ensureSeeded()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]
    if (motion.proposerId !== userId) throw new Error('Only the proposer may withdraw a motion')
    motion.status = 'withdrawn'
    motion.updatedAtISO = new Date().toISOString()
    writeAll(all)
    return motion
  }

  async resolveVoting(motionId: string): Promise<Motion> {
    const all = ensureSeeded()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]
    const result = computeResult(motion)
    motion.result = result
    motion.status = result.passed ? 'passed' : 'failed'
    motion.updatedAtISO = new Date().toISOString()
    writeAll(all)
    return motion
  }
}
