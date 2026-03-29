import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { getMotionById } from '../../../application/usecases/getMotionById'
import { secondMotion } from '../../../application/usecases/secondMotion'
import { castVote } from '../../../application/usecases/castVote'
import { tableMotion } from '../../../application/usecases/tableMotion'
import { withdrawMotion } from '../../../application/usecases/withdrawMotion'
import { listMotions } from '../../../application/usecases/listMotions'
import type { Motion, VoteChoice, VoteDirection, Comment } from '../../../domain/motion/Motion'
import { MotionStatusBadge } from '../../components/governance/MotionStatusBadge'
import { MotionTimeline } from '../../components/governance/MotionTimeline'
import { VotingPanel } from '../../components/governance/VotingPanel'

function getGuestId(): string {
  const key = 'governance.guestId'
  let gid = localStorage.getItem(key)
  if (!gid) {
    gid = `guest_${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, gid)
  }
  return gid
}

export function MotionDetailPage() {
  const { id } = useParams()
  const { motionRepository, voteRepository, engagementRepository } = useServices()
  const { user } = useAuth()
  const effectiveUserId = user?.id ?? getGuestId()
  const effectiveUserName = user?.displayName ?? 'Guest'
  const [motion, setMotion] = useState<Motion | null>(null)
  const [amendments, setAmendments] = useState<Motion[]>([])
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [userVote, setUserVote] = useState<VoteDirection | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [commentBody, setCommentBody] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      getMotionById(motionRepository, id),
      listMotions(motionRepository, { parentMotionId: id }),
      engagementRepository.listComments(id),
    ]).then(([m, amends, cmts]) => {
      setMotion(m)
      setAmendments(amends)
      setComments(cmts)
      setLoading(false)
      if (m) document.title = `ballot-sign \u2022 ${m.title}`
    })
  }, [motionRepository, engagementRepository, id])

  useEffect(() => {
    if (!id) return
    engagementRepository.getUserVote(id, effectiveUserId).then(setUserVote)
  }, [engagementRepository, id, effectiveUserId])

  async function refreshMotion() {
    if (!id) return
    const [m, amends] = await Promise.all([
      getMotionById(motionRepository, id),
      listMotions(motionRepository, { parentMotionId: id }),
    ])
    setMotion(m)
    setAmendments(amends)
  }

  async function handleSecond() {
    if (!id || !user) return
    setActionError(null)
    const res = await secondMotion(motionRepository, id, user.id, user.displayName)
    if (res.ok) setMotion(res.motion)
    else setActionError(res.errors.join(', '))
  }

  async function handleVote(choice: VoteChoice) {
    if (!id || !user) return
    setActionError(null)
    const res = await castVote(voteRepository, motionRepository, id, user.id, user.displayName, choice)
    if (res.ok) await refreshMotion()
    else setActionError(res.errors.join(', '))
  }

  async function handleTable() {
    if (!id) return
    setActionError(null)
    const res = await tableMotion(motionRepository, id)
    if (res.ok) setMotion(res.motion)
    else setActionError(res.errors.join(', '))
  }

  async function handleWithdraw() {
    if (!id || !user) return
    setActionError(null)
    const res = await withdrawMotion(motionRepository, id, user.id)
    if (res.ok) setMotion(res.motion)
    else setActionError(res.errors.join(', '))
  }

  async function handleOpenVoting() {
    if (!id) return
    setActionError(null)
    try {
      const updated = await motionRepository.openVoting(id)
      setMotion(updated)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to open voting')
    }
  }

  async function handleUpvote() {
    if (!id) return
    const result = await engagementRepository.upvote(id, effectiveUserId)
    setUserVote(result.userVote)
    setMotion((prev) => (prev ? { ...prev, score: result.score } : prev))
  }

  async function handleDownvote() {
    if (!id) return
    const result = await engagementRepository.downvote(id, effectiveUserId)
    setUserVote(result.userVote)
    setMotion((prev) => (prev ? { ...prev, score: result.score } : prev))
  }

  async function handleAddComment() {
    if (!id || !commentBody.trim()) return
    await engagementRepository.addComment({
      motionId: id,
      authorId: effectiveUserId,
      authorName: effectiveUserName,
      body: commentBody.trim(),
    })
    setCommentBody('')
    const cmts = await engagementRepository.listComments(id)
    setComments(cmts)
  }

  if (loading) {
    return (
      <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
        <p className="muted">Loading...</p>
      </div>
    )
  }

  if (!motion) {
    return (
      <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
        <section className="panel">
          <h1 style={{ marginTop: 0 }}>Motion not found</h1>
          <p className="muted">Check the URL or return to governance.</p>
          <Link to="/governance">Back to Governance</Link>
        </section>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/governance" style={{ fontSize: 14 }}>
          &larr; Back to Governance
        </Link>
      </div>

      {/* Header */}
      <section
        style={{
          background: 'var(--panel)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: '1.5rem',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          {/* Vote widget */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              minWidth: 36,
              flexShrink: 0,
              gap: 2,
            }}
          >
            <button
              type="button"
              onClick={handleUpvote}
              aria-label="Upvote"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 20,
                lineHeight: 1,
                padding: 2,
                color: userVote === 'up' ? 'var(--primary)' : 'var(--text-muted, #999)',
                fontWeight: userVote === 'up' ? 700 : 400,
              }}
            >
              ▲
            </button>
            <span style={{ fontWeight: 700, fontSize: 16, lineHeight: 1 }}>{motion.score}</span>
            <button
              type="button"
              onClick={handleDownvote}
              aria-label="Downvote"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 20,
                lineHeight: 1,
                padding: 2,
                color: userVote === 'down' ? '#991b1b' : 'var(--text-muted, #999)',
                fontWeight: userVote === 'down' ? 700 : 400,
              }}
            >
              ▼
            </button>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 700, margin: 0 }}>{motion.title}</h1>
              <MotionStatusBadge status={motion.status} />
            </div>
          </div>
        </div>
        <MotionTimeline status={motion.status} />
      </section>

      {/* Motion text */}
      <section
        style={{
          background: 'var(--panel)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: '1.5rem',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ marginTop: 0 }}>Motion Text</h2>
        <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{motion.body}</p>
      </section>

      {/* Proposer / Seconder info */}
      <section
        style={{
          background: 'var(--panel)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: '1.5rem',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ marginTop: 0 }}>Details</h2>
        <div className="muted" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: 14 }}>
          <span>Proposed by <strong>{motion.proposerName}</strong> on {motion.createdAtISO.slice(0, 10)}</span>
          {motion.seconderName ? (
            <span>Seconded by <strong>{motion.seconderName}</strong></span>
          ) : (
            <span>Not yet seconded</span>
          )}
          <span>Quorum required: {motion.quorumRequired}</span>
        </div>
      </section>

      {/* Action buttons */}
      {user && (
        <section
          style={{
            background: 'var(--panel)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: '1.5rem',
            marginBottom: '1rem',
          }}
        >
          <h2 style={{ marginTop: 0 }}>Actions</h2>

          {actionError && (
            <p style={{ color: '#991b1b', fontSize: 14, margin: '0 0 0.75rem' }}>{actionError}</p>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            {motion.status === 'proposed' && motion.proposerId !== user.id && (
              <button
                type="button"
                onClick={handleSecond}
                style={{
                  background: 'var(--primary)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  padding: '0.5rem 1.25rem',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Second this Motion
              </button>
            )}

            {motion.status === 'proposed' && motion.proposerId === user.id && (
              <button
                type="button"
                onClick={handleWithdraw}
                style={{
                  background: '#991b1b',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  padding: '0.5rem 1.25rem',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Withdraw
              </button>
            )}

            {motion.status === 'discussion' && (
              <>
                <button
                  type="button"
                  onClick={handleOpenVoting}
                  style={{
                    background: 'var(--primary)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    padding: '0.5rem 1.25rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Open Voting
                </button>
                <button
                  type="button"
                  onClick={handleTable}
                  style={{
                    background: '#6b7280',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    padding: '0.5rem 1.25rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Table
                </button>
                <Link
                  to={`/governance/${motion.id}/amend`}
                  style={{
                    background: 'transparent',
                    color: 'var(--primary)',
                    border: '1px solid var(--primary)',
                    borderRadius: 8,
                    padding: '0.5rem 1.25rem',
                    textDecoration: 'none',
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  Propose Amendment
                </Link>
              </>
            )}
          </div>

          {motion.status === 'voting' && (
            <div style={{ marginTop: '1rem' }}>
              <VotingPanel motion={motion} currentUserId={user.id} onVote={handleVote} />
            </div>
          )}
        </section>
      )}

      {/* Vote result (when motion has a result) */}
      {motion.result && motion.status !== 'voting' && (
        <section
          style={{
            background: 'var(--panel)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: '1.5rem',
            marginBottom: '1rem',
          }}
        >
          <h2 style={{ marginTop: 0 }}>Vote Result</h2>
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 8,
              backgroundColor: motion.result.passed ? '#dcfce7' : '#fee2e2',
              color: motion.result.passed ? '#166534' : '#991b1b',
              fontWeight: 600,
              fontSize: 14,
              marginBottom: 12,
              display: 'inline-block',
            }}
          >
            {motion.result.passed ? 'Passed' : 'Failed'}
            {motion.result.quorumMet ? '' : ' (quorum not met)'}
          </div>
          <div className="muted" style={{ fontSize: 14 }}>
            Yea: {motion.result.yea} / Nay: {motion.result.nay} / Abstain: {motion.result.abstain}
          </div>
        </section>
      )}

      {/* Amendments */}
      {amendments.length > 0 && (
        <section
          style={{
            background: 'var(--panel)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: '1.5rem',
            marginBottom: '1rem',
          }}
        >
          <h2 style={{ marginTop: 0 }}>Amendments</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {amendments.map((a) => (
              <Link
                key={a.id}
                to={`/governance/${a.id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  borderRadius: 8,
                  border: '1px solid var(--border-subtle)',
                  textDecoration: 'none',
                  color: 'inherit',
                }}
              >
                <MotionStatusBadge status={a.status} />
                <span style={{ fontWeight: 500 }}>{a.title}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Comments / Discussion */}
      <section
        style={{
          background: 'var(--panel)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: '1.5rem',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ marginTop: 0 }}>Discussion ({comments.length})</h2>

        {comments.length === 0 && (
          <p className="muted" style={{ fontSize: 14 }}>No comments yet. Be the first to discuss this motion.</p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {comments.map((c) => (
            <div
              key={c.id}
              style={{
                padding: '0.75rem',
                borderRadius: 8,
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'baseline', marginBottom: '0.35rem' }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{c.authorName}</span>
                <span className="muted" style={{ fontSize: 12 }}>{new Date(c.createdAtISO).toLocaleDateString()}</span>
              </div>
              <p style={{ margin: 0, fontSize: 14, whiteSpace: 'pre-wrap' }}>{c.body}</p>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            placeholder={user ? 'Add a comment...' : 'Add a comment as Guest...'}
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleAddComment()
            }}
            style={{ flex: 1 }}
          />
          <button
            type="button"
            onClick={handleAddComment}
            disabled={!commentBody.trim()}
            style={{
              background: 'var(--primary)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '0.5rem 1.25rem',
              cursor: commentBody.trim() ? 'pointer' : 'default',
              fontWeight: 600,
              fontSize: 14,
              opacity: commentBody.trim() ? 1 : 0.5,
            }}
          >
            Add Comment
          </button>
        </div>
      </section>
    </div>
  )
}
