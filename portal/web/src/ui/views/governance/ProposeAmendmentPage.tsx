import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { getMotionById } from '../../../application/usecases/getMotionById'
import { proposeAmendment } from '../../../application/usecases/proposeAmendment'
import type { Motion } from '../../../domain/motion/Motion'
import { AmendmentDiff } from '../../components/governance/AmendmentDiff'
import { GovernanceNav, GovernanceBreadcrumb } from '../../components/governance/GovernanceNav'

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 16px',
  fontSize: 14,
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-md)',
  backgroundColor: 'var(--panel)',
  color: 'var(--text-primary)',
  outline: 'none',
  transition: 'border-color 0.15s',
  boxSizing: 'border-box',
  fontFamily: 'inherit',
}

export function ProposeAmendmentPage() {
  const { id } = useParams()
  const { motionRepository } = useServices()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [parentMotion, setParentMotion] = useState<Motion | null>(null)
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [proposedText, setProposedText] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    document.title = 'ballot-sign \u2022 Propose Amendment'
  }, [])

  useEffect(() => {
    if (!id) return
    getMotionById(motionRepository, id).then((m) => {
      setParentMotion(m)
      if (m) setProposedText(m.body)
      setLoading(false)
    })
  }, [motionRepository, id])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!user || !id || !parentMotion) {
      setErrors(['Unable to submit. Please ensure you are logged in.'])
      return
    }
    setErrors([])
    setSubmitting(true)
    const res = await proposeAmendment(motionRepository, {
      parentMotionId: id,
      title,
      body: proposedText,
      proposedBodyDiff: proposedText,
      proposerId: user.id,
      proposerName: user.displayName,
      quorumRequired: parentMotion.quorumRequired,
    })
    setSubmitting(false)
    if (res.ok) {
      navigate(`/governance/${res.motion.id}`)
    } else {
      setErrors(res.errors)
    }
  }

  if (loading) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading...</p>
      </div>
    )
  }

  if (!parentMotion) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px' }}>
        <div style={{
          background: 'var(--panel)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
          padding: 32,
        }}>
          <h1 style={{ marginTop: 0, color: 'var(--text-primary)' }}>Motion not found</h1>
          <p style={{ color: 'var(--text-muted)' }}>Cannot propose an amendment for a nonexistent motion.</p>
          <Link to="/governance" style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>Back to Governance</Link>
        </div>
      </div>
    )
  }

  return (
    <div>
      <GovernanceNav />
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px 40px' }}>
        <GovernanceBreadcrumb 
          items={[
            { label: 'Motions', to: '/governance' },
            { label: parentMotion?.title || 'Motion', to: `/governance/${id}` },
            { label: 'Propose Amendment' },
          ]} 
        />

      <div style={{
        background: 'var(--panel)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-card)',
        padding: 32,
      }}>
        <h1 style={{
          fontSize: 24,
          fontWeight: 800,
          margin: '0 0 8px',
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
        }}>
          Propose Amendment
        </h1>
        <p style={{
          margin: '0 0 24px',
          fontSize: 14,
          color: 'var(--text-muted)',
        }}>
          Amending: <strong style={{ color: 'var(--text-primary)' }}>{parentMotion.title}</strong>
        </p>

        {errors.length > 0 && (
          <div style={{
            marginBottom: 20,
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--accent-red-bg)',
            border: '1px solid var(--accent-red)',
          }}>
            {errors.map((err, i) => (
              <p key={i} style={{ color: 'var(--accent-red)', fontSize: 14, margin: i > 0 ? '4px 0 0' : 0, fontWeight: 500 }}>{err}</p>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div>
              <label
                htmlFor="amend-title"
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Amendment Title
              </label>
              <input
                id="amend-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Describe the amendment"
                style={inputStyle}
                required
              />
            </div>

            <div>
              <label
                htmlFor="amend-text"
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Proposed Text
              </label>
              <textarea
                id="amend-text"
                value={proposedText}
                onChange={(e) => setProposedText(e.target.value)}
                rows={10}
                placeholder="Edit the motion text..."
                style={{ ...inputStyle, resize: 'vertical' }}
                required
              />
            </div>

            <div>
              <h3 style={{
                margin: '0 0 12px',
                fontSize: 15,
                fontWeight: 700,
                color: 'var(--text-primary)',
              }}>
                Preview Changes
              </h3>
              <AmendmentDiff originalText={parentMotion.body} proposedText={proposedText} />
            </div>

            <button
              type="submit"
              disabled={submitting}
              style={{
                width: '100%',
                background: 'var(--primary)',
                color: '#fff',
                border: 'none',
                borderRadius: 999,
                padding: '14px 24px',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontWeight: 700,
                fontSize: 15,
                opacity: submitting ? 0.6 : 1,
                transition: 'opacity 0.15s, background 0.15s',
                marginTop: 4,
              }}
            >
              {submitting ? 'Submitting...' : 'Submit Amendment'}
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
  )
}
