import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { listMotions } from '../../../application/usecases/listMotions'
import type { Motion, MotionStatus, VoteDirection } from '../../../domain/motion/Motion'
import type { MotionListQuery } from '../../../application/ports/MotionRepository'
import { MotionStatusBadge } from '../../components/governance/MotionStatusBadge'

const STATUS_FILTERS: (MotionStatus | null)[] = [
  null,
  'proposed',
  'discussion',
  'voting',
  'passed',
  'failed',
  'tabled',
]

const STATUS_LABELS: Record<string, string> = {
  all: 'All',
  proposed: 'Proposed',
  discussion: 'Discussion',
  voting: 'Voting',
  passed: 'Passed',
  failed: 'Failed',
  tabled: 'Tabled',
}

type SortMode = 'newest' | 'score'

function getGuestId(): string {
  const key = 'governance.guestId'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `guest_${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, id)
  }
  return id
}

export function MotionListPage() {
  const { motionRepository, engagementRepository } = useServices()
  const { user } = useAuth()
  const navigate = useNavigate()
  const effectiveUserId = user?.id ?? getGuestId()
  const effectiveUserName = user?.displayName ?? 'Guest'
  const [motions, setMotions] = useState<Motion[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<MotionStatus | null>(null)
  const [sortMode, setSortMode] = useState<SortMode>('newest')
  const [userVotes, setUserVotes] = useState<Record<string, VoteDirection | null>>({})

  useEffect(() => {
    document.title = 'ballot-sign \u2022 Governance'
  }, [])

  useEffect(() => {
    const query: MotionListQuery = {}
    if (search) query.search = search
    if (statusFilter) query.status = [statusFilter]
    listMotions(motionRepository, query).then((fetched) => {
      setMotions(fetched)
      {
        Promise.all(
          fetched.map((m) => engagementRepository.getUserVote(m.id, effectiveUserId).then((dir) => [m.id, dir] as const)),
        ).then((pairs) => {
          const map: Record<string, VoteDirection | null> = {}
          for (const [id, dir] of pairs) map[id] = dir
          setUserVotes(map)
        })
      }
    })
  }, [motionRepository, engagementRepository, search, statusFilter, effectiveUserId])

  const sortedMotions = [...motions].sort((a, b) => {
    if (sortMode === 'score') return b.score - a.score || b.createdAtISO.localeCompare(a.createdAtISO)
    return b.createdAtISO.localeCompare(a.createdAtISO)
  })

  async function handleVote(motionId: string, direction: 'up' | 'down', e: React.MouseEvent) {
    e.stopPropagation()
    const result =
      direction === 'up'
        ? await engagementRepository.upvote(motionId, effectiveUserId)
        : await engagementRepository.downvote(motionId, effectiveUserId)
    setMotions((prev) => prev.map((m) => (m.id === motionId ? { ...m, score: result.score } : m)))
    setUserVotes((prev) => ({ ...prev, [motionId]: result.userVote }))
  }

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 700, margin: 0 }}>Governance</h1>
        <Link
          to="/governance/propose"
          style={{
            background: 'var(--primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '0.5rem 1.25rem',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: 14,
          }}
        >
          Propose Motion
        </Link>
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="Search motions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: 200 }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: 13 }}>
          <span className="muted">Sort by:</span>
          <button
            type="button"
            onClick={() => setSortMode('score')}
            style={{
              padding: '0.25rem 0.65rem',
              borderRadius: 6,
              border: sortMode === 'score' ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
              background: sortMode === 'score' ? 'var(--primary)' : 'transparent',
              color: sortMode === 'score' ? '#fff' : 'inherit',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            Score
          </button>
          <button
            type="button"
            onClick={() => setSortMode('newest')}
            style={{
              padding: '0.25rem 0.65rem',
              borderRadius: 6,
              border: sortMode === 'newest' ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
              background: sortMode === 'newest' ? 'var(--primary)' : 'transparent',
              color: sortMode === 'newest' ? '#fff' : 'inherit',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            Newest
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        {STATUS_FILTERS.map((s) => {
          const label = s ? STATUS_LABELS[s] : STATUS_LABELS.all
          const active = statusFilter === s
          return (
            <button
              key={label}
              type="button"
              onClick={() => setStatusFilter(s)}
              style={{
                padding: '0.35rem 0.85rem',
                borderRadius: 8,
                border: active ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                background: active ? 'var(--primary)' : 'transparent',
                color: active ? '#fff' : 'inherit',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {sortedMotions.length === 0 ? (
        <p className="muted">No motions found.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {sortedMotions.map((motion) => {
            const uv = userVotes[motion.id] ?? null
            return (
              <div
                key={motion.id}
                onClick={() => navigate(`/governance/${motion.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') navigate(`/governance/${motion.id}`)
                }}
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-subtle)',
                  padding: '1.5rem',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s',
                  display: 'flex',
                  gap: '1rem',
                }}
              >
                {/* Vote widget */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    minWidth: 32,
                    flexShrink: 0,
                    gap: 2,
                  }}
                >
                  <button
                    type="button"
                    onClick={(e) => handleVote(motion.id, 'up', e)}
                    aria-label="Upvote"
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 18,
                      lineHeight: 1,
                      padding: 2,
                      color: uv === 'up' ? 'var(--primary)' : 'var(--text-muted, #999)',
                      fontWeight: uv === 'up' ? 700 : 400,
                    }}
                  >
                    ▲
                  </button>
                  <span style={{ fontWeight: 700, fontSize: 14, lineHeight: 1 }}>{motion.score}</span>
                  <button
                    type="button"
                    onClick={(e) => handleVote(motion.id, 'down', e)}
                    aria-label="Downvote"
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 18,
                      lineHeight: 1,
                      padding: 2,
                      color: uv === 'down' ? '#991b1b' : 'var(--text-muted, #999)',
                      fontWeight: uv === 'down' ? 700 : 400,
                    }}
                  >
                    ▼
                  </button>
                </div>

                {/* Card content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                    <MotionStatusBadge status={motion.status} />
                    <span style={{ fontWeight: 600, fontSize: 16 }}>{motion.title}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 13, marginBottom: '0.5rem' }}>
                    Proposed by {motion.proposerName} on {motion.createdAtISO.slice(0, 10)}
                  </div>
                  <p className="muted" style={{ margin: 0, fontSize: 14 }}>
                    {motion.body.length > 100 ? motion.body.slice(0, 100) + '...' : motion.body}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
