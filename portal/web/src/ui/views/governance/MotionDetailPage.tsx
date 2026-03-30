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
import { DiffView, InlineDiff } from '../../components/governance/DiffView'
import { UnifiedDiff } from '../../components/governance/UnifiedDiff'
import { GovernanceNav, GovernanceBreadcrumb } from '../../components/governance/GovernanceNav'

function getGuestId(): string {
  const key = 'governance.guestId'
  let gid = localStorage.getItem(key)
  if (!gid) {
    gid = `guest_${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, gid)
  }
  return gid
}

const sectionStyle: React.CSSProperties = {
  background: 'var(--panel)',
  borderRadius: 'var(--radius-lg)',
  boxShadow: 'var(--shadow-card)',
  padding: 24,
  marginBottom: 16,
}

const sectionTitle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: 16,
  fontSize: 17,
  fontWeight: 700,
  color: 'var(--text-primary)',
  letterSpacing: '-0.01em',
}

const primaryBtn: React.CSSProperties = {
  background: 'var(--primary)',
  color: '#fff',
  border: 'none',
  borderRadius: 999,
  padding: '10px 22px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 14,
  transition: 'background 0.15s',
}

const outlinedBtn: React.CSSProperties = {
  background: 'transparent',
  color: 'var(--primary)',
  border: '1.5px solid var(--primary)',
  borderRadius: 999,
  padding: '9px 22px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 14,
  textDecoration: 'none',
  display: 'inline-flex',
  alignItems: 'center',
  transition: 'background 0.15s',
}

const destructiveBtn: React.CSSProperties = {
  background: 'var(--accent-red)',
  color: '#fff',
  border: 'none',
  borderRadius: 999,
  padding: '10px 22px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 14,
  transition: 'background 0.15s',
}

export function MotionDetailPage() {
  const { id } = useParams()
  const { motionRepository, voteRepository, engagementRepository } = useServices()
  const { user } = useAuth()
  const effectiveUserId = user?.id ?? getGuestId()
  const effectiveUserName = user?.displayName ?? 'Guest'
  const [motion, setMotion] = useState<Motion | null>(null)
  const [parentMotion, setParentMotion] = useState<Motion | null>(null)
  const [amendments, setAmendments] = useState<Motion[]>([])
  const [actionError, setActionError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [userVote, setUserVote] = useState<VoteDirection | null>(null)
  const [comments, setComments] = useState<Comment[]>([])
  const [commentBody, setCommentBody] = useState('')
  const [upCount, setUpCount] = useState(0)
  const [downCount, setDownCount] = useState(0)
  const [showUnifiedDiff, setShowUnifiedDiff] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      getMotionById(motionRepository, id),
      listMotions(motionRepository, { parentMotionId: id }),
      engagementRepository.listComments(id),
    ]).then(async ([m, amends, cmts]) => {
      setMotion(m)
      setAmendments(amends)
      setComments(cmts)
      
      // If this is an amendment, fetch the parent motion for diff view
      if (m?.parentMotionId) {
        const parent = await getMotionById(motionRepository, m.parentMotionId)
        setParentMotion(parent)
      }
      
      setLoading(false)
      if (m) document.title = `ballot-sign \u2022 ${m.title}`
    })
  }, [motionRepository, engagementRepository, id, user])

  useEffect(() => {
    if (!id) return
    engagementRepository.getUserVote(id, effectiveUserId).then(setUserVote)
    engagementRepository.getVoteCounts(id).then((vc) => { setUpCount(vc.up); setDownCount(vc.down) })
    engagementRepository.trackView(id, effectiveUserId)
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
    const vc = await engagementRepository.getVoteCounts(id)
    setUpCount(vc.up)
    setDownCount(vc.down)
  }

  async function handleDownvote() {
    if (!id) return
    const result = await engagementRepository.downvote(id, effectiveUserId)
    setUserVote(result.userVote)
    setMotion((prev) => (prev ? { ...prev, score: result.score } : prev))
    const vc = await engagementRepository.getVoteCounts(id)
    setUpCount(vc.up)
    setDownCount(vc.down)
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
      <div style={{ maxWidth: 920, margin: '0 auto', padding: '40px 20px' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading...</p>
      </div>
    )
  }

  if (!motion) {
    return (
      <div style={{ maxWidth: 920, margin: '0 auto', padding: '40px 20px' }}>
        <div style={sectionStyle}>
          <h1 style={{ ...sectionTitle, fontSize: 22 }}>Motion not found</h1>
          <p style={{ color: 'var(--text-muted)', margin: '0 0 16px' }}>Check the URL or return to governance.</p>
          <Link to="/governance" style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>Back to Governance</Link>
        </div>
      </div>
    )
  }

  const avatarColor = (name: string) => {
    const colors = ['var(--accent-blue)', 'var(--accent-purple)', 'var(--accent-teal)', 'var(--accent-green)', 'var(--accent-amber)', 'var(--accent-red)']
    let hash = 0
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
    return colors[Math.abs(hash) % colors.length]
  }

  return (
    <div>
      <GovernanceNav />
      <div style={{ maxWidth: 920, margin: '0 auto', padding: '24px 20px 40px' }}>
        {/* Breadcrumb */}
        <GovernanceBreadcrumb 
          items={[
            { label: motion?.type === 'amendment' ? 'Amendments' : 'Motions', to: '/governance' },
            { label: motion?.title || 'Motion' },
          ]} 
        />

      {/* Header card */}
      <section style={sectionStyle}>
        <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
          {/* Vote widget — Reddit style */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              minWidth: 56,
              flexShrink: 0,
              background: 'var(--panel-2)',
              borderRadius: 14,
              padding: '8px 6px',
            }}
          >
            <button
              type="button"
              onClick={handleUpvote}
              aria-label="Upvote"
              style={{
                background: userVote === 'up' ? 'var(--vote-up-bg)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                lineHeight: 1,
                padding: 8,
                borderRadius: 10,
                color: userVote === 'up' ? 'var(--vote-up)' : 'var(--vote-neutral)',
                minWidth: 44,
                minHeight: 44,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { if (userVote !== 'up') e.currentTarget.style.background = 'var(--vote-neutral-hover)' }}
              onMouseLeave={(e) => { if (userVote !== 'up') e.currentTarget.style.background = 'transparent' }}
            >
              <svg width="24" height="24" viewBox="0 0 20 20" fill="currentColor"><path d="M10 3l7 7h-4v7H7v-7H3l7-7z"/></svg>
            </button>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 0' }}>
              <span style={{
                fontWeight: 800,
                fontSize: 18,
                lineHeight: 1,
                color: userVote === 'up' ? 'var(--vote-up)' : userVote === 'down' ? 'var(--vote-down)' : 'var(--text-primary)',
              }}>
                {motion.score}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, whiteSpace: 'nowrap' }}>
                {upCount}&#8593; {downCount}&#8595;
              </span>
            </div>
            <button
              type="button"
              onClick={handleDownvote}
              aria-label="Downvote"
              style={{
                background: userVote === 'down' ? 'var(--vote-down-bg)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                lineHeight: 1,
                padding: 8,
                borderRadius: 10,
                color: userVote === 'down' ? 'var(--vote-down)' : 'var(--vote-neutral)',
                minWidth: 44,
                minHeight: 44,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { if (userVote !== 'down') e.currentTarget.style.background = 'var(--vote-neutral-hover)' }}
              onMouseLeave={(e) => { if (userVote !== 'down') e.currentTarget.style.background = 'transparent' }}
            >
              <svg width="24" height="24" viewBox="0 0 20 20" fill="currentColor"><path d="M10 17l-7-7h4V3h6v7h4l-7 7z"/></svg>
            </button>
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
              <h1 style={{
                fontSize: 24,
                fontWeight: 800,
                margin: 0,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}>
                {motion.title}
              </h1>
              <MotionStatusBadge status={motion.status} />
            </div>
          </div>
        </div>
        <MotionTimeline status={motion.status} />
      </section>

      {/* Amendment diff (if this is an amendment) */}
      {motion.parentMotionId && parentMotion && (
        <section style={sectionStyle}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 12, 
            marginBottom: 16,
            flexWrap: 'wrap',
          }}>
            <h2 style={{ ...sectionTitle, margin: 0 }}>Proposed Changes</h2>
            <span style={{
              fontSize: 12,
              color: 'var(--text-muted)',
              backgroundColor: 'var(--panel-2)',
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
            }}>
              Amendment to{' '}
              <Link 
                to={`/governance/${parentMotion.id}`}
                style={{ color: 'var(--primary)', textDecoration: 'none' }}
              >
                {parentMotion.title}
              </Link>
            </span>
          </div>
          <DiffView 
            original={parentMotion.body} 
            proposed={motion.proposedBodyDiff || motion.body}
            showUnchanged={false}
          />
        </section>
      )}

      {/* Motion text */}
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>
          {motion.parentMotionId ? 'Amendment Text' : 'Motion Text'}
        </h2>
        <p style={{
          whiteSpace: 'pre-wrap',
          margin: 0,
          fontSize: 15,
          lineHeight: 1.7,
          color: 'var(--text-primary)',
        }}>
          {motion.body}
        </p>
      </section>

      {/* Details */}
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>Details</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14, color: 'var(--text-secondary)' }}>
          <span>
            Proposed by <strong style={{ color: 'var(--text-primary)' }}>{motion.proposerName}</strong> on {motion.createdAtISO.slice(0, 10)}
          </span>
          {motion.seconderName ? (
            <span>
              Seconded by <strong style={{ color: 'var(--text-primary)' }}>{motion.seconderName}</strong>
            </span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>Not yet seconded</span>
          )}
          <span>
            Quorum required: <strong style={{ color: 'var(--text-primary)' }}>{motion.quorumRequired}</strong>
          </span>
        </div>
      </section>

      {/* Actions */}
      {user && (
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>Actions</h2>

          {actionError && (
            <div style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'var(--accent-red-bg)',
              color: 'var(--accent-red)',
              fontSize: 14,
              fontWeight: 500,
              marginBottom: 16,
            }}>
              {actionError}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {motion.status === 'proposed' && motion.proposerId !== user.id && (
              <button type="button" onClick={handleSecond} style={primaryBtn}>
                Second this Motion
              </button>
            )}

            {motion.status === 'proposed' && motion.proposerId === user.id && (
              <button type="button" onClick={handleWithdraw} style={destructiveBtn}>
                Withdraw
              </button>
            )}

            {motion.status === 'discussion' && (
              <>
                <button type="button" onClick={handleOpenVoting} style={primaryBtn}>
                  Open Voting
                </button>
                <button
                  type="button"
                  onClick={handleTable}
                  style={{
                    background: 'var(--surface)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: 999,
                    padding: '10px 22px',
                    cursor: 'pointer',
                    fontWeight: 700,
                    fontSize: 14,
                    transition: 'background 0.15s',
                  }}
                >
                  Table
                </button>
                <Link to={`/governance/${motion.id}/amend`} style={outlinedBtn}>
                  Propose Amendment
                </Link>
              </>
            )}
          </div>

          {motion.status === 'voting' && (
            <div style={{ marginTop: 20 }}>
              <VotingPanel motion={motion} currentUserId={user.id} onVote={handleVote} />
            </div>
          )}
        </section>
      )}

      {/* Vote result */}
      {motion.result && motion.status !== 'voting' && (
        <section style={sectionStyle}>
          <h2 style={sectionTitle}>Vote Result</h2>
          <div
            style={{
              padding: '14px 20px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: motion.result.passed ? 'var(--accent-green-bg)' : 'var(--accent-red-bg)',
              color: motion.result.passed ? 'var(--accent-green)' : 'var(--accent-red)',
              fontWeight: 700,
              fontSize: 15,
              marginBottom: 16,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span style={{ fontSize: 20 }}>{motion.result.passed ? '\u2713' : '\u2717'}</span>
            {motion.result.passed ? 'Passed' : 'Failed'}
            {motion.result.quorumMet ? '' : ' (quorum not met)'}
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', display: 'flex', gap: 16 }}>
            <span>
              Yea: <strong style={{ color: 'var(--accent-green)' }}>{motion.result.yea}</strong>
            </span>
            <span>
              Nay: <strong style={{ color: 'var(--accent-red)' }}>{motion.result.nay}</strong>
            </span>
            <span>
              Abstain: <strong style={{ color: 'var(--text-muted)' }}>{motion.result.abstain}</strong>
            </span>
          </div>
        </section>
      )}

      {/* Amendments */}
      {amendments.length > 0 && (
        <section style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
            <h2 style={{ ...sectionTitle, margin: 0 }}>Proposed Amendments</h2>
            
            {/* Unified diff toggle */}
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 13,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '6px 12px',
              backgroundColor: showUnifiedDiff ? 'var(--primary-bg)' : 'var(--panel-2)',
              borderRadius: 'var(--radius-md)',
              border: `1px solid ${showUnifiedDiff ? 'var(--primary)' : 'var(--border-subtle)'}`,
              transition: 'all 0.15s',
            }}>
              <input
                type="checkbox"
                checked={showUnifiedDiff}
                onChange={(e) => setShowUnifiedDiff(e.target.checked)}
                style={{ margin: 0 }}
              />
              <span>Show unified diff</span>
            </label>
          </div>
          
          {/* Unified diff view */}
          {showUnifiedDiff && (
            <div style={{ marginBottom: 24 }}>
              <UnifiedDiff
                original={motion.body}
                amendments={amendments.map(a => ({
                  id: a.id,
                  title: a.title,
                  body: a.body,
                  proposedBodyDiff: a.proposedBodyDiff,
                  proposerName: a.proposerName,
                  status: a.status,
                }))}
                showUnchanged={false}
              />
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {amendments.map((a) => (
              <div
                key={a.id}
                style={{
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--panel-2)',
                  overflow: 'hidden',
                }}
              >
                {/* Amendment header */}
                <div style={{
                  padding: '16px 20px',
                  borderBottom: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--panel)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                    <MotionStatusBadge status={a.status} />
                    <span style={{ 
                      fontWeight: 700, 
                      fontSize: 16, 
                      color: 'var(--text-primary)',
                    }}>
                      {a.title}
                    </span>
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 16,
                    fontSize: 13,
                    color: 'var(--text-secondary)',
                  }}>
                    <span>
                      Proposed by <strong style={{ color: 'var(--text-primary)' }}>{a.proposerName}</strong>
                    </span>
                    <InlineDiff 
                      original={motion.body} 
                      proposed={a.proposedBodyDiff || a.body} 
                    />
                  </div>
                </div>
                
                {/* Diff view */}
                <div style={{ padding: 20 }}>
                  <div style={{ 
                    fontSize: 12, 
                    fontWeight: 600, 
                    color: 'var(--text-muted)',
                    marginBottom: 12,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}>
                    Proposed Changes
                  </div>
                  <DiffView 
                    original={motion.body} 
                    proposed={a.proposedBodyDiff || a.body}
                    showUnchanged={false}
                  />
                </div>
                
                {/* Action link */}
                <div style={{
                  padding: '12px 20px',
                  borderTop: '1px solid var(--border-subtle)',
                  backgroundColor: 'var(--panel)',
                }}>
                  <Link
                    to={`/governance/${a.id}`}
                    style={{
                      color: 'var(--primary)',
                      textDecoration: 'none',
                      fontWeight: 600,
                      fontSize: 14,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                    }}
                  >
                    View full amendment 
                    <span style={{ fontSize: 18 }}>&rarr;</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Discussion */}
      <section style={sectionStyle}>
        <h2 style={sectionTitle}>
          Discussion
          <span style={{
            marginLeft: 8,
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text-muted)',
          }}>
            ({comments.length})
          </span>
        </h2>

        {comments.length === 0 && (
          <p style={{
            color: 'var(--text-muted)',
            fontSize: 14,
            margin: '0 0 16px',
            padding: '20px 0',
            textAlign: 'center',
          }}>
            No comments yet. Be the first to discuss this motion.
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {comments.map((c) => (
            <div
              key={c.id}
              style={{
                padding: 16,
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--panel-2)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
                {/* Avatar placeholder */}
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  backgroundColor: avatarColor(c.authorName),
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <span style={{ color: '#fff', fontWeight: 700, fontSize: 13, lineHeight: 1 }}>
                    {c.authorName.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>
                    {c.authorName}
                  </span>
                  <span style={{
                    fontSize: 12,
                    color: 'var(--text-muted)',
                    marginLeft: 8,
                  }}>
                    {new Date(c.createdAtISO).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <p style={{
                margin: 0,
                fontSize: 14,
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                color: 'var(--text-primary)',
              }}>
                {c.body}
              </p>
            </div>
          ))}
        </div>

        {/* Comment input */}
        <div style={{ marginTop: 20 }}>
          {!user && (
            <div style={{
              fontSize: 12,
              color: 'var(--text-muted)',
              marginBottom: 8,
              fontWeight: 500,
            }}>
              Commenting as Guest
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            <textarea
              placeholder={user ? 'Add a comment...' : 'Add a comment as Guest...'}
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleAddComment()
                }
              }}
              rows={3}
              style={{
                flex: 1,
                padding: '12px 16px',
                fontSize: 14,
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--panel)',
                color: 'var(--text-primary)',
                outline: 'none',
                resize: 'vertical',
                fontFamily: 'inherit',
                boxSizing: 'border-box',
                transition: 'border-color 0.15s',
              }}
            />
            <button
              type="button"
              onClick={handleAddComment}
              disabled={!commentBody.trim()}
              style={{
                background: commentBody.trim() ? 'var(--primary)' : 'var(--surface)',
                color: commentBody.trim() ? '#fff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 999,
                padding: '12px 24px',
                cursor: commentBody.trim() ? 'pointer' : 'default',
                fontWeight: 700,
                fontSize: 14,
                transition: 'all 0.15s',
                whiteSpace: 'nowrap',
                alignSelf: 'flex-end',
              }}
            >
              Comment
            </button>
          </div>
        </div>
      </section>
      </div>
    </div>
  )
}
