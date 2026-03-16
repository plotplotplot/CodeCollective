import { Link } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../../app/AppProviders'

export function Header() {
  const { role, user, logout } = useAuth()
  const displayName = user?.displayName || user?.email || 'Signed in'
  const accountSettingsPath = role === 'campaign_manager' ? '/campaign/account' : '/constituent/account'
  const nextUrl = window.location.href
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

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

  return (
    <header className="portal-header">
      <div className="portal-header-inner">
        <Link to="/" className="portal-brand">
          <img src="/laurel_wreath_logo.png" alt="Code Collective" />
          <div>
            <div className="portal-brand-title">Code Collective</div>
            <div className="portal-brand-sub">Economic Operations</div>
          </div>
        </Link>
        <nav className="portal-nav">
          <Link to="/">Overview</Link>
          <Link to="/send">Send</Link>
          <Link to="/receive">Receive</Link>
          <Link to="/create">Create</Link>
          <Link to="/ecops">EcOps</Link>
          <a href="/pidp">Identity</a>
          <a href="/cockroach">Ledger</a>
        </nav>
        <div className="portal-auth">
          {role !== 'guest' ? (
            <div className="portal-user" ref={menuRef}>
              <button type="button" className="portal-user-trigger" onClick={() => setMenuOpen((prev) => !prev)}>
                <span className="portal-avatar">
                  {user?.avatarUrl ? (
                    <img src={user.avatarUrl} alt={displayName} />
                  ) : (
                    displayName.slice(0, 1).toUpperCase()
                  )}
                </span>
                <span>{displayName}</span>
              </button>
              {menuOpen && (
                <div className="portal-user-menu">
                  <Link to={accountSettingsPath}>Account settings</Link>
                  <button type="button" onClick={logout}>
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <a className="portal-button" href={`/pidp/auth/google/login?next=${encodeURIComponent(nextUrl)}`}>
              Log In
            </a>
          )}
        </div>
      </div>
    </header>
  )
}
