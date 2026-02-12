import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useAuth } from '../../app/AppProviders'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'

const ORG_API_BASE = '/api/org'

type Metrics = {
  total_accounts?: number
  average_balance?: number
  total_money_supply?: number
  individual_accounts?: number
  business_accounts?: number
  nonprofit_accounts?: number
  total_transactions?: number
  total_transaction_volume?: number
  ubi_payments?: number
  tax_payments?: number
  total_stocks?: number
  total_market_cap?: number
  average_stock_price?: number
  timestamp?: string
  market_open?: boolean
  currency?: string
}

type Stock = {
  id: string
  company_name: string
  ticker_symbol: string
  current_price: number
  day_change: number
  volume: number
  market_cap: number
  sector: string
}

type LogEntry = {
  id: string
  kind: 'system' | 'action' | 'error'
  message: string
}

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

export function EconomicOpsPage() {
  const { role, user, token } = useAuth()
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [stocks, setStocks] = useState<Stock[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])

  const [accountForm, setAccountForm] = useState({
    entity_type: 'individual',
    name: '',
    email: '',
    address: '',
    initial_deposit: '0.00',
  })

  const [transactionForm, setTransactionForm] = useState({
    to_account_id: '',
    amount: '0.00',
    transaction_type: 'purchase',
    description: '',
  })

  const [ubiStatus, setUbiStatus] = useState<string>('')

  const [stockOrderForm, setStockOrderForm] = useState({
    stock_id: '',
    quantity: '1',
    order_type: 'market',
    limit_price: '',
    action: 'buy',
  })

  const [insuranceForm, setInsuranceForm] = useState({
    insurance_type: 'life',
    coverage_amount: '10000',
    duration_years: '1',
    deductible: '0',
  })

  const [fiscalForm, setFiscalForm] = useState({
    title: '',
    description: '',
    policy_area: 'education',
    proposed_budget: '100000',
    duration_months: '12',
    expected_impact: '',
  })

  const [fiscalVoteForm, setFiscalVoteForm] = useState({
    proposal_id: '',
    vote: 'yes',
    rationale: '',
  })

  const [taxForm, setTaxForm] = useState({
    taxable_income: '0',
    tax_year: new Date().getFullYear().toString(),
  })

  const [taxPayForm, setTaxPayForm] = useState({
    record_id: '',
    amount: '0',
  })

  const signedInLabel = useMemo(() => {
    if (role === 'guest' || !user) return 'Sign in required'
    return user.displayName || user.email || 'Signed in'
  }, [role, user])

  const pushLog = (kind: LogEntry['kind'], message: string) => {
    setLogs((prev) => [{ id: crypto.randomUUID(), kind, message }, ...prev].slice(0, 10))
  }

  useEffect(() => {
    let cancelled = false
    orgFetch<Metrics>('/api/system/metrics')
      .then((data) => {
        if (cancelled) return
        setMetrics(data)
        pushLog('system', `Metrics synced. Market open: ${data.market_open}`)
      })
      .catch((err) => {
        if (cancelled) return
        pushLog('error', err instanceof Error ? err.message : 'Failed to load metrics')
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    orgFetch<Stock[]>('/api/stocks')
      .then((data) => {
        if (cancelled) return
        setStocks(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (cancelled) return
        pushLog('error', err instanceof Error ? err.message : 'Failed to load market data')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  async function submitAccount(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        entity_type: accountForm.entity_type,
        name: accountForm.name.trim(),
        email: accountForm.email.trim(),
        address: accountForm.address.trim() || null,
        initial_deposit: Number(accountForm.initial_deposit || 0),
      }
      const response = await orgFetch<{ id: string; name: string }>('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', `Account created: ${response.name} (${response.id})`)
      setAccountForm({ entity_type: 'individual', name: '', email: '', address: '', initial_deposit: '0.00' })
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Account creation failed')
    }
  }

  async function submitTransaction(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        to_account_id: transactionForm.to_account_id || null,
        amount: Number(transactionForm.amount || 0),
        transaction_type: transactionForm.transaction_type,
        description: transactionForm.description,
      }
      const response = await orgFetch<{ id: string }>('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', `Transaction created: ${response.id}`)
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Transaction failed')
    }
  }

  async function fetchUbiEligibility() {
    try {
      const response = await orgFetch<{ is_eligible: boolean; reason?: string; next_payment_date?: string; ubi_amount?: number }>(
        '/api/ubi/eligibility',
        { headers: authHeaders },
      )
      const detail = response.is_eligible
        ? `Eligible. Next payment: ${response.next_payment_date ?? 'unknown'} Amount: ${response.ubi_amount ?? ''}`
        : `Not eligible. ${response.reason ?? ''}`
      setUbiStatus(detail)
      pushLog('action', `UBI check: ${detail}`)
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'UBI check failed')
    }
  }

  async function submitStockOrder(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        stock_id: stockOrderForm.stock_id,
        quantity: Number(stockOrderForm.quantity || 0),
        order_type: stockOrderForm.order_type,
        limit_price: stockOrderForm.limit_price ? Number(stockOrderForm.limit_price) : null,
        action: stockOrderForm.action,
      }
      const response = await orgFetch<{ status: string }>('/api/stocks/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', `Order result: ${response.status}`)
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Order failed')
    }
  }

  async function submitInsurance(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        insurance_type: insuranceForm.insurance_type,
        coverage_amount: Number(insuranceForm.coverage_amount || 0),
        duration_years: Number(insuranceForm.duration_years || 1),
        deductible: Number(insuranceForm.deductible || 0),
      }
      await orgFetch('/api/insurance/policies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', 'Insurance policy created')
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Policy creation failed')
    }
  }

  async function submitFiscalProposal(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        title: fiscalForm.title,
        description: fiscalForm.description,
        policy_area: fiscalForm.policy_area,
        proposed_budget: Number(fiscalForm.proposed_budget || 0),
        duration_months: Number(fiscalForm.duration_months || 0),
        expected_impact: fiscalForm.expected_impact,
      }
      await orgFetch('/api/fiscal/proposals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', 'Fiscal proposal submitted')
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Proposal submission failed')
    }
  }

  async function submitFiscalVote(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        vote: fiscalVoteForm.vote,
        rationale: fiscalVoteForm.rationale || null,
      }
      await orgFetch(`/api/fiscal/proposals/${fiscalVoteForm.proposal_id}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', `Vote recorded on ${fiscalVoteForm.proposal_id}`)
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Vote failed')
    }
  }

  async function submitTaxEstimate(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = {
        taxable_income: Number(taxForm.taxable_income || 0),
        tax_year: Number(taxForm.tax_year || new Date().getFullYear()),
      }
      const response = await orgFetch<{ tax_amount: number; due_date: string; record_id?: string }>('/api/tax/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      pushLog('action', `Tax estimate: ${response.tax_amount}. Due ${response.due_date}`)
      if (response.record_id) {
        setTaxPayForm((prev) => ({ ...prev, record_id: response.record_id }))
      }
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Tax estimate failed')
    }
  }

  async function submitTaxPayment(event: FormEvent) {
    event.preventDefault()
    try {
      const payload = new URLSearchParams({
        record_id: taxPayForm.record_id,
        amount: taxPayForm.amount,
      })
      await orgFetch(`/api/tax/pay?${payload.toString()}`, {
        method: 'POST',
        headers: { ...authHeaders },
      })
      pushLog('action', `Tax payment posted for ${taxPayForm.amount}`)
    } catch (err) {
      pushLog('error', err instanceof Error ? err.message : 'Tax payment failed')
    }
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero" id="overview">
            <div>
              <span className="portal-pill">Org backend control plane</span>
              <h1>Economic operations console</h1>
              <p className="portal-muted">
                Live control and observability for accounts, UBI disbursements, markets, insurance policies, fiscal
                proposals, and tax compliance.
              </p>
            </div>
            <div className="portal-card">
              <div className="portal-grid">
                <div>
                  <div className="portal-muted">Accounts</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{formatNumber(metrics?.total_accounts)}</div>
                </div>
                <div>
                  <div className="portal-muted">Money supply</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                    {formatCurrency(metrics?.total_money_supply, metrics?.currency)}
                  </div>
                </div>
                <div>
                  <div className="portal-muted">Market cap</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                    {formatCurrency(metrics?.total_market_cap, metrics?.currency)}
                  </div>
                </div>
                <div>
                  <div className="portal-muted">Market status</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{metrics?.market_open ? 'Open' : 'Closed'}</div>
                </div>
              </div>
            </div>
          </section>

          <section className="portal-section">
            <div className="portal-grid">
              <div className="portal-card">
                <span className="portal-pill">Operator</span>
                <h3>{signedInLabel}</h3>
                <p className="portal-muted">Sign in required for all write operations.</p>
              </div>
              <div className="portal-card dark">
                <span className="portal-pill">System log</span>
                <div className="portal-log">
                  {logs.length === 0 && <div className="portal-log-entry">No events yet.</div>}
                  {logs.map((entry) => (
                    <div key={entry.id} className="portal-log-entry">
                      {entry.message}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="portal-section" id="accounts">
            <h2>Accounts + UBI</h2>
            <p className="portal-muted">POST /api/accounts · GET /api/ubi/eligibility</p>
            <div className="portal-grid">
              <form className="portal-card portal-form" onSubmit={submitAccount}>
                <label>
                  Entity type
                  <select value={accountForm.entity_type} onChange={(event) => setAccountForm({ ...accountForm, entity_type: event.target.value })}>
                    <option value="individual">Individual</option>
                    <option value="business">Business</option>
                    <option value="nonprofit">Nonprofit</option>
                    <option value="government">Government</option>
                  </select>
                </label>
                <label>
                  Name
                  <input value={accountForm.name} onChange={(event) => setAccountForm({ ...accountForm, name: event.target.value })} required />
                </label>
                <label>
                  Email
                  <input type="email" value={accountForm.email} onChange={(event) => setAccountForm({ ...accountForm, email: event.target.value })} required />
                </label>
                <label>
                  Address
                  <input value={accountForm.address} onChange={(event) => setAccountForm({ ...accountForm, address: event.target.value })} />
                </label>
                <label>
                  Initial deposit
                  <input type="number" min="0" step="0.01" value={accountForm.initial_deposit} onChange={(event) => setAccountForm({ ...accountForm, initial_deposit: event.target.value })} />
                </label>
                <button type="submit">Create account</button>
                <button type="button" className="secondary" onClick={fetchUbiEligibility}>
                  Check UBI eligibility
                </button>
                {ubiStatus && <div className="portal-muted">{ubiStatus}</div>}
              </form>
              <div className="portal-card">
                <h3>Program rules</h3>
                <p className="portal-muted">Individuals auto-enroll in UBI with a 30-day cycle.</p>
                <p className="portal-muted">Businesses and nonprofits receive tax IDs when verified.</p>
                <p className="portal-muted">Edits create audit trails via edit requests.</p>
              </div>
            </div>
          </section>

          <section className="portal-section" id="transactions">
            <h2>Transactions</h2>
            <p className="portal-muted">POST /api/transactions · GET /api/accounts/me/transactions</p>
            <form className="portal-card portal-form" onSubmit={submitTransaction}>
              <label>
                Recipient account ID
                <input value={transactionForm.to_account_id} onChange={(event) => setTransactionForm({ ...transactionForm, to_account_id: event.target.value })} />
              </label>
              <label>
                Amount
                <input type="number" min="0" step="0.01" value={transactionForm.amount} onChange={(event) => setTransactionForm({ ...transactionForm, amount: event.target.value })} />
              </label>
              <label>
                Type
                <select value={transactionForm.transaction_type} onChange={(event) => setTransactionForm({ ...transactionForm, transaction_type: event.target.value })}>
                  <option value="ubi_payment">UBI payment</option>
                  <option value="tax_payment">Tax payment</option>
                  <option value="salary">Salary</option>
                  <option value="purchase">Purchase</option>
                  <option value="investment">Investment</option>
                  <option value="dividend">Dividend</option>
                  <option value="insurance_premium">Insurance premium</option>
                  <option value="insurance_claim">Insurance claim</option>
                  <option value="business_revenue">Business revenue</option>
                  <option value="donation">Donation</option>
                  <option value="grant">Grant</option>
                  <option value="stock_purchase">Stock purchase</option>
                  <option value="stock_sale">Stock sale</option>
                  <option value="interest">Interest</option>
                </select>
              </label>
              <label>
                Description
                <input value={transactionForm.description} onChange={(event) => setTransactionForm({ ...transactionForm, description: event.target.value })} />
              </label>
              <button type="submit">Post transaction</button>
            </form>
          </section>

          <section className="portal-section" id="markets">
            <h2>Markets + Portfolio</h2>
            <p className="portal-muted">GET /api/stocks · POST /api/stocks/orders · GET /api/portfolio</p>
            <div className="portal-grid">
              {stocks.slice(0, 4).map((stock) => (
                <div key={stock.id} className="portal-card">
                  <h3>{stock.ticker_symbol}</h3>
                  <p className="portal-muted">{stock.company_name}</p>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                    {formatCurrency(stock.current_price, metrics?.currency)}
                  </div>
                  <div className="portal-muted">Day change: {formatNumber(stock.day_change)}%</div>
                </div>
              ))}
            </div>
            <form className="portal-card portal-form" onSubmit={submitStockOrder}>
              <label>
                Stock ID
                <input value={stockOrderForm.stock_id} onChange={(event) => setStockOrderForm({ ...stockOrderForm, stock_id: event.target.value })} />
              </label>
              <label>
                Quantity
                <input type="number" min="1" value={stockOrderForm.quantity} onChange={(event) => setStockOrderForm({ ...stockOrderForm, quantity: event.target.value })} />
              </label>
              <label>
                Order type
                <select value={stockOrderForm.order_type} onChange={(event) => setStockOrderForm({ ...stockOrderForm, order_type: event.target.value })}>
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                </select>
              </label>
              <label>
                Limit price (optional)
                <input type="number" min="0" step="0.01" value={stockOrderForm.limit_price} onChange={(event) => setStockOrderForm({ ...stockOrderForm, limit_price: event.target.value })} />
              </label>
              <label>
                Action
                <select value={stockOrderForm.action} onChange={(event) => setStockOrderForm({ ...stockOrderForm, action: event.target.value })}>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </label>
              <button type="submit">Place order</button>
            </form>
          </section>

          <section className="portal-section" id="insurance">
            <h2>Insurance</h2>
            <p className="portal-muted">POST /api/insurance/policies · POST /api/insurance/claims</p>
            <form className="portal-card portal-form" onSubmit={submitInsurance}>
              <label>
                Insurance type
                <select value={insuranceForm.insurance_type} onChange={(event) => setInsuranceForm({ ...insuranceForm, insurance_type: event.target.value })}>
                  <option value="life">Life</option>
                  <option value="health">Health</option>
                  <option value="fire">Fire</option>
                  <option value="acts_of_god">Acts of God</option>
                </select>
              </label>
              <label>
                Coverage amount
                <input type="number" min="0" step="0.01" value={insuranceForm.coverage_amount} onChange={(event) => setInsuranceForm({ ...insuranceForm, coverage_amount: event.target.value })} />
              </label>
              <label>
                Duration (years)
                <input type="number" min="1" max="30" value={insuranceForm.duration_years} onChange={(event) => setInsuranceForm({ ...insuranceForm, duration_years: event.target.value })} />
              </label>
              <label>
                Deductible
                <input type="number" min="0" step="0.01" value={insuranceForm.deductible} onChange={(event) => setInsuranceForm({ ...insuranceForm, deductible: event.target.value })} />
              </label>
              <button type="submit">Issue policy</button>
            </form>
          </section>

          <section className="portal-section" id="policy">
            <h2>Fiscal policy</h2>
            <p className="portal-muted">POST /api/fiscal/proposals · POST /api/fiscal/proposals/:id/vote</p>
            <div className="portal-grid">
              <form className="portal-card portal-form" onSubmit={submitFiscalProposal}>
                <label>
                  Title
                  <input value={fiscalForm.title} onChange={(event) => setFiscalForm({ ...fiscalForm, title: event.target.value })} />
                </label>
                <label>
                  Description
                  <textarea value={fiscalForm.description} onChange={(event) => setFiscalForm({ ...fiscalForm, description: event.target.value })} />
                </label>
                <label>
                  Policy area
                  <select value={fiscalForm.policy_area} onChange={(event) => setFiscalForm({ ...fiscalForm, policy_area: event.target.value })}>
                    <option value="education">Education</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="infrastructure">Infrastructure</option>
                    <option value="defense">Defense</option>
                    <option value="environment">Environment</option>
                    <option value="social_welfare">Social welfare</option>
                    <option value="research">Research</option>
                    <option value="culture">Culture</option>
                  </select>
                </label>
                <label>
                  Proposed budget
                  <input type="number" min="0" step="0.01" value={fiscalForm.proposed_budget} onChange={(event) => setFiscalForm({ ...fiscalForm, proposed_budget: event.target.value })} />
                </label>
                <label>
                  Duration (months)
                  <input type="number" min="1" max="120" value={fiscalForm.duration_months} onChange={(event) => setFiscalForm({ ...fiscalForm, duration_months: event.target.value })} />
                </label>
                <label>
                  Expected impact
                  <textarea value={fiscalForm.expected_impact} onChange={(event) => setFiscalForm({ ...fiscalForm, expected_impact: event.target.value })} />
                </label>
                <button type="submit">Submit proposal</button>
              </form>
              <form className="portal-card portal-form" onSubmit={submitFiscalVote}>
                <label>
                  Proposal ID
                  <input value={fiscalVoteForm.proposal_id} onChange={(event) => setFiscalVoteForm({ ...fiscalVoteForm, proposal_id: event.target.value })} />
                </label>
                <label>
                  Vote
                  <select value={fiscalVoteForm.vote} onChange={(event) => setFiscalVoteForm({ ...fiscalVoteForm, vote: event.target.value })}>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                    <option value="abstain">Abstain</option>
                  </select>
                </label>
                <label>
                  Rationale
                  <textarea value={fiscalVoteForm.rationale} onChange={(event) => setFiscalVoteForm({ ...fiscalVoteForm, rationale: event.target.value })} />
                </label>
                <button type="submit">Submit vote</button>
              </form>
            </div>
          </section>

          <section className="portal-section" id="tax">
            <h2>Tax & compliance</h2>
            <p className="portal-muted">POST /api/tax/calculate · POST /api/tax/pay</p>
            <div className="portal-grid">
              <form className="portal-card portal-form" onSubmit={submitTaxEstimate}>
                <label>
                  Taxable income
                  <input type="number" min="0" step="0.01" value={taxForm.taxable_income} onChange={(event) => setTaxForm({ ...taxForm, taxable_income: event.target.value })} />
                </label>
                <label>
                  Tax year
                  <input type="number" min="2000" value={taxForm.tax_year} onChange={(event) => setTaxForm({ ...taxForm, tax_year: event.target.value })} />
                </label>
                <button type="submit">Calculate</button>
              </form>
              <form className="portal-card portal-form" onSubmit={submitTaxPayment}>
                <label>
                  Record ID
                  <input value={taxPayForm.record_id} onChange={(event) => setTaxPayForm({ ...taxPayForm, record_id: event.target.value })} />
                </label>
                <label>
                  Amount
                  <input type="number" min="0" step="0.01" value={taxPayForm.amount} onChange={(event) => setTaxPayForm({ ...taxPayForm, amount: event.target.value })} />
                </label>
                <button type="submit">Submit payment</button>
              </form>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
