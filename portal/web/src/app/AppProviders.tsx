import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { AppServices } from '../composition/createServices'
import type { UserRole } from '../domain/user/User'
import type { SessionUser } from '../ui/auth/SessionUser'
import { readVotes, writeVotes, readComments, writeComments, readProfiles, writeProfiles } from '../infrastructure/utils/localStorage'

type PidpUser = {
  id: string
  email: string
  full_name: string | null
  avatar_url?: string | null
  identity_data?: {
    display_name?: string | null
    avatar_url?: string | null
    first_name?: string | null
    last_name?: string | null
  } | null
}

type ServicesContextValue = {
  services: AppServices
}

const ServicesContext = createContext<ServicesContextValue | null>(null)

export function useServices(): AppServices {
  const ctx = useContext(ServicesContext)
  if (!ctx) throw new Error('useServices must be used within AppProviders')
  return ctx.services
}

type AuthContextValue = {
  role: UserRole | 'guest'
  user: SessionUser | null
  token: string | null
  isLoading: boolean
  setRole: (role: UserRole | 'guest') => void
  setUser: (user: SessionUser | null) => void
  loginWithPassword: (email: string, password: string) => Promise<void>
  registerWithPassword: (email: string, password: string, fullName?: string) => Promise<void>
  completeOAuthLogin: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AppProviders')
  return ctx
}

function readInitialRole(): UserRole | 'guest' {
  const value = localStorage.getItem('demo.role')
  if (value === 'campaign_manager' || value === 'constituent' || value === 'guest') return value
  return 'guest'
}

function readInitialUser(): SessionUser | null {
  const raw = localStorage.getItem('pidp.user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as SessionUser
  } catch {
    return null
  }
}

export function AppProviders(props: { services: AppServices; children: ReactNode }) {
  const [role, setRoleState] = useState<UserRole | 'guest'>(() => readInitialRole())
  const [user, setUserState] = useState<SessionUser | null>(() => readInitialUser())
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [showMigration, setShowMigration] = useState(false)
  const [pendingMigration, setPendingMigration] = useState<{guestId: string, userId: string, displayName: string} | null>(null)

  const pidpBaseUrl = (import.meta.env.VITE_PIDP_BASE_URL as string | undefined) ?? '/pidp'
  const normalizedPidpBase = pidpBaseUrl.replace(/\/$/, '')

  const normalizeAvatarUrl = useCallback(
    (rawUrl?: string | null): string | null => {
      if (!rawUrl) return null
      if (/^(data:|https?:\/\/)/i.test(rawUrl)) return rawUrl
      if (rawUrl.startsWith(`${normalizedPidpBase}/`)) return rawUrl
      const cleaned = rawUrl.replace(/^\/+/, '')
      return `${normalizedPidpBase}/${cleaned}`
    },
    [normalizedPidpBase],
  )

  const servicesValue = useMemo<ServicesContextValue>(() => ({ services: props.services }), [props.services])

  const migrateGuestData = useCallback(() => {
    if (!pendingMigration) return
    const { guestId, userId, displayName } = pendingMigration
    // Migrate votes
    const votes = readVotes()
    for (const motionId in votes) {
      if (votes[motionId][guestId]) {
        votes[motionId][userId] = votes[motionId][guestId]
        delete votes[motionId][guestId]
      }
    }
    writeVotes(votes)
    // Migrate comments
    const comments = readComments()
    for (const comment of comments) {
      if (comment.authorId === guestId) {
        comment.authorId = userId
        comment.authorName = displayName
      }
    }
    writeComments(comments)
    // Migrate profiles
    const profiles = readProfiles()
    if (profiles[guestId]) {
      profiles[userId] = profiles[guestId]
      delete profiles[guestId]
    }
    writeProfiles(profiles)
    // Clear guestId
    localStorage.removeItem('governance.guestId')
    setShowMigration(false)
    setPendingMigration(null)
    // Reload page to update displayed comments
    window.location.reload()
  }, [pendingMigration])

  const formatApiError = useCallback(async (resp: Response, fallback: string) => {
    const data = await resp.json().catch(() => null)
    if (data && Array.isArray(data.detail)) {
      const details = data.detail
        .map((item: { loc?: (string | number)[]; msg?: string }) => {
          if (!item || !item.msg) return null
          const field = item.loc?.slice(1).join('.') ?? 'request'
          return `${field}: ${item.msg}`
        })
        .filter(Boolean)
      if (details.length) return `${fallback} ${details.join('; ')}`
    }
    if (data?.detail) return `${fallback} ${data.detail}`
    const text = await resp.text().catch(() => '')
    return text ? `${fallback} ${text}` : fallback
  }, [])

  // Login with password - sets HTTP-only cookie via PIdP
  const loginWithPassword = useCallback(
    async (email: string, password: string) => {
      const body = new URLSearchParams()
      body.set('username', email)
      body.set('password', password)
      const resp = await fetch(`${normalizedPidpBase}/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        credentials: 'include', // Important: include cookies
        body,
      })
      if (!resp.ok) {
        throw new Error(await formatApiError(resp, 'Login failed.'))
      }
      // Cookie is set by server, now hydrate session
      setIsLoading(true)
    },
    [normalizedPidpBase],
  )

  const registerWithPassword = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const resp = await fetch(`${normalizedPidpBase}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, full_name: fullName ?? null }),
      })
      if (!resp.ok) {
        if (resp.status === 409) {
          const data = await resp.json().catch(() => null)
          const detail =
            typeof data?.detail === 'string'
              ? data.detail
              : typeof data?.detail?.message === 'string'
                ? data.detail.message
                : null
          throw new Error(detail || 'Account already exists. Please log in.')
        }
        const message = await formatApiError(resp, `Registration failed (${resp.status}).`)
        throw new Error(message)
      }
      await loginWithPassword(email, password)
    },
    [normalizedPidpBase, loginWithPassword, formatApiError],
  )

  // Check for OAuth token in URL hash (for OAuth flows that return token)
  useEffect(() => {
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : window.location.hash
    const params = new URLSearchParams(hash || window.location.search)
    const accessToken = params.get('token')
    if (!accessToken) return
    // OAuth login successful, clear hash and hydrate session
    // The cookie should already be set by PIdP OAuth callback
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
    setIsLoading(true)
  }, [])

  // Main session hydration effect - uses HTTP-only cookie only
  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    async function hydrateSession() {
      try {
        // Call /auth/me with credentials to use the HTTP-only cookie
        const resp = await fetch(`${normalizedPidpBase}/auth/me`, {
          credentials: 'include', // Include cookies
          signal: controller.signal,
        })
        
        if (!resp.ok) throw new Error('Not authenticated')
        
        const data = (await resp.json()) as PidpUser
        const displayName = data.identity_data?.display_name?.trim() || data.full_name?.trim() || data.email
        const handle = data.email.split('@')[0]
        const avatarUrl = normalizeAvatarUrl(data.identity_data?.avatar_url ?? data.avatar_url)
        const firstName = data.identity_data?.first_name ?? null
        const lastName = data.identity_data?.last_name ?? null
        
        if (cancelled) return
        
        setRoleState('constituent')
        localStorage.setItem('demo.role', 'constituent')
        setUserState({
          id: data.id,
          role: 'constituent',
          displayName,
          handle,
          email: data.email,
          fullName: data.full_name,
          firstName,
          lastName,
          avatarUrl,
        })
        // Store user info (not token) in localStorage for UI state
        localStorage.setItem(
          'pidp.user',
          JSON.stringify({
            id: data.id,
            role: 'constituent',
            displayName,
            handle,
            email: data.email,
            fullName: data.full_name,
            firstName,
            lastName,
            avatarUrl,
          }),
        )
        
        // Check for guest data migration
        const guestId = localStorage.getItem('governance.guestId')
        if (guestId && guestId !== data.id) {
          const votes = readVotes()
          let hasGuestData = false
          for (const motionVotes of Object.values(votes)) {
            if (motionVotes[guestId]) {
              hasGuestData = true
              break
            }
          }
          if (hasGuestData) {
            setPendingMigration({ guestId, userId: data.id, displayName })
            setShowMigration(true)
          }
        }
      } catch {
        if (!cancelled) {
          setRoleState('guest')
          localStorage.setItem('demo.role', 'guest')
          setToken(null)
          setUserState(null)
          localStorage.removeItem('pidp.user')
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    hydrateSession()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [normalizedPidpBase, normalizeAvatarUrl])

  const authValue = useMemo<AuthContextValue>(
    () => ({
      role,
      user,
      token,
      isLoading,
      setRole: (r) => {
        setRoleState(r)
        localStorage.setItem('demo.role', r)
        if (r === 'guest') {
          setUserState(null)
          localStorage.removeItem('pidp.user')
        }
      },
      setUser: (u) => {
        setUserState(u)
        if (!u) localStorage.removeItem('pidp.user')
        else localStorage.setItem('pidp.user', JSON.stringify(u))
      },
      loginWithPassword,
      registerWithPassword,
      completeOAuthLogin: () => {
        // OAuth login sets cookie via redirect, just hydrate
        setIsLoading(true)
      },
      logout: () => {
        setRoleState('guest')
        localStorage.setItem('demo.role', 'guest')
        setToken(null)
        setUserState(null)
        localStorage.removeItem('pidp.user')
        // Call PIdP logout to clear HTTP-only cookie
        fetch(`${normalizedPidpBase}/logout`, { 
          method: 'GET', 
          credentials: 'include' 
        }).then(() => {
          // Reload to clear any cached state
          window.location.reload()
        }).catch(() => {
          window.location.reload()
        })
      },
    }),
    [role, user, token, isLoading, loginWithPassword, registerWithPassword, normalizedPidpBase],
  )

  return (
    <ServicesContext.Provider value={servicesValue}>
      <AuthContext.Provider value={authValue}>
        <div style={{ border: role === 'guest' ? '2px solid red' : 'none', minHeight: '100vh' }}>
          {props.children}
        </div>
        {showMigration && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{
              background: 'white',
              padding: 20,
              borderRadius: 8,
              maxWidth: 400,
              color: 'black',
            }}>
              <h3>Migrate Guest Data</h3>
              <p>You have data from guest mode. Would you like to migrate it to your account?</p>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button onClick={() => setShowMigration(false)} style={{ padding: '8px 16px' }}>No</button>
                <button onClick={migrateGuestData} style={{ padding: '8px 16px', background: 'var(--primary)', color: 'white', border: 'none', borderRadius: 4 }}>Yes</button>
              </div>
            </div>
          </div>
        )}
      </AuthContext.Provider>
    </ServicesContext.Provider>
  )
}
