import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { getMotionById } from '../../../application/usecases/getMotionById'
import { proposeAmendment } from '../../../application/usecases/proposeAmendment'
import type { Motion } from '../../../domain/motion/Motion'
import { AmendmentDiff } from '../../components/governance/AmendmentDiff'

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
      <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
        <p className="muted">Loading...</p>
      </div>
    )
  }

  if (!parentMotion) {
    return (
      <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
        <section className="panel">
          <h1 style={{ marginTop: 0 }}>Motion not found</h1>
          <p className="muted">Cannot propose an amendment for a nonexistent motion.</p>
          <Link to="/governance">Back to Governance</Link>
        </section>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link to={`/governance/${id}`} style={{ fontSize: 14 }}>
          &larr; Back to Motion
        </Link>
      </div>

      <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 700 }}>Propose Amendment</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        Amending: <strong>{parentMotion.title}</strong>
      </p>

      {errors.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          {errors.map((err, i) => (
            <p key={i} style={{ color: '#991b1b', fontSize: 14, margin: '0 0 0.25rem' }}>{err}</p>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label className="muted" htmlFor="amend-title" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Amendment Title
            </label>
            <input
              id="amend-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ width: '100%' }}
              required
            />
          </div>

          <div>
            <label className="muted" htmlFor="amend-text" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Proposed Text
            </label>
            <textarea
              id="amend-text"
              value={proposedText}
              onChange={(e) => setProposedText(e.target.value)}
              rows={10}
              style={{ width: '100%' }}
              required
            />
          </div>

          <div>
            <h3 style={{ marginBottom: '0.5rem' }}>Preview Changes</h3>
            <AmendmentDiff originalText={parentMotion.body} proposedText={proposedText} />
          </div>

          <div>
            <button
              type="submit"
              disabled={submitting}
              style={{
                background: 'var(--primary)',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                padding: '0.5rem 1.25rem',
                cursor: submitting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                opacity: submitting ? 0.6 : 1,
              }}
            >
              {submitting ? 'Submitting...' : 'Submit Amendment'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
