import { useEffect, useMemo, useState } from 'react'
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

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

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

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  useEffect(() => {
    if (role === 'guest' || !token) return
    let cancelled = false
    async function load() {
      try {
        const [accountData, txData, portfolioData, policyData] = await Promise.all([
          orgFetch<Account>('/api/accounts/me', { headers: authHeaders }),
          orgFetch<Transaction[]>('/api/accounts/me/transactions', { headers: authHeaders }),
          orgFetch<Portfolio>('/api/portfolio', { headers: authHeaders }),
          orgFetch<InsurancePolicy[]>('/api/insurance/policies', { headers: authHeaders }),
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

  const balanceSeries = useMemo<BalancePoint[]>(() => {
    if (!account) return []
    if (!transactions.length) return [{ timestamp: new Date().toISOString(), balance: account.balance }]
    const sorted = [...transactions].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    const deltaFor = (tx: Transaction) => {
      if (tx.to_account_id === account.id) return tx.amount
      if (tx.from_account_id === account.id) return -tx.amount
      return 0
    }
    let startBalance = account.balance
    for (let i = sorted.length - 1; i >= 0; i -= 1) {
      startBalance -= deltaFor(sorted[i])
    }
    let running = startBalance
    const points: BalancePoint[] = []
    for (const tx of sorted) {
      running += deltaFor(tx)
      points.push({ timestamp: tx.timestamp, balance: running })
    }
    return points.slice(-40)
  }, [account, transactions])

  const chartPath = useMemo(() => {
    if (!balanceSeries.length) return ''
    const width = 600
    const height = 180
    const padding = 16
    const values = balanceSeries.map((point) => point.balance)
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const range = maxVal - minVal || 1
    return balanceSeries
      .map((point, index) => {
        const x = padding + (index / (balanceSeries.length - 1 || 1)) * (width - padding * 2)
        const y = height - padding - ((point.balance - minVal) / range) * (height - padding * 2)
        return `${index === 0 ? 'M' : 'L'}${x},${y}`
      })
      .join(' ')
  }, [balanceSeries])

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
            <h2>Balance over time</h2>
            <div className="portal-card">
              {balanceSeries.length === 0 ? (
                <div className="portal-muted">No transactions yet.</div>
              ) : (
                <svg viewBox="0 0 600 180" width="100%" height="200" role="img" aria-label="Balance history">
                  <path d={chartPath} fill="none" stroke="#0b1a33" strokeWidth="2" />
                </svg>
              )}
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
