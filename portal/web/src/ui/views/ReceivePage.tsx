import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../app/AppProviders'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'
import { createQrSvg } from '../utils/qr'

const ORG_API_BASE = '/api/org'

type MeAccount = {
  id: string
  name: string
  email: string
  balance: number
}

type Transaction = {
  id: string
  from_account_id?: string | null
  to_account_id?: string | null
  amount: number
  transaction_type: string
  description: string
  timestamp: string
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

export function ReceivePage() {
  const { token } = useAuth()
  const [me, setMe] = useState<MeAccount | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [error, setError] = useState('')
  const [requestAmount, setRequestAmount] = useState('10.00')
  const [copyStatus, setCopyStatus] = useState('')

  useEffect(() => {
    if (!token) return
    const headers = { Authorization: `Bearer ${token}` }
    Promise.allSettled([
      orgFetch<MeAccount>('/api/accounts/me', { headers }),
      orgFetch<Transaction[]>('/api/accounts/me/transactions?limit=50', { headers }),
    ]).then(([meResult, txResult]) => {
      if (meResult.status === 'fulfilled') {
        setMe(meResult.value)
      } else {
        setError('Failed to load account.')
      }
      if (txResult.status === 'fulfilled') {
        setTransactions(Array.isArray(txResult.value) ? txResult.value : [])
      }
    })
  }, [token])

  const incoming = useMemo(() => {
    if (!me) return []
    return transactions.filter((tx) => tx.to_account_id === me.id).slice(0, 10)
  }, [transactions, me])

  const paymentRequestUrl = useMemo(() => {
    if (!me) return ''
    const base = import.meta.env.BASE_URL ?? '/'
    const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base
    const sendPath = `${normalizedBase}/send`
    const params = new URLSearchParams({
      t: me.id,
      a: requestAmount || '0',
    })
    return `${window.location.origin}${sendPath}?${params.toString()}`
  }, [me, requestAmount])

  const qrSvg = useMemo(() => {
    if (!paymentRequestUrl) return ''
    try {
      return createQrSvg(paymentRequestUrl, 8, 4)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      console.error('QR generation failed', {
        message,
        paymentRequestUrl,
        payloadLength: paymentRequestUrl.length,
      })
      return ''
    }
  }, [paymentRequestUrl])

  async function copyRequestLink() {
    if (!paymentRequestUrl) return
    try {
      await navigator.clipboard.writeText(paymentRequestUrl)
      setCopyStatus('Link copied.')
    } catch {
      setCopyStatus('Unable to copy link.')
    }
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero">
            <div>
              <span className="portal-pill">Payments</span>
              <h1>Receive Dena</h1>
              <p className="portal-muted">Share your account details to receive transfers.</p>
              {error && <p className="portal-muted">{error}</p>}
            </div>
            <div className="portal-card">
              <div className="portal-muted">Account ID</div>
              <div style={{ fontWeight: 700, wordBreak: 'break-all' }}>{me?.id ?? '—'}</div>
              <div className="portal-muted">{me?.email ?? ''}</div>
            </div>
          </section>

          <section className="portal-section">
            <h2>Request payment</h2>
            <div className="portal-grid">
              <div className="portal-card portal-form">
                <label>
                  Amount (DEM)
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={requestAmount}
                    onChange={(event) => setRequestAmount(event.target.value)}
                  />
                </label>
                <label>
                  Payment request link
                  <input value={paymentRequestUrl} readOnly />
                </label>
                <button type="button" className="secondary" onClick={copyRequestLink}>
                  Copy link
                </button>
                {copyStatus && <p className="portal-muted">{copyStatus}</p>}
              </div>
              <div className="portal-card" style={{ display: 'grid', placeItems: 'center' }}>
                {qrSvg ? (
                  <div
                    style={{ width: '100%', maxWidth: 320 }}
                    dangerouslySetInnerHTML={{ __html: qrSvg }}
                  />
                ) : (
                  <p className="portal-muted">QR code unavailable.</p>
                )}
                <p className="portal-muted" style={{ marginTop: 10, textAlign: 'center' }}>
                  Scan to open Send page with recipient and amount pre-filled.
                </p>
              </div>
            </div>
          </section>

          <section className="portal-section">
            <h2>Latest incoming transfers</h2>
            <div className="portal-card" style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Time</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Type</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>Amount</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {incoming.map((tx) => (
                    <tr key={tx.id} style={{ borderTop: '1px solid rgba(12, 30, 60, 0.12)' }}>
                      <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{new Date(tx.timestamp).toLocaleString()}</td>
                      <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>
                        {String(tx.transaction_type || '').toLowerCase().replaceAll('_', ' ')}
                      </td>
                      <td style={{ padding: '8px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(tx.amount)} DEM
                      </td>
                      <td style={{ padding: '8px 6px' }}>{tx.description || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {incoming.length === 0 && <p className="portal-muted">No incoming transfers yet.</p>}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
