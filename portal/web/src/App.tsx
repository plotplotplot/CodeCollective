import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth, useServices } from './app/AppProviders'
import { Header } from './ui/shell/Header'
import { Footer } from './ui/shell/Footer'
import { listMotions } from './application/usecases/listMotions'
import { MotionStatusBadge } from './ui/components/governance/MotionStatusBadge'
import type { Motion } from './domain/motion/Motion'

export default function App() {
  const { user } = useAuth()
  const { motionRepository } = useServices()
  const [recentMotions, setRecentMotions] = useState<Motion[]>([])
  const [activeCount, setActiveCount] = useState(0)
  const [passedCount, setPassedCount] = useState(0)

  useEffect(() => {
    document.title = 'Code Collective Portal'
    listMotions(motionRepository).then((motions) => {
      setRecentMotions(motions.slice(0, 5))
      setActiveCount(motions.filter((m) => !['passed', 'failed', 'withdrawn'].includes(m.status)).length)
      setPassedCount(motions.filter((m) => m.status === 'passed').length)
    })
  }, [motionRepository])

  const greeting = user?.displayName ? `, ${user.displayName}` : ''

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">

          {/* Hero */}
          <section style={{
            background: 'var(--panel)',
            borderRadius: 20,
            padding: '48px 40px',
            boxShadow: 'var(--shadow-card)',
            marginBottom: 32,
          }}>
            <div style={{ maxWidth: 640 }}>
              <span style={{
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: 999,
                background: 'var(--accent-green-bg)',
                color: 'var(--accent-green)',
                fontSize: 12,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: 16,
              }}>
                Open governance
              </span>
              <h1 style={{
                fontSize: 'clamp(1.8rem, 4vw, 2.6rem)',
                fontWeight: 800,
                margin: '0 0 12px',
                color: 'var(--text-primary)',
                letterSpacing: '-0.03em',
                lineHeight: 1.15,
              }}>
                Welcome{greeting}
              </h1>
              <p style={{
                fontSize: 17,
                lineHeight: 1.6,
                color: 'var(--text-secondary)',
                margin: '0 0 28px',
                maxWidth: 520,
              }}>
                Propose motions, vote on community decisions, and shape the direction of Code Collective through transparent Robert&apos;s Rules governance.
              </p>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <Link
                  to="/governance"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'var(--primary)',
                    color: '#fff',
                    borderRadius: 999,
                    padding: '12px 28px',
                    fontWeight: 700,
                    fontSize: 15,
                    textDecoration: 'none',
                    transition: 'background 0.15s',
                  }}
                >
                  View motions
                  <span style={{ fontSize: 18 }}>&rarr;</span>
                </Link>
                <Link
                  to="/governance/propose"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'transparent',
                    color: 'var(--primary)',
                    border: '1.5px solid var(--primary)',
                    borderRadius: 999,
                    padding: '11px 28px',
                    fontWeight: 700,
                    fontSize: 15,
                    textDecoration: 'none',
                    transition: 'all 0.15s',
                  }}
                >
                  Propose a motion
                </Link>
                <Link
                  to="/constituent/dashboard"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    border: '1.5px solid var(--border)',
                    borderRadius: 999,
                    padding: '11px 28px',
                    fontWeight: 600,
                    fontSize: 15,
                    textDecoration: 'none',
                    transition: 'all 0.15s',
                  }}
                >
                  Browse initiatives
                </Link>
              </div>
            </div>
          </section>

          {/* Stats row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 16,
            marginBottom: 32,
          }}>
            {[
              { label: 'Active motions', value: activeCount, color: 'var(--accent-blue)' },
              { label: 'Passed', value: passedCount, color: 'var(--accent-green)' },
              { label: 'Total motions', value: recentMotions.length > 0 ? activeCount + passedCount + recentMotions.filter((m) => ['failed', 'withdrawn'].includes(m.status)).length : 0, color: 'var(--text-primary)' },
            ].map((stat) => (
              <div
                key={stat.label}
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-card)',
                  padding: '24px 20px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 32, fontWeight: 800, color: stat.color, letterSpacing: '-0.02em' }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: 4 }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          {/* Recent motions */}
          <section style={{ marginBottom: 32 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}>
              <h2 style={{
                fontSize: 20,
                fontWeight: 800,
                margin: 0,
                color: 'var(--text-primary)',
                letterSpacing: '-0.01em',
              }}>
                Recent motions
              </h2>
              <Link
                to="/governance"
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--accent-blue)',
                  textDecoration: 'none',
                }}
              >
                View all &rarr;
              </Link>
            </div>

            {recentMotions.length === 0 ? (
              <div style={{
                background: 'var(--panel)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-card)',
                padding: 40,
                textAlign: 'center',
                color: 'var(--text-muted)',
              }}>
                <p style={{ margin: '0 0 16px', fontSize: 15 }}>No motions yet. Be the first to propose one.</p>
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
                  Propose a motion
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {recentMotions.map((motion) => (
                  <Link
                    key={motion.id}
                    to={`/governance/${motion.id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 16,
                      background: 'var(--panel)',
                      borderRadius: 'var(--radius-md)',
                      boxShadow: 'var(--shadow-section)',
                      padding: '16px 20px',
                      textDecoration: 'none',
                      color: 'inherit',
                      transition: 'box-shadow 0.15s, transform 0.15s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'var(--shadow-section)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    {/* Score */}
                    <div style={{
                      minWidth: 40,
                      textAlign: 'center',
                      fontWeight: 800,
                      fontSize: 16,
                      color: motion.score > 0 ? 'var(--vote-up)' : motion.score < 0 ? 'var(--vote-down)' : 'var(--text-muted)',
                    }}>
                      {motion.score > 0 ? `+${motion.score}` : motion.score}
                    </div>
                    <MotionStatusBadge status={motion.status} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontWeight: 700,
                        fontSize: 15,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}>
                        {motion.title}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                        by {motion.proposerName} &middot; {motion.createdAtISO.slice(0, 10)}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Quick actions */}
          <section style={{ marginBottom: 32 }}>
            <h2 style={{
              fontSize: 20,
              fontWeight: 800,
              margin: '0 0 16px',
              color: 'var(--text-primary)',
              letterSpacing: '-0.01em',
            }}>
              Get involved
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 16,
            }}>
              <Link
                to="/governance/propose"
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-card)',
                  padding: 24,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'box-shadow 0.15s, transform 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>&#128227;</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
                  Propose a motion
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Submit a proposal for the community to consider, discuss, and vote on.
                </div>
              </Link>

              <Link
                to="/governance"
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-card)',
                  padding: 24,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'box-shadow 0.15s, transform 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>&#9878;&#65039;</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
                  Vote &amp; discuss
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Second motions, cast formal votes, upvote priorities, and join the discussion.
                </div>
              </Link>

              <Link
                to="/constituent/dashboard"
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-card)',
                  padding: 24,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'box-shadow 0.15s, transform 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>&#128203;</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
                  Sign initiatives
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Browse ballot initiatives and add your signature to the ones you support.
                </div>
              </Link>

              <Link
                to="/constituent/profile"
                style={{
                  background: 'var(--panel)',
                  borderRadius: 'var(--radius-lg)',
                  boxShadow: 'var(--shadow-card)',
                  padding: 24,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'box-shadow 0.15s, transform 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-card)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 8 }}>&#127942;</div>
                <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 6 }}>
                  Run for office
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Declare your candidacy, share your platform, and connect with constituents.
                </div>
              </Link>
            </div>
          </section>

        </div>
      </main>
      <Footer />
    </div>
  )
}
