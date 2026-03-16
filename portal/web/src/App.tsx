import { useEffect, useMemo, useState, type WheelEvent } from 'react'
import { useAuth } from './app/AppProviders'
import { Header } from './ui/shell/Header'
import { Footer } from './ui/shell/Footer'

const ORG_API_BASE = '/api/org'

type Account = {
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

type Portfolio = {
  portfolio_value: number
  total_invested: number
  unrealized_gains: number
  cash_balance: number
  holdings: Array<{
    stock_id: string
    ticker: string
    company_name: string
    quantity: number
    average_price: number
    current_price: number
    current_value: number
    unrealized_gain: number
  }>
}

type InsurancePolicy = {
  id: string
  insurance_type: string
  coverage_amount: number
  premium_amount: number
  duration_years: number
  start_date: string
  end_date: string
  deductible: number | null
  is_active: boolean
}

type BalancePoint = { timestamp: string; balance: number }
type BalanceEvent = { time: number; balance: number }

const HOUR_MS = 60 * 60 * 1000
const DAY_MS = 24 * HOUR_MS
const YEAR_MS = 365 * DAY_MS
const MIN_TIMEFRAME_MS = HOUR_MS
const MAX_TIMEFRAME_MS = 5 * YEAR_MS
const DEFAULT_TIMEFRAME_MS = 30 * DAY_MS

const TIMEFRAME_PRESETS: Array<{ label: string; durationMs: number }> = [
  { label: '1H', durationMs: HOUR_MS },
  { label: '1W', durationMs: 7 * DAY_MS },
  { label: '1M', durationMs: 30 * DAY_MS },
  { label: '1Y', durationMs: YEAR_MS },
  { label: '3Y', durationMs: 3 * YEAR_MS },
  { label: '5Y', durationMs: 5 * YEAR_MS },
]

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

function toFiniteNumber(value: unknown, fallback = 0): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined) return '—'
  return numberFormat.format(value)
}

function formatCurrency(value?: number | null, currency = 'DEM') {
  if (value === null || value === undefined) return '—'
  return `${numberFormat.format(value)} ${currency}`
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

export default function App() {
  const { role, user, token } = useAuth()
  const [account, setAccount] = useState<Account | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [policies, setPolicies] = useState<InsurancePolicy[]>([])
  const [error, setError] = useState<string | null>(null)
  const [timeframeMs, setTimeframeMs] = useState<number>(DEFAULT_TIMEFRAME_MS)
  const [activePresetLabel, setActivePresetLabel] = useState<string>('1M')

  const withAuthHeader = (base: Record<string, string> = {}): Record<string, string> => {
    if (token) return { ...base, Authorization: `Bearer ${token}` }
    return base
  }

  useEffect(() => {
    if (role === 'guest' || !token) return
    let cancelled = false
    async function load() {
      try {
        const [accountData, txData, portfolioData, policyData] = await Promise.all([
          orgFetch<Account>('/api/accounts/me', { headers: withAuthHeader() }),
          orgFetch<Transaction[]>('/api/accounts/me/transactions', { headers: withAuthHeader() }),
          orgFetch<Portfolio>('/api/portfolio', { headers: withAuthHeader() }),
          orgFetch<InsurancePolicy[]>('/api/insurance/policies', { headers: withAuthHeader() }),
        ])
        if (cancelled) return
        setAccount(accountData)
        setTransactions(Array.isArray(txData) ? txData : [])
        setPortfolio(portfolioData)
        setPolicies(Array.isArray(policyData) ? policyData : [])
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load account data')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [role, token])

  const balanceEvents = useMemo<BalanceEvent[]>(() => {
    if (!account) return []
    if (!transactions.length) return []
    const accountBalance = toFiniteNumber(account.balance)
    const sorted = [...transactions].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    const deltaFor = (tx: Transaction) => {
      const amount = toFiniteNumber(tx.amount)
      if (tx.to_account_id === account.id) return amount
      if (tx.from_account_id === account.id) return -amount
      return 0
    }
    let startBalance = accountBalance
    for (let i = sorted.length - 1; i >= 0; i -= 1) {
      startBalance -= deltaFor(sorted[i])
    }
    let running = startBalance
    const points: BalanceEvent[] = []
    for (const tx of sorted) {
      running += deltaFor(tx)
      points.push({ time: new Date(tx.timestamp).getTime(), balance: running })
    }
    return points
  }, [account, transactions])

  const balanceSeries = useMemo<BalancePoint[]>(() => {
    if (!account) return []
    const pointCount = 120
    const now = Date.now()
    const start = now - timeframeMs
    const interval = timeframeMs / (pointCount - 1)
    const firstTrackedAt = balanceEvents[0]?.time ?? Number.POSITIVE_INFINITY

    let eventIndex = 0
    let currentBalance = 0
    const points: BalancePoint[] = []

    for (let i = 0; i < pointCount; i += 1) {
      const ts = start + interval * i
      if (ts < firstTrackedAt) {
        points.push({ timestamp: new Date(ts).toISOString(), balance: 0 })
        continue
      }
      while (eventIndex < balanceEvents.length && balanceEvents[eventIndex].time <= ts) {
        currentBalance = balanceEvents[eventIndex].balance
        eventIndex += 1
      }
      points.push({ timestamp: new Date(ts).toISOString(), balance: currentBalance })
    }
    return points
  }, [account, balanceEvents, timeframeMs])

  const chartPath = useMemo(() => {
    if (!balanceSeries.length) return ''
    const width = 600
    const height = 180
    const padding = 16
    const values = balanceSeries.map((point) => toFiniteNumber(point.balance))
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const range = maxVal - minVal || 1
    const path = balanceSeries
      .map((point, index) => {
        const x = padding + (index / (balanceSeries.length - 1 || 1)) * (width - padding * 2)
        const y = height - padding - ((toFiniteNumber(point.balance) - minVal) / range) * (height - padding * 2)
        return `${index === 0 ? 'M' : 'L'}${x},${y}`
      })
      .join(' ')
    return path.includes('NaN') ? '' : path
  }, [balanceSeries])

  const onChartWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault()
    const zoomScale = Math.exp(event.deltaY * 0.0015)
    setTimeframeMs((prev) => {
      const next = prev * zoomScale
      if (next < MIN_TIMEFRAME_MS) return MIN_TIMEFRAME_MS
      if (next > MAX_TIMEFRAME_MS) return MAX_TIMEFRAME_MS
      return next
    })
    setActivePresetLabel('')
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero" id="overview">
            <div>
              <span className="portal-pill">Personal console</span>
              <h1>Welcome back{user?.displayName ? `, ${user.displayName}` : ''}</h1>
              <p className="portal-muted">Track your balances, equity exposure, and insured assets.</p>
              {error && <p className="portal-muted">{error}</p>}
            </div>
            <div className="portal-card">
              <div className="portal-muted">Current balance</div>
              <div style={{ fontSize: '2rem', fontWeight: 700 }}>{formatCurrency(account?.balance)}</div>
              <div className="portal-muted">Account: {account?.email ?? '—'}</div>
            </div>
          </section>

          <section className="portal-section">
            <div className="portal-section-header">
              <h2>Balance over time</h2>
              <div className="portal-timeframe-controls">
                {TIMEFRAME_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    className={`portal-timeframe-button ${activePresetLabel === preset.label ? 'active' : ''}`}
                    onClick={() => {
                      setTimeframeMs(preset.durationMs)
                      setActivePresetLabel(preset.label)
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="portal-card" onWheel={onChartWheel}>
              {balanceSeries.length === 0 ? (
                <div className="portal-muted">No transactions yet.</div>
              ) : (
                <svg viewBox="0 0 600 180" width="100%" height="200" role="img" aria-label="Balance history">
                  <path d={chartPath} fill="none" stroke="#0b1a33" strokeWidth="2" />
                </svg>
              )}
              <div className="portal-muted">Use mouse wheel over chart to smoothly zoom timeframe.</div>
            </div>
          </section>

          <section className="portal-section" id="equities">
            <h2>Equities</h2>
            <p className="portal-muted">Holdings and market value.</p>
            <div className="portal-grid">
              {portfolio?.holdings?.length ? (
                portfolio.holdings.map((holding) => (
                  <div key={holding.stock_id} className="portal-card">
                    <div className="portal-pill">{holding.ticker}</div>
                    <h3>{holding.company_name}</h3>
                    <div className="portal-muted">Qty: {formatNumber(holding.quantity)}</div>
                    <div style={{ fontWeight: 700 }}>{formatCurrency(holding.current_value)}</div>
                    <div className="portal-muted">Unrealized: {formatCurrency(holding.unrealized_gain)}</div>
                  </div>
                ))
              ) : (
                <div className="portal-card">No equities yet.</div>
              )}
            </div>
          </section>

          <section className="portal-section" id="insurance">
            <h2>Insurance assets</h2>
            <p className="portal-muted">Active policies and coverage.</p>
            <div className="portal-grid">
              {policies.length ? (
                policies.map((policy) => (
                  <div key={policy.id} className="portal-card">
                    <div className="portal-pill">{policy.insurance_type}</div>
                    <div className="portal-muted">Coverage</div>
                    <div style={{ fontWeight: 700 }}>{formatCurrency(policy.coverage_amount)}</div>
                    <div className="portal-muted">Premium: {formatCurrency(policy.premium_amount)}</div>
                    <div className="portal-muted">Ends: {policy.end_date}</div>
                  </div>
                ))
              ) : (
                <div className="portal-card">No insurance policies yet.</div>
              )}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
