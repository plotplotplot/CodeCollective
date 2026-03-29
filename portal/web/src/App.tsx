import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, useServices } from './app/AppProviders'
import { Header } from './ui/shell/Header'
import { Footer } from './ui/shell/Footer'
import { listMotions } from './application/usecases/listMotions'
import { MotionStatusBadge } from './ui/components/governance/MotionStatusBadge'
import type { VoteDirection } from './domain/motion/Motion'
import type { RankedMotion } from './application/ports/EngagementRepository'

function getGuestId(): string {
  const key = 'governance.guestId'
  let id = localStorage.getItem(key)
  if (!id) {
    id = `guest_${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, id)
  }
  return id
}

function timeAgo(isoDate: string): string {
  const ms = Date.now() - new Date(isoDate).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(isoDate).toLocaleDateString()
}

export default function App() {
  const { user } = useAuth()
  const { motionRepository, engagementRepository } = useServices()
  const navigate = useNavigate()
  const effectiveUserId = user?.id ?? getGuestId()

  const [ranked, setRanked] = useState<RankedMotion[]>([])
  const [userVotes, setUserVotes] = useState<Record<string, VoteDirection | null>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    document.title = 'Code Collective'
    listMotions(motionRepository).then(async (motions) => {
      const rankedMotions = await engagementRepository.rankMotions(motions, effectiveUserId)
      setRanked(rankedMotions)
      setLoading(false)

      const pairs = await Promise.all(
        rankedMotions.map((m) =>
          engagementRepository.getUserVote(m.id, effectiveUserId).then((dir) => [m.id, dir] as const),
        ),
      )
      const map: Record<string, VoteDirection | null> = {}
      for (const [id, dir] of pairs) map[id] = dir
      setUserVotes(map)
    })
  }, [motionRepository, engagementRepository, effectiveUserId])

  async function handleVote(motionId: string, direction: 'up' | 'down', e: React.MouseEvent) {
    e.stopPropagation()
    const result =
      direction === 'up'
        ? await engagementRepository.upvote(motionId, effectiveUserId)
        : await engagementRepository.downvote(motionId, effectiveUserId)
    setRanked((prev) => prev.map((m) => (m.id === motionId ? { ...m, score: result.score } : m)))
    setUserVotes((prev) => ({ ...prev, [motionId]: result.userVote }))
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div style={{ maxWidth: 680, margin: '0 auto', padding: '0 16px' }}>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)' }}>
              Loading...
            </div>
          ) : ranked.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '80px 0',
            }}>
              <p style={{ color: 'var(--text-muted)', fontSize: 15, margin: '0 0 16px' }}>
                No motions yet.
              </p>
              <Link
                to="/governance/propose"
                style={{
                  display: 'inline-flex',
                  background: 'var(--primary)',
                  color: '#fff',
                  borderRadius: 999,
                  padding: '10px 24px',
                  fontWeight: 700,
                  fontSize: 14,
                  textDecoration: 'none',
                }}
              >
                Be the first to propose
              </Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {ranked.map((motion, i) => {
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
                      display: 'flex',
                      gap: 0,
                      padding: '12px 0',
                      borderBottom: i < ranked.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                      cursor: 'pointer',
                      transition: 'background 0.1s',
                      borderRadius: 8,
                      margin: '0 -8px',
                      padding: '12px 8px',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--panel-2)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                  >
                    {/* Vote column */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      width: 48,
                      flexShrink: 0,
                      paddingTop: 2,
                    }}>
                      <button
                        type="button"
                        onClick={(e) => handleVote(motion.id, 'up', e)}
                        aria-label="Upvote"
                        style={{
                          background: uv === 'up' ? 'var(--vote-up-bg)' : 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 4,
                          borderRadius: 6,
                          color: uv === 'up' ? 'var(--vote-up)' : 'var(--vote-neutral)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.12s',
                          width: 28,
                          height: 28,
                        }}
                        onMouseEnter={(e) => { if (uv !== 'up') { e.currentTarget.style.background = 'var(--vote-up-hover)'; e.currentTarget.style.color = 'var(--vote-up)' } }}
                        onMouseLeave={(e) => { if (uv !== 'up') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--vote-neutral)' } }}
                      >
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3l7 7h-4v7H7v-7H3l7-7z"/></svg>
                      </button>
                      <span style={{
                        fontWeight: 800,
                        fontSize: 13,
                        lineHeight: 1,
                        padding: '2px 0',
                        color: uv === 'up' ? 'var(--vote-up)' : uv === 'down' ? 'var(--vote-down)' : 'var(--text-primary)',
                      }}>
                        {motion.score}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => handleVote(motion.id, 'down', e)}
                        aria-label="Downvote"
                        style={{
                          background: uv === 'down' ? 'var(--vote-down-bg)' : 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 4,
                          borderRadius: 6,
                          color: uv === 'down' ? 'var(--vote-down)' : 'var(--vote-neutral)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.12s',
                          width: 28,
                          height: 28,
                        }}
                        onMouseEnter={(e) => { if (uv !== 'down') { e.currentTarget.style.background = 'var(--vote-down-hover)'; e.currentTarget.style.color = 'var(--vote-down)' } }}
                        onMouseLeave={(e) => { if (uv !== 'down') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--vote-neutral)' } }}
                      >
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path d="M10 17l-7-7h4V3h6v7h4l-7 7z"/></svg>
                      </button>
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1, minWidth: 0, paddingLeft: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                        <MotionStatusBadge status={motion.status} />
                        <span style={{
                          fontWeight: 700,
                          fontSize: 15,
                          color: 'var(--text-primary)',
                          lineHeight: 1.3,
                        }}>
                          {motion.title}
                        </span>
                      </div>
                      <div style={{
                        fontSize: 12,
                        color: 'var(--text-muted)',
                        display: 'flex',
                        gap: 8,
                        alignItems: 'center',
                        flexWrap: 'wrap',
                      }}>
                        <span>by {motion.proposerName}</span>
                        <span>&middot;</span>
                        <span>{timeAgo(motion.createdAtISO)}</span>
                        {motion.commentCount > 0 && (
                          <>
                            <span>&middot;</span>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                              <svg width="12" height="12" viewBox="0 0 20 20" fill="currentColor" style={{ opacity: 0.6 }}>
                                <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v7a2 2 0 01-2 2H8l-4 3v-3H4a2 2 0 01-2-2V5z"/>
                              </svg>
                              {motion.commentCount}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
