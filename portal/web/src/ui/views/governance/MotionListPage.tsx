import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useServices } from '../../../app/AppProviders'
import { listMotions } from '../../../application/usecases/listMotions'
import type { Motion, MotionStatus } from '../../../domain/motion/Motion'
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

export function MotionListPage() {
  const { motionRepository } = useServices()
  const navigate = useNavigate()
  const [motions, setMotions] = useState<Motion[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<MotionStatus | null>(null)

  useEffect(() => {
    document.title = 'ballot-sign \u2022 Governance'
  }, [])

  useEffect(() => {
    const query: MotionListQuery = {}
    if (search) query.search = search
    if (statusFilter) query.status = [statusFilter]
    listMotions(motionRepository, query).then(setMotions)
  }, [motionRepository, search, statusFilter])

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

      <input
        type="text"
        placeholder="Search motions..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ width: '100%', marginBottom: '1rem' }}
      />

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

      {motions.length === 0 ? (
        <p className="muted">No motions found.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {motions.map((motion) => (
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
              }}
            >
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
          ))}
        </div>
      )}
    </div>
  )
}
