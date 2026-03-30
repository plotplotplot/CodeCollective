import { Link, useLocation } from 'react-router-dom'

interface NavItemProps {
  to: string
  children: React.ReactNode
  end?: boolean
}

function NavItem({ to, children, end = false }: NavItemProps) {
  const location = useLocation()
  const isActive = end 
    ? location.pathname === to
    : location.pathname.startsWith(to)
  
  return (
    <Link
      to={to}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '10px 16px',
        borderRadius: 'var(--radius-md)',
        backgroundColor: isActive ? 'var(--primary)' : 'transparent',
        color: isActive ? '#fff' : 'var(--text-secondary)',
        textDecoration: 'none',
        fontSize: 14,
        fontWeight: isActive ? 600 : 500,
        transition: 'all 0.15s',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </Link>
  )
}

export function GovernanceNav() {
  const location = useLocation()
  
  // Only show on governance pages
  if (!location.pathname.startsWith('/governance')) {
    return null
  }
  
  return (
    <nav style={{
      backgroundColor: 'var(--panel)',
      borderBottom: '1px solid var(--border-subtle)',
      padding: '12px 0',
    }}>
      <div style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: '0 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        overflowX: 'auto',
        scrollbarWidth: 'none',
      }}>
        <NavItem to="/governance" end>
          <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
          Motions
        </NavItem>
        
        <NavItem to="/governance/propose">
          <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          Propose Motion
        </NavItem>
        
        <div style={{ 
          width: 1, 
          height: 24, 
          backgroundColor: 'var(--border-subtle)', 
          margin: '0 8px' 
        }} />
        
        <span style={{ 
          fontSize: 12, 
          color: 'var(--text-muted)', 
          fontWeight: 500,
          whiteSpace: 'nowrap',
        }}>
          Robert's Rules of Order
        </span>
      </div>
    </nav>
  )
}

/**
 * Breadcrumb component for governance pages
 */
interface BreadcrumbProps {
  items: Array<{ label: string; to?: string }>
}

export function GovernanceBreadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" style={{ marginBottom: 16 }}>
      <ol style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        listStyle: 'none',
        padding: 0,
        margin: 0,
        fontSize: 13,
      }}>
        <li>
          <Link 
            to="/governance"
            style={{
              color: 'var(--text-muted)',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              transition: 'color 0.15s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--primary)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
            </svg>
            Governance
          </Link>
        </li>
        
        {items.map((item, index) => (
          <li key={index} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" style={{ color: 'var(--text-muted)', opacity: 0.5 }}>
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
            {item.to ? (
              <Link
                to={item.to}
                style={{
                  color: 'var(--text-muted)',
                  textDecoration: 'none',
                  transition: 'color 0.15s',
                  maxWidth: 200,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
              >
                {item.label}
              </Link>
            ) : (
              <span style={{
                color: 'var(--text-primary)',
                fontWeight: 600,
                maxWidth: 300,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {item.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
