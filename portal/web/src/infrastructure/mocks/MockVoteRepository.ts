import type { VoteRepository } from '../../application/ports/VoteRepository'
import type { Motion, Vote, VoteChoice, VoteResult } from '../../domain/motion/Motion'

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

function computeResult(motion: Motion): VoteResult {
  const yea = motion.votes.filter((v) => v.choice === 'yea').length
  const nay = motion.votes.filter((v) => v.choice === 'nay').length
  const abstain = motion.votes.filter((v) => v.choice === 'abstain').length
  const totalEligible = motion.quorumRequired
  const quorumMet = motion.votes.length >= motion.quorumRequired
  const passed = quorumMet && yea > nay
  return { yea, nay, abstain, totalEligible, quorumMet, passed }
}

export class MockVoteRepository implements VoteRepository {
  async castVote(motionId: string, voterId: string, voterName: string, choice: VoteChoice): Promise<Vote> {
    const all = readAll()
    const idx = all.findIndex((m) => m.id === motionId)
    if (idx === -1) throw new Error(`Motion not found: ${motionId}`)
    const motion = all[idx]

    const vote: Vote = {
      id: `vote_${Math.random().toString(16).slice(2)}`,
      motionId,
      voterId,
      voterName,
      choice,
      castAtISO: new Date().toISOString(),
    }
    motion.votes.push(vote)

    // Auto-resolve if quorum reached
    if (motion.votes.length >= motion.quorumRequired) {
      const result = computeResult(motion)
      motion.result = result
      motion.status = result.passed ? 'passed' : 'failed'
      motion.updatedAtISO = new Date().toISOString()
    }

    writeAll(all)
    return vote
  }

  async getResults(motionId: string): Promise<VoteResult> {
    const all = readAll()
    const motion = all.find((m) => m.id === motionId)
    if (!motion) throw new Error(`Motion not found: ${motionId}`)
    return computeResult(motion)
  }
}
