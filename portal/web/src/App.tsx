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
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d`
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
    setRanked((prev) => prev.map((m) => {
      if (m.id !== motionId) return m
      const oldDir = userVotes[motionId]
      const vc = { ...m.voteCounts }
      if (oldDir === 'up') vc.up--
      else if (oldDir === 'down') vc.down--
      if (result.userVote === 'up') vc.up++
      else if (result.userVote === 'down') vc.down++
      vc.score = vc.up - vc.down
      return { ...m, score: result.score, voteCounts: vc }
    }))
    setUserVotes((prev) => ({ ...prev, [motionId]: result.userVote }))
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 20px' }}>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '100px 0', color: 'var(--text-muted)', fontSize: 16 }}>
              Loading...
            </div>
          ) : ranked.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '100px 0' }}>
              <p style={{ color: 'var(--text-muted)', fontSize: 18, margin: '0 0 20px' }}>
                No motions yet.
              </p>
              <Link
                to="/governance/propose"
                style={{
                  display: 'inline-flex',
                  background: 'var(--primary)',
                  color: '#fff',
                  borderRadius: 999,
                  padding: '14px 32px',
                  fontWeight: 700,
                  fontSize: 16,
                  textDecoration: 'none',
                }}
              >
                Be the first to propose
              </Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {ranked.map((motion) => {
                const uv = userVotes[motion.id] ?? null
                const scoreColor = uv === 'up' ? 'var(--vote-up)' : uv === 'down' ? 'var(--vote-down)' : 'var(--text-primary)'

                return (
                  <div
                    key={motion.id}
                    style={{
                      background: 'var(--panel)',
                      borderRadius: 16,
                      boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)',
                      overflow: 'hidden',
                      transition: 'box-shadow 0.2s, transform 0.15s',
                      cursor: 'pointer',
                    }}
                    onClick={() => navigate(`/governance/${motion.id}`)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(`/governance/${motion.id}`) }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    {/* Title row */}
                    <div style={{ padding: '20px 24px 0' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8 }}>
                        <MotionStatusBadge status={motion.status} />
                        <h3 style={{
                          margin: 0,
                          fontSize: 18,
                          fontWeight: 700,
                          color: 'var(--text-primary)',
                          lineHeight: 1.35,
                          letterSpacing: '-0.01em',
                        }}>
                          {motion.title}
                        </h3>
                      </div>
                      <p style={{
                        margin: '0 0 16px',
                        fontSize: 14,
                        lineHeight: 1.55,
                        color: 'var(--text-secondary)',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical' as const,
                        overflow: 'hidden',
                      }}>
                        {motion.body}
                      </p>
                    </div>

                    {/* Bottom bar: votes + meta */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0,
                      padding: '0 24px 16px',
                    }}>
                      {/* Vote pill — horizontal like Reddit redesign */}
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 0,
                          background: '#f6f7f8',
                          borderRadius: 999,
                          overflow: 'hidden',
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={(e) => handleVote(motion.id, 'up', e)}
                          aria-label="Upvote"
                          style={{
                            background: uv === 'up' ? 'var(--vote-up-bg)' : 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '8px 10px',
                            color: uv === 'up' ? 'var(--vote-up)' : '#878a8c',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.12s',
                            borderRadius: '999px 0 0 999px',
                          }}
                          onMouseEnter={(e) => { if (uv !== 'up') { e.currentTarget.style.background = 'var(--vote-up-hover)'; e.currentTarget.style.color = 'var(--vote-up)' } }}
                          onMouseLeave={(e) => { if (uv !== 'up') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#878a8c' } }}
                        >
                          <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3l7 7h-4v7H7v-7H3l7-7z"/></svg>
                        </button>

                        <span style={{
                          fontWeight: 800,
                          fontSize: 14,
                          color: scoreColor,
                          padding: '0 4px',
                          minWidth: 32,
                          textAlign: 'center',
                          lineHeight: 1,
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
                            padding: '8px 10px',
                            color: uv === 'down' ? 'var(--vote-down)' : '#878a8c',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.12s',
                            borderRadius: '0 999px 999px 0',
                          }}
                          onMouseEnter={(e) => { if (uv !== 'down') { e.currentTarget.style.background = 'var(--vote-down-hover)'; e.currentTarget.style.color = 'var(--vote-down)' } }}
                          onMouseLeave={(e) => { if (uv !== 'down') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#878a8c' } }}
                        >
                          <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor"><path d="M10 17l-7-7h4V3h6v7h4l-7 7z"/></svg>
                        </button>
                      </div>

                      {/* Vote breakdown */}
                      <span style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        marginLeft: 8,
                        whiteSpace: 'nowrap',
                      }}>
                        <span style={{ color: 'var(--vote-up)' }}>{motion.voteCounts.up}</span>
                        <span style={{ margin: '0 3px', opacity: 0.4 }}>/</span>
                        <span style={{ color: 'var(--vote-down)' }}>{motion.voteCounts.down}</span>
                      </span>

                      {/* Spacer */}
                      <div style={{ flex: 1 }} />

                      {/* Meta row */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        fontSize: 13,
                        color: 'var(--text-muted)',
                        fontWeight: 500,
                      }}>
                        {motion.commentCount > 0 && (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style={{ opacity: 0.5 }}>
                              <path d="M2 5a2 2 0 012-2h12a2 2 0 012 2v7a2 2 0 01-2 2H8l-4 3v-3H4a2 2 0 01-2-2V5z"/>
                            </svg>
                            {motion.commentCount}
                          </span>
                        )}
                        <span>{motion.proposerName}</span>
                        <span style={{ opacity: 0.4 }}>&middot;</span>
                        <span>{timeAgo(motion.createdAtISO)}</span>
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
