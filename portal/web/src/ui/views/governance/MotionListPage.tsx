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
    <div style={{ maxWidth: 920, margin: '0 auto', padding: '40px 20px' }}>
      {/* Page header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 32,
      }}>
        <h1 style={{
          fontSize: 28,
          fontWeight: 800,
          margin: 0,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
        }}>
          Governance
        </h1>
        <Link
          to="/governance/propose"
          style={{
            background: 'var(--primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 999,
            padding: '10px 24px',
            textDecoration: 'none',
            fontWeight: 700,
            fontSize: 14,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            transition: 'background 0.15s',
          }}
        >
          + Propose Motion
        </Link>
      </div>

      {/* Search + Sort row */}
      <div style={{
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        flexWrap: 'wrap',
        marginBottom: 16,
      }}>
        <div style={{ flex: 1, minWidth: 220, position: 'relative' }}>
          <input
            type="text"
            placeholder="Search motions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '12px 16px',
              fontSize: 14,
              border: '1px solid var(--border)',
              borderRadius: 12,
              backgroundColor: 'var(--panel)',
              color: 'var(--text-primary)',
              outline: 'none',
              transition: 'border-color 0.15s',
              boxSizing: 'border-box',
            }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>Sort:</span>
          {(['score', 'newest'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setSortMode(mode)}
              style={{
                padding: '6px 14px',
                borderRadius: 999,
                border: 'none',
                background: sortMode === mode ? 'var(--primary)' : 'var(--surface)',
                color: sortMode === mode ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
                transition: 'all 0.15s',
              }}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Status filter pills */}
      <div style={{
        display: 'flex',
        gap: 8,
        flexWrap: 'wrap',
        marginBottom: 28,
      }}>
        {STATUS_FILTERS.map((s) => {
          const label = s ? STATUS_LABELS[s] : STATUS_LABELS.all
          const active = statusFilter === s
          return (
            <button
              key={label}
              type="button"
              onClick={() => setStatusFilter(s)}
              style={{
                padding: '7px 16px',
                borderRadius: 999,
                border: active ? 'none' : '1px solid var(--border-subtle)',
                background: active ? 'var(--primary)' : 'var(--panel)',
                color: active ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
                transition: 'all 0.15s',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Motion list */}
      {sortedMotions.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '48px 20px',
          color: 'var(--text-muted)',
          fontSize: 15,
        }}>
          No motions found.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
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
                  boxShadow: 'var(--shadow-card)',
                  padding: '20px 24px',
                  cursor: 'pointer',
                  transition: 'box-shadow 0.2s, transform 0.2s',
                  display: 'flex',
                  gap: 16,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-1px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                {/* Vote widget */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    minWidth: 44,
                    flexShrink: 0,
                    gap: 2,
                    paddingTop: 2,
                  }}
                >
                  <button
                    type="button"
                    onClick={(e) => handleVote(motion.id, 'up', e)}
                    aria-label="Upvote"
                    style={{
                      background: uv === 'up' ? 'var(--primary-light)' : 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 16,
                      lineHeight: 1,
                      padding: 6,
                      borderRadius: 8,
                      color: uv === 'up' ? 'var(--primary)' : 'var(--text-muted)',
                      fontWeight: 700,
                      minWidth: 36,
                      minHeight: 36,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'background 0.15s',
                    }}
                  >
                    &#9650;
                  </button>
                  <span style={{
                    fontWeight: 800,
                    fontSize: 15,
                    lineHeight: 1,
                    color: 'var(--text-primary)',
                  }}>
                    {motion.score}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleVote(motion.id, 'down', e)}
                    aria-label="Downvote"
                    style={{
                      background: uv === 'down' ? 'var(--accent-red-bg)' : 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 16,
                      lineHeight: 1,
                      padding: 6,
                      borderRadius: 8,
                      color: uv === 'down' ? 'var(--accent-red)' : 'var(--text-muted)',
                      fontWeight: 700,
                      minWidth: 36,
                      minHeight: 36,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'background 0.15s',
                    }}
                  >
                    &#9660;
                  </button>
                </div>

                {/* Card content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    marginBottom: 8,
                    flexWrap: 'wrap',
                  }}>
                    <MotionStatusBadge status={motion.status} />
                    <span style={{
                      fontWeight: 700,
                      fontSize: 16,
                      color: 'var(--text-primary)',
                      letterSpacing: '-0.01em',
                    }}>
                      {motion.title}
                    </span>
                  </div>
                  <div style={{
                    fontSize: 13,
                    color: 'var(--text-muted)',
                    marginBottom: 6,
                  }}>
                    Proposed by {motion.proposerName} on {motion.createdAtISO.slice(0, 10)}
                  </div>
                  <p style={{
                    margin: 0,
                    fontSize: 14,
                    color: 'var(--text-secondary)',
                    lineHeight: 1.5,
                  }}>
                    {motion.body.length > 120 ? motion.body.slice(0, 120) + '...' : motion.body}
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
