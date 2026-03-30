import { Link, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../app/AppProviders'

interface NavLinkProps {
  to: string
  children: React.ReactNode
  end?: boolean
  isActive?: boolean
}

function NavLink({ to, children, end = false, isActive: forceActive }: NavLinkProps) {
  const location = useLocation()
  const isActive = forceActive !== undefined 
    ? forceActive
    : (end 
        ? location.pathname === to
        : location.pathname.startsWith(to))
  
  return (
    <Link 
      to={to} 
      className={`portal-nav-link ${isActive ? 'active' : ''}`}
      style={{
        position: 'relative',
        color: isActive ? 'var(--primary)' : 'var(--text-secondary)',
        fontWeight: isActive ? 600 : 500,
        padding: '8px 16px',
        borderRadius: 'var(--radius-md)',
        transition: 'all 0.15s',
        textDecoration: 'none',
        backgroundColor: isActive ? 'var(--primary-bg)' : 'transparent',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}
    >
      {children}
      {isActive && (
        <span style={{
          position: 'absolute',
          bottom: -2,
          left: 16,
          right: 16,
          height: 2,
          backgroundColor: 'var(--primary)',
          borderRadius: 1,
        }} />
      )}
    </Link>
  )
}

export function Header() {
  const { role, user, logout, token } = useAuth()
  const location = useLocation()
  const displayName = user?.displayName || user?.email || 'Signed in'
  const accountSettingsPath = role === 'campaign_manager' ? '/campaign/account' : '/constituent/account'
  const nextUrl = window.location.href
  const [menuOpen, setMenuOpen] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  // Check admin status
  useEffect(() => {
    if (role === 'guest' || !token) {
      setIsAdmin(false)
      return
    }
    fetch('/api/org/admin/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((resp) => (resp.ok ? resp.json() : { is_admin: false }))
      .then((data) => setIsAdmin(Boolean(data.is_admin)))
      .catch(() => setIsAdmin(false))
  }, [role, token])

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!menuRef.current) return
      if (!menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    if (menuOpen) {
      document.addEventListener('mousedown', handleClick)
    }
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  // Determine active tabs based on current route
  const isCivicActive = 
    location.pathname === '/' ||
    location.pathname.startsWith('/governance') ||
    location.pathname.startsWith('/constituent') ||
    location.pathname.startsWith('/campaign') ||
    location.pathname.startsWith('/about') ||
    location.pathname.startsWith('/initiatives')
  
  const isFinanceActive =
    location.pathname.startsWith('/ecops') ||
    location.pathname.startsWith('/send') ||
    location.pathname.startsWith('/receive') ||
    location.pathname.startsWith('/create')

  return (
    <header className="portal-header" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <div className="portal-header-inner" style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
        {/* Brand */}
        <Link to="/" className="portal-brand" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <img src="/laurel_wreath_logo.png" alt="Code Collective" style={{ width: 40, height: 40 }} />
          <div>
            <div className="portal-brand-title" style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              Code Collective
            </div>
            <div className="portal-brand-sub" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Civic Governance Portal
            </div>
          </div>
        </Link>

        {/* Main Navigation */}
        <nav className="portal-nav" style={{ display: 'flex', alignItems: 'center', gap: 4, flex: 1 }}>
          {/* Civic tab - combines Home, Governance, Ballot, Campaign, About */}
          <NavLink to="/" isActive={isCivicActive}>
            <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
            </svg>
            Civic
          </NavLink>
          
          {/* Finance tab */}
          <NavLink to="/ecops" isActive={isFinanceActive}>
            <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
              <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd" />
            </svg>
            Finance
          </NavLink>
          
          {/* Admin tab */}
          <NavLink to="/admin" isActive={location.pathname === '/admin'}>
            <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
            </svg>
            Admin
          </NavLink>
        </nav>

        {/* Secondary Actions */}
        <div className="portal-auth" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {role !== 'guest' ? (
            <div className="portal-user" ref={menuRef} style={{ position: 'relative' }}>
              <button 
                type="button" 
                className="portal-user-trigger" 
                onClick={() => setMenuOpen((prev) => !prev)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  backgroundColor: menuOpen ? 'var(--panel-2)' : 'transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <span className="portal-avatar" style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  backgroundColor: 'var(--primary)',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  fontWeight: 700,
                }}>
                  {user?.avatarUrl ? (
                    <img src={user.avatarUrl} alt={displayName} style={{ width: '100%', height: '100%', borderRadius: '50%' }} />
                  ) : (
                    displayName.slice(0, 1).toUpperCase()
                  )}
                </span>
                <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                  {displayName.split(' ')[0]}
                </span>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" style={{ color: 'var(--text-muted)', transform: menuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                  <path d="M6 8L1 3h10z"/>
                </svg>
              </button>
              
              {menuOpen && (
                <div className="portal-user-menu" style={{
                  position: 'absolute',
                  top: 'calc(100% + 8px)',
                  right: 0,
                  backgroundColor: 'var(--panel)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                  minWidth: 180,
                  zIndex: 1000,
                  padding: 8,
                }}>
                  <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-subtle)', marginBottom: 4 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {displayName}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                      {role.replace('_', ' ')}
                    </div>
                  </div>
                  <Link 
                    to={accountSettingsPath}
                    onClick={() => setMenuOpen(false)}
                    style={{
                      display: 'block',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      textDecoration: 'none',
                      fontSize: 14,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--panel-2)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    Account Settings
                  </Link>
                  <Link 
                    to={role === 'campaign_manager' ? '/campaign/profile' : '/constituent/profile'}
                    onClick={() => setMenuOpen(false)}
                    style={{
                      display: 'block',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      textDecoration: 'none',
                      fontSize: 14,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--panel-2)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    Profile
                  </Link>
                  {isAdmin && (
                    <Link 
                      to="/admin"
                      onClick={() => setMenuOpen(false)}
                      style={{
                        display: 'block',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--accent-purple, #8b5cf6)',
                        textDecoration: 'none',
                        fontSize: 14,
                        fontWeight: 600,
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--panel-2)'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      <span style={{ marginRight: 6 }}>⚙️</span> Admin
                    </Link>
                  )}
                  <button 
                    type="button" 
                    onClick={logout}
                    style={{
                      display: 'block',
                      width: '100%',
                      textAlign: 'left',
                      padding: '8px 12px',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--accent-red)',
                      backgroundColor: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: 14,
                      fontWeight: 500,
                      transition: 'background 0.15s',
                      marginTop: 4,
                      borderTop: '1px solid var(--border-subtle)',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--accent-red-bg)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <a 
                className="portal-button" 
                href={`/pidp/auth/google/login?next=${encodeURIComponent(nextUrl)}`}
                style={{
                  padding: '8px 16px',
                  borderRadius: 999,
                  backgroundColor: 'var(--primary)',
                  color: '#fff',
                  textDecoration: 'none',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Log In
              </a>
              <Link
                to="/constituent/register"
                style={{
                  padding: '8px 16px',
                  borderRadius: 999,
                  border: '1px solid var(--border)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-primary)',
                  textDecoration: 'none',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
