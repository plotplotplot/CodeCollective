import { useEffect, useState } from 'react'
import { useAuth } from '../../../app/AppProviders'

export function ConstituentAccountPage() {
  const { user, token } = useAuth()
  const [email, setEmail] = useState('demo.constituent@example.com')
  const [addressLine1, setAddressLine1] = useState('123 Example St NW')
  const [addressLine2, setAddressLine2] = useState('')
  const [city, setCity] = useState('Washington')
  const [state, setState] = useState('DC')
  const [postalCode, setPostalCode] = useState('20001')
  const [country, setCountry] = useState('United States')
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)

  useEffect(() => {
    document.title = 'ballot-sign • Constituent account'
  }, [])

  useEffect(() => {
    if (user?.avatarUrl) {
      setAvatarUrl(user.avatarUrl)
      return
    }
    const raw = localStorage.getItem('constituent.profile')
    if (!raw) return
    try {
      const saved = JSON.parse(raw) as { avatarUrl?: string }
      if (saved.avatarUrl) setAvatarUrl(saved.avatarUrl)
    } catch {
      // Ignore malformed local profile data.
    }
  }, [user?.avatarUrl])

  useEffect(() => {
    if (!token || avatarUrl) return
    let cancelled = false
    fetch('/pidp/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((resp) => (resp.ok ? resp.json() : null))
      .then((data) => {
        if (cancelled) return
        const nextAvatar = data?.identity_data?.avatar_url ?? data?.avatar_url ?? null
        if (nextAvatar) setAvatarUrl(nextAvatar)
      })
      .catch(() => {
        // Keep fallback initial if PIDP profile cannot be loaded.
      })
    return () => {
      cancelled = true
    }
  }, [token, avatarUrl])

  const displayName = user?.displayName || user?.email || 'Signed in'

  return (
    <section className="panel">
      <h1 style={{ marginTop: 0 }}>Account (constituent)</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        Demo-only editable form.
      </p>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.9rem' }}>
        <span className="portal-avatar" style={{ width: 48, height: 48 }}>
          {avatarUrl ? <img src={avatarUrl} alt={displayName} /> : displayName.slice(0, 1).toUpperCase()}
        </span>
        <div>
          <div style={{ fontWeight: 700 }}>{displayName}</div>
          <div className="muted">Profile image from identity provider</div>
        </div>
      </div>
      <div style={{ display: 'grid', gap: '0.6rem' }}>
        <div>
          <label className="muted" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <div>
          <label className="muted" htmlFor="addr-line1">
            Address line 1
          </label>
          <input
            id="addr-line1"
            name="addressLine1"
            autoComplete="address-line1"
            value={addressLine1}
            onChange={(e) => setAddressLine1(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <div>
          <label className="muted" htmlFor="addr-line2">
            Address line 2
          </label>
          <input
            id="addr-line2"
            name="addressLine2"
            autoComplete="address-line2"
            value={addressLine2}
            onChange={(e) => setAddressLine2(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <div>
          <label className="muted" htmlFor="city">
            City
          </label>
          <input id="city" name="city" autoComplete="address-level2" value={city} onChange={(e) => setCity(e.target.value)} style={{ width: '100%' }} />
        </div>
        <div>
          <label className="muted" htmlFor="state">
            State
          </label>
          <input
            id="state"
            name="state"
            autoComplete="address-level1"
            value={state}
            onChange={(e) => setState(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <div>
          <label className="muted" htmlFor="postal-code">
            ZIP code
          </label>
          <input
            id="postal-code"
            name="postalCode"
            autoComplete="postal-code"
            value={postalCode}
            onChange={(e) => setPostalCode(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <div>
          <label className="muted" htmlFor="country">
            Country
          </label>
          <input
            id="country"
            name="country"
            autoComplete="country-name"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
        <button type="button" onClick={() => alert('Account saved (mock)')}>
          Save account
        </button>
      </div>
    </section>
  )
}
