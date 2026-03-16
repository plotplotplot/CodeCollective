import { useState, type FormEvent } from 'react'
import { useAuth } from '../../app/AppProviders'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'

const ORG_API_BASE = '/api/org'

type EntityCreatePayload = {
  entity_type: 'business'
  name: string
  email: string
  address?: string
  business_type?: string
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

export function CreateForProfitPage() {
  const { token } = useAuth()
  const [form, setForm] = useState({
    name: '',
    email: '',
    address: '',
    business_type: '',
    mission_statement: '',
    initial_deposit: '0',
  })
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!token) {
      setStatus('Sign in required.')
      return
    }
    setBusy(true)
    setStatus('')
    try {
      const payload: EntityCreatePayload = {
        entity_type: 'business',
        name: form.name.trim(),
        email: form.email.trim(),
        address: form.address.trim() || undefined,
        business_type: form.business_type.trim() || undefined,
        mission_statement: form.mission_statement.trim() || undefined,
        initial_deposit: Number(form.initial_deposit || '0'),
      }
      await orgFetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
      setStatus('For-profit entity created.')
      setForm({
        name: '',
        email: '',
        address: '',
        business_type: '',
        mission_statement: '',
        initial_deposit: '0',
      })
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
              <h1>For Profit</h1>
              <p className="portal-muted">Register a business entity.</p>
            </div>
          </section>
          <section className="portal-section">
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
                Business type
                <input value={form.business_type} onChange={(event) => setForm({ ...form, business_type: event.target.value })} />
              </label>
              <label>
                Mission statement
                <textarea rows={3} value={form.mission_statement} onChange={(event) => setForm({ ...form, mission_statement: event.target.value })} />
              </label>
              <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create'}</button>
              {status && <p className="portal-muted">{status}</p>}
            </form>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}

