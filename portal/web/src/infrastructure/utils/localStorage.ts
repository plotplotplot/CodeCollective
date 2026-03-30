const VOTES_KEY = 'demo.engagement.votes'
const COMMENTS_KEY = 'demo.engagement.comments'
const PROFILE_KEY = 'demo.engagement.profiles'

export type VotesStore = Record<string, Record<string, import('../../domain/motion/Motion').VoteDirection>>

export function readVotes(): VotesStore {
  const raw = localStorage.getItem(VOTES_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw) as VotesStore
  } catch {
    return {}
  }
}

export function writeVotes(votes: VotesStore) {
  localStorage.setItem(VOTES_KEY, JSON.stringify(votes))
}

export type CommentStore = import('../../domain/motion/Motion').Comment[]

export function readComments(): CommentStore {
  const raw = localStorage.getItem(COMMENTS_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as CommentStore
  } catch {
    return []
  }
}

export function writeComments(comments: CommentStore) {
  localStorage.setItem(COMMENTS_KEY, JSON.stringify(comments))
}

export type ProfileStore = Record<string, import('../../application/ports/EngagementRepository').UserProfile>

export function readProfiles(): ProfileStore {
  const raw = localStorage.getItem(PROFILE_KEY)
  if (!raw) return {}
  try {
    return JSON.parse(raw) as ProfileStore
  } catch {
    return {}
  }
}

export function writeProfiles(profiles: ProfileStore) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profiles))
}