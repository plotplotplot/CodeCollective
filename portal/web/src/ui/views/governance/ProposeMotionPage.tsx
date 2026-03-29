import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { proposeMotion } from '../../../application/usecases/proposeMotion'

export function ProposeMotionPage() {
  const { motionRepository } = useServices()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [quorumRequired, setQuorumRequired] = useState(5)
  const [errors, setErrors] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    document.title = 'ballot-sign \u2022 Propose Motion'
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!user) {
      setErrors(['You must be logged in to propose a motion.'])
      return
    }
    setErrors([])
    setSubmitting(true)
    const res = await proposeMotion(motionRepository, {
      title,
      body,
      proposerId: user.id,
      proposerName: user.displayName,
      quorumRequired,
    })
    setSubmitting(false)
    if (res.ok) {
      navigate(`/governance/${res.motion.id}`)
    } else {
      setErrors(res.errors)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/governance" style={{ fontSize: 14 }}>
          &larr; Back to Governance
        </Link>
      </div>

      <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 700 }}>Propose a Motion</h1>

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
            <label className="muted" htmlFor="motion-title" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Title
            </label>
            <input
              id="motion-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ width: '100%' }}
              required
            />
          </div>

          <div>
            <label className="muted" htmlFor="motion-body" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Body
            </label>
            <textarea
              id="motion-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
              style={{ width: '100%' }}
              required
            />
          </div>

          <div>
            <label className="muted" htmlFor="motion-quorum" style={{ display: 'block', marginBottom: '0.25rem' }}>
              Quorum Required
            </label>
            <input
              id="motion-quorum"
              type="number"
              min={1}
              value={quorumRequired}
              onChange={(e) => setQuorumRequired(Number(e.target.value))}
              style={{ width: 120 }}
            />
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
              {submitting ? 'Submitting...' : 'Submit Motion'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
