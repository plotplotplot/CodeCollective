import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useAuth } from '../../app/AppProviders'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'

const ORG_API_BASE = '/api/org'

type AccountSummary = {
  id: string
  name: string
  email: string
  entity_type: string
}

type EntityCreatePayload = {
  entity_type: 'nonprofit'
  name: string
  email: string
  address?: string
  mission_statement?: string
  initial_deposit: number
}

function orgUrl(path: string) {
  if (!path.startsWith('/')) return `${ORG_API_BASE}/${path}`
  return `${ORG_API_BASE}${path}`
}

async function orgFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(orgUrl(path), options)
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(text || `Request failed (${resp.status})`)
  }
  return (await resp.json()) as T
}

export function CreateNonProfitPage() {
  const { token } = useAuth()
  const [allUsers, setAllUsers] = useState<AccountSummary[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [board, setBoard] = useState<AccountSummary[]>([])
  const [form, setForm] = useState({
    name: '',
    email: '',
    address: '',
    mission_statement: '',
    initial_deposit: '0',
  })
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!token) return
    orgFetch<AccountSummary[]>('/api/accounts?limit=2000&sort=name_asc', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((data) => setAllUsers(Array.isArray(data) ? data : []))
      .catch(() => setAllUsers([]))
  }, [token])

  const boardIdSet = useMemo(() => new Set(board.map((member) => member.id)), [board])
  const rankedUsers = useMemo(() => {
    const pool = allUsers.filter((u) => !boardIdSet.has(u.id))
    const needle = searchTerm.trim().toLowerCase()
    if (!needle) return pool.slice(0, 25)

    const scored = pool
      .map((user) => {
        const name = user.name.toLowerCase()
        const email = user.email.toLowerCase()
        let score = 0
        if (name === needle) score += 1000
        if (email === needle) score += 1000
        if (name.startsWith(needle)) score += 700
        if (email.startsWith(needle)) score += 650
        if (name.includes(needle)) score += 350
        if (email.includes(needle)) score += 300

        // Token-aware boosts (e.g., searching first or last name part)
        const nameTokens = name.split(/\s+/).filter(Boolean)
        if (nameTokens.some((token) => token.startsWith(needle))) score += 220
        if (nameTokens.some((token) => token.includes(needle))) score += 120

        // Mild closeness boost for short-distance matches.
        const idx = name.indexOf(needle)
        if (idx >= 0) score += Math.max(0, 80 - idx * 4)

        return { user, score }
      })
      .filter((entry) => entry.score > 0)
      .sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score
        return a.user.name.localeCompare(b.user.name)
      })

    return scored.slice(0, 25).map((entry) => entry.user)
  }, [allUsers, boardIdSet, searchTerm])

  const filteredUsers = useMemo(() => {
    return rankedUsers
  }, [rankedUsers])

  function addBoardMember(user: AccountSummary) {
    if (boardIdSet.has(user.id)) return
    setBoard((prev) => [...prev, user])
  }

  function removeBoardMember(userId: string) {
    setBoard((prev) => prev.filter((member) => member.id !== userId))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!token) {
      setStatus('Sign in required.')
      return
    }
    setBusy(true)
    setStatus('')
    try {
      const boardSummary = board.map((member) => `${member.name} <${member.email}>`).join(', ')
      const mission = form.mission_statement.trim()
      const missionWithBoard = boardSummary ? `${mission}\n\nBoard: ${boardSummary}`.trim() : mission
      const payload: EntityCreatePayload = {
        entity_type: 'nonprofit',
        name: form.name.trim(),
        email: form.email.trim(),
        address: form.address.trim() || undefined,
        mission_statement: missionWithBoard || undefined,
        initial_deposit: Number(form.initial_deposit || '0'),
      }
      await orgFetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
      setStatus('Non-profit entity created.')
      setForm({
        name: '',
        email: '',
        address: '',
        mission_statement: '',
        initial_deposit: '0',
      })
      setBoard([])
      setSearchTerm('')
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Failed to create entity.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero">
            <div>
              <span className="portal-pill">Create</span>
              <h1>Non Profit</h1>
              <p className="portal-muted">Register a nonprofit and assemble your board.</p>
            </div>
          </section>
          <section className="portal-section">
            <div className="portal-grid">
              <form className="portal-card portal-form" onSubmit={onSubmit}>
                <label>
                  Name
                  <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
                </label>
                <label>
                  Email
                  <input type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
                </label>
                <label>
                  Initial deposit (DEM)
                  <input type="number" min="0" step="0.01" value={form.initial_deposit} onChange={(event) => setForm({ ...form, initial_deposit: event.target.value })} />
                </label>
                <label>
                  Address
                  <input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
                </label>
                <label>
                  Mission statement
                  <textarea rows={4} value={form.mission_statement} onChange={(event) => setForm({ ...form, mission_statement: event.target.value })} />
                </label>
                <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create'}</button>
                {status && <p className="portal-muted">{status}</p>}
              </form>

              <div className="portal-card">
                <h3 style={{ marginTop: 0 }}>Board assembly</h3>
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Search users by name or email"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 12, border: '1px solid rgba(12, 30, 60, 0.2)' }}
                />
                <div style={{ marginTop: 12, display: 'grid', gap: 8, maxHeight: 260, overflow: 'auto' }}>
                  {filteredUsers.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      className="portal-timeframe-button"
                      style={{ justifyContent: 'space-between', display: 'flex', borderRadius: 10, padding: '8px 10px' }}
                      onClick={() => addBoardMember(user)}
                    >
                      <span>{user.name}</span>
                      <span style={{ opacity: 0.7 }}>{user.email}</span>
                    </button>
                  ))}
                  {filteredUsers.length === 0 && <p className="portal-muted">No users match.</p>}
                </div>
                <h4 style={{ marginTop: 16, marginBottom: 8 }}>Selected board</h4>
                <div style={{ display: 'grid', gap: 8 }}>
                  {board.map((member) => (
                    <div key={member.id} className="portal-card" style={{ padding: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 700 }}>{member.name}</div>
                        <div className="portal-muted">{member.email}</div>
                      </div>
                      <button type="button" className="portal-timeframe-button" onClick={() => removeBoardMember(member.id)}>
                        Remove
                      </button>
                    </div>
                  ))}
                  {board.length === 0 && <p className="portal-muted">No board members selected.</p>}
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
