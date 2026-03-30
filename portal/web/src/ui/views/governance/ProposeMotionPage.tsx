import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useServices, useAuth } from '../../../app/AppProviders'
import { proposeMotion } from '../../../application/usecases/proposeMotion'
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
    <div>
      <GovernanceNav />
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 20px 40px' }}>
        <GovernanceBreadcrumb items={[{ label: 'Motions', to: '/governance' }, { label: 'Propose Motion' }]} />

      <div style={{
        background: 'var(--panel)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-card)',
        padding: 32,
      }}>
        <h1 style={{
          fontSize: 24,
          fontWeight: 800,
          margin: '0 0 24px',
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
        }}>
          Propose a Motion
        </h1>

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
                htmlFor="motion-title"
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Title
              </label>
              <input
                id="motion-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a clear, descriptive title"
                style={inputStyle}
                required
              />
            </div>

            <div>
              <label
                htmlFor="motion-body"
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Body
              </label>
              <textarea
                id="motion-body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={10}
                placeholder="Describe the motion in detail..."
                style={{ ...inputStyle, resize: 'vertical' }}
                required
              />
            </div>

            <div>
              <label
                htmlFor="motion-quorum"
                style={{
                  display: 'block',
                  marginBottom: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                }}
              >
                Quorum Required
              </label>
              <input
                id="motion-quorum"
                type="number"
                min={1}
                value={quorumRequired}
                onChange={(e) => setQuorumRequired(Number(e.target.value))}
                style={{ ...inputStyle, width: 140 }}
              />
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
              {submitting ? 'Submitting...' : 'Submit Motion'}
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
  )
}
