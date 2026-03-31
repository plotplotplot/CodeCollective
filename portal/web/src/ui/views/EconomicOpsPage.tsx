import { useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent, type PointerEvent } from 'react'
import { useAuth } from '../../app/AppProviders'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'

const ORG_API_BASE = '/api/org'

type MoneySupplyPoint = {
  timestamp: string
  total_supply: number
}

type MoneySupplyHistory = {
  points: MoneySupplyPoint[]
  current_total_supply: number
  currency: string
}

type AccountSummary = {
  id: string
  name: string
  email: string
  entity_type: string
  balance: number
  created_at: string
}

type RecentTransaction = {
  id: string
  timestamp: string
  transaction_type: string
  amount: number
  currency: string
  description: string
  from_account_id?: string | null
  to_account_id?: string | null
  from_account_name?: string | null
  to_account_name?: string | null
}

type UbiRuntimeSettings = {
  interval_seconds: number
  dena_annual: number
  dena_precision: number
  entity_types: string[]
  updated_at?: string
  updated_by?: string | null
}

type UbiEligibility = {
  is_eligible: boolean
  payment_due?: boolean
  estimated_amount?: number
  next_payment_date?: string
  last_payment_amount?: number
  total_payments_received?: number
  reason?: string
}

const HOUR_MS = 60 * 60 * 1000
const DAY_MS = 24 * HOUR_MS
const YEAR_MS = 365 * DAY_MS
const MIN_TIMEFRAME_MS = HOUR_MS
const MAX_TIMEFRAME_MS = 5 * YEAR_MS
const DEFAULT_TIMEFRAME_MS = 30 * DAY_MS

const TIMEFRAME_PRESETS: Array<{ label: string; durationMs: number }> = [
  { label: '1D', durationMs: DAY_MS },
  { label: '1W', durationMs: 7 * DAY_MS },
  { label: '1M', durationMs: 30 * DAY_MS },
  { label: '1Y', durationMs: YEAR_MS },
  { label: '3Y', durationMs: 3 * YEAR_MS },
  { label: '5Y', durationMs: 5 * YEAR_MS },
]

const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
const axisDateFormat = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
const tooltipDateFormat = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
const CHART_WIDTH = 760
const CHART_HEIGHT = 320
const CHART_MARGIN_TOP = 20
const CHART_MARGIN_RIGHT = 24
const CHART_MARGIN_BOTTOM = 52
const CHART_MARGIN_LEFT = 88
const CHART_TARGET_SAMPLES = 1400

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : fallback
}

function resampleHistory(points: MoneySupplyPoint[], targetSamples: number): MoneySupplyPoint[] {
  if (points.length <= 2 || points.length >= targetSamples) return points
  const lastIndex = points.length - 1
  const samples: MoneySupplyPoint[] = []
  for (let i = 0; i < targetSamples; i += 1) {
    const t = (i / (targetSamples - 1)) * lastIndex
    const left = Math.floor(t)
    const leftPoint = points[left]

    samples.push({
      timestamp: leftPoint.timestamp,
      total_supply: toFiniteNumber(leftPoint.total_supply),
    })
  }
  return samples
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
    let message = text
    if (text) {
      try {
        const parsed = JSON.parse(text) as { detail?: string }
        if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
          message = parsed.detail
        }
      } catch {
        // Keep raw response text when it is not JSON.
      }
    }
    throw new Error(message || `Request failed (${resp.status} ${resp.statusText})`)
  }
  return (await resp.json()) as T
}

export function EconomicOpsPage() {
  const { token } = useAuth()
  const [history, setHistory] = useState<MoneySupplyPoint[]>([])
  const [currency, setCurrency] = useState<string>('DEM')
  const [currentSupply, setCurrentSupply] = useState<number | null>(null)
  const [accounts, setAccounts] = useState<AccountSummary[]>([])
  const [adminAccounts, setAdminAccounts] = useState<AccountSummary[]>([])
  const [recentTransactions, setRecentTransactions] = useState<RecentTransaction[]>([])
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [sortDirection, setSortDirection] = useState<'desc' | 'asc'>('desc')
  const [timeframeMs, setTimeframeMs] = useState<number>(DEFAULT_TIMEFRAME_MS)
  const [activePresetLabel, setActivePresetLabel] = useState<string>('1M')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [ubiSettings, setUbiSettings] = useState<UbiRuntimeSettings | null>(null)
  const [ubiSettingsForm, setUbiSettingsForm] = useState({
    interval_seconds: '60',
    dena_annual: '1',
    dena_precision: '6',
    entity_types: 'individual',
  })
  const [ubiSettingsStatus, setUbiSettingsStatus] = useState<string>('')
  const [ubiEligibility, setUbiEligibility] = useState<UbiEligibility | null>(null)
  const [ubiEligibilityStatus, setUbiEligibilityStatus] = useState<string>('')
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(null)
  const dragZoomStateRef = useRef<{ active: boolean; lastY: number }>({ active: false, lastY: 0 })

  useEffect(() => {
    if (!token) {
      setError('Sign in required to view circulation and account data.')
      setHistory([])
      setAccounts([])
      setAdminAccounts([])
      setRecentTransactions([])
      setCurrentSupply(null)
      setUbiSettings(null)
      setUbiEligibility(null)
      setUbiSettingsStatus('')
      setUbiEligibilityStatus('')
      return
    }

    let cancelled = false
    const headers = { Authorization: `Bearer ${token}` }

    const loadData = () => {
      setIsLoading(true)
      Promise.allSettled([
        orgFetch<MoneySupplyHistory>('/api/system/money-supply/history?days=1825&bucket=day', { headers }),
        orgFetch<AccountSummary[]>('/api/accounts?limit=2000&sort=balance_desc', { headers }),
        orgFetch<AccountSummary[]>('/api/admin/accounts', { headers }),
        orgFetch<RecentTransaction[]>('/api/transactions/recent?limit=10', { headers }),
        orgFetch<UbiRuntimeSettings>('/api/ubi/settings', { headers }),
      ])
        .then(([historyResult, accountsResult, adminsResult, recentTxResult, ubiSettingsResult]) => {
          if (cancelled) return

          if (historyResult.status === 'fulfilled') {
            const historyData = historyResult.value
            const sortedPoints = [...(historyData.points ?? [])].sort(
              (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
            )
            setHistory(sortedPoints)
            setCurrency(historyData.currency || 'DEM')
            setCurrentSupply(historyData.current_total_supply ?? null)
          } else {
            setHistory([])
            setCurrentSupply(null)
          }

          if (accountsResult.status === 'fulfilled') {
            setAccounts(Array.isArray(accountsResult.value) ? accountsResult.value : [])
          } else {
            setAccounts([])
          }

          if (adminsResult.status === 'fulfilled') {
            setAdminAccounts(Array.isArray(adminsResult.value) ? adminsResult.value : [])
          } else {
            setAdminAccounts([])
          }

          if (recentTxResult.status === 'fulfilled') {
            setRecentTransactions(Array.isArray(recentTxResult.value) ? recentTxResult.value : [])
          } else {
            setRecentTransactions([])
          }

          if (ubiSettingsResult.status === 'fulfilled') {
            const data = ubiSettingsResult.value
            setUbiSettings(data)
            setUbiSettingsForm({
              interval_seconds: String(data.interval_seconds ?? 60),
              dena_annual: String(data.dena_annual ?? 1),
              dena_precision: String(data.dena_precision ?? 6),
              entity_types: Array.isArray(data.entity_types) ? data.entity_types.join(', ') : 'individual',
            })
            setUbiSettingsStatus('')
          } else {
            setUbiSettings(null)
            setUbiSettingsStatus('UBI settings unavailable.')
          }

          setUbiEligibility(null)
          setUbiEligibilityStatus('Click "Check my eligibility" to load your personal UBI status.')

          if (historyResult.status === 'rejected' && accountsResult.status === 'rejected' && adminsResult.status === 'rejected') {
            const message =
              historyResult.reason instanceof Error
                ? historyResult.reason.message
                : accountsResult.reason instanceof Error
                  ? accountsResult.reason.message
                  : adminsResult.reason instanceof Error
                    ? adminsResult.reason.message
                    : 'Failed to load economic operations data'
            setError(message)
            return
          }

          if (historyResult.status === 'rejected') {
            const message =
              historyResult.reason instanceof Error ? historyResult.reason.message : 'Failed to load circulation history'
            setError(`Circulation chart unavailable: ${message}`)
            return
          }

          if (accountsResult.status === 'rejected') {
            const message = accountsResult.reason instanceof Error ? accountsResult.reason.message : 'Failed to load user list'
            setError(`User list unavailable: ${message}`)
            return
          }

          if (adminsResult.status === 'rejected') {
            const message = adminsResult.reason instanceof Error ? adminsResult.reason.message : 'Failed to load admin list'
            setError(`Admin list unavailable: ${message}`)
            return
          }

          setError(null)
        })
        .finally(() => {
          if (!cancelled) setIsLoading(false)
        })
    }

    loadData()
    const refreshId = window.setInterval(loadData, 30000)

    return () => {
      cancelled = true
      window.clearInterval(refreshId)
    }
  }, [token])

  const visibleHistory = useMemo(() => {
    if (!history.length) return []
    const now = Date.now()
    const start = now - timeframeMs
    const firstInRange = history.findIndex((point) => new Date(point.timestamp).getTime() >= start)
    if (firstInRange <= 0) return history
    return history.slice(firstInRange - 1)
  }, [history, timeframeMs])

  const chartModel = useMemo(() => {
    const normalizedHistory = visibleHistory.map((point) => ({
      timestamp: point.timestamp,
      total_supply: toFiniteNumber(point.total_supply),
    }))
    const sampledHistory = resampleHistory(normalizedHistory, CHART_TARGET_SAMPLES)
    const plotWidth = CHART_WIDTH - CHART_MARGIN_LEFT - CHART_MARGIN_RIGHT
    const plotHeight = CHART_HEIGHT - CHART_MARGIN_TOP - CHART_MARGIN_BOTTOM
    if (sampledHistory.length < 2) {
      return {
        points: [] as Array<MoneySupplyPoint & { x: number; y: number }>,
        path: '',
        yTicks: [] as Array<{ y: number; value: number }>,
        xTicks: [] as Array<{ x: number; label: string }>,
        minVal: null as number | null,
        maxVal: null as number | null,
        plotWidth,
        plotHeight,
      }
    }

    const values = sampledHistory.map((point) => point.total_supply)
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const range = maxVal - minVal || 1

    const points = sampledHistory.map((point, index) => {
      const x = CHART_MARGIN_LEFT + (index / (sampledHistory.length - 1 || 1)) * plotWidth
      const y = CHART_MARGIN_TOP + (1 - (toFiniteNumber(point.total_supply) - minVal) / range) * plotHeight
      return { ...point, x, y }
    }).filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))

    const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`).join(' ')
    if (points.length < 2 || path.includes('NaN')) {
      return {
        points: [] as Array<MoneySupplyPoint & { x: number; y: number }>,
        path: '',
        yTicks: [] as Array<{ y: number; value: number }>,
        xTicks: [] as Array<{ x: number; label: string }>,
        minVal: null as number | null,
        maxVal: null as number | null,
        plotWidth,
        plotHeight,
      }
    }
    const yTicks = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4
      return {
        y: CHART_MARGIN_TOP + ratio * plotHeight,
        value: maxVal - ratio * range,
      }
    })
    const xTickCount = Math.min(6, Math.max(3, Math.floor(plotWidth / 120)))
    const xTicks = Array.from({ length: xTickCount }, (_, index) => {
      const ratio = xTickCount === 1 ? 0 : index / (xTickCount - 1)
      const pointIndex = Math.round(ratio * (points.length - 1))
      const point = points[pointIndex]
      return {
        x: point.x,
        label: axisDateFormat.format(new Date(point.timestamp)),
      }
    })

    return { points, path, yTicks, xTicks, minVal, maxVal, plotWidth, plotHeight }
  }, [visibleHistory])

  const visibleMin = useMemo(() => chartModel.minVal, [chartModel.minVal])
  const visibleMax = useMemo(() => chartModel.maxVal, [chartModel.maxVal])

  const applyChartZoom = (deltaY: number) => {
    const zoomScale = Math.exp(deltaY * 0.0015)
    setTimeframeMs((prev) => clamp(prev * zoomScale, MIN_TIMEFRAME_MS, MAX_TIMEFRAME_MS))
    setActivePresetLabel('')
  }

  const hoveredPoint = useMemo(() => {
    if (hoveredPointIndex === null) return null
    return chartModel.points[hoveredPointIndex] ?? null
  }, [chartModel.points, hoveredPointIndex])

  const onChartMouseMove = (event: MouseEvent<SVGRectElement>) => {
    if (!chartModel.points.length) return
    const rect = event.currentTarget.getBoundingClientRect()
    const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1)
    const pointCount = chartModel.points.length
    const approxIndex = Math.round(ratio * (pointCount - 1))
    setHoveredPointIndex(clamp(approxIndex, 0, pointCount - 1))
  }

  const onChartMouseLeave = () => {
    setHoveredPointIndex(null)
  }

  const onChartPointerDown = (event: PointerEvent<SVGRectElement>) => {
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    dragZoomStateRef.current = { active: true, lastY: event.clientY }
  }

  const onChartPointerMove = (event: PointerEvent<SVGRectElement>) => {
    if (!dragZoomStateRef.current.active) return
    event.preventDefault()
    const deltaY = event.clientY - dragZoomStateRef.current.lastY
    if (Math.abs(deltaY) >= 1) {
      applyChartZoom(deltaY * 4)
      dragZoomStateRef.current.lastY = event.clientY
    }
  }

  const stopChartPointerDrag = (event: PointerEvent<SVGRectElement>) => {
    if (!dragZoomStateRef.current.active) return
    event.preventDefault()
    dragZoomStateRef.current.active = false
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const filteredAccounts = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase()
    const filtered = accounts.filter((account) => {
      if (!needle) return true
      return account.name.toLowerCase().includes(needle) || account.email.toLowerCase().includes(needle)
    })

    return filtered.sort((a, b) => {
      const delta = (a.balance ?? 0) - (b.balance ?? 0)
      return sortDirection === 'asc' ? delta : -delta
    })
  }, [accounts, searchTerm, sortDirection])

  const filteredAdminAccounts = useMemo(() => {
    const needle = searchTerm.trim().toLowerCase()
    const filtered = adminAccounts.filter((account) => {
      if (!needle) return true
      return account.name.toLowerCase().includes(needle) || account.email.toLowerCase().includes(needle)
    })

    return filtered.sort((a, b) => {
      const delta = (a.balance ?? 0) - (b.balance ?? 0)
      return sortDirection === 'asc' ? delta : -delta
    })
  }, [adminAccounts, searchTerm, sortDirection])

  const adminIdSet = useMemo(() => new Set(adminAccounts.map((account) => account.id)), [adminAccounts])

  const filteredNonAdminAccounts = useMemo(
    () => filteredAccounts.filter((account) => !adminIdSet.has(account.id)),
    [filteredAccounts, adminIdSet],
  )

  async function refreshUbiSettings() {
    if (!token) return
    try {
      const data = await orgFetch<UbiRuntimeSettings>('/api/ubi/settings', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setUbiSettings(data)
      setUbiSettingsForm({
        interval_seconds: String(data.interval_seconds ?? 60),
        dena_annual: String(data.dena_annual ?? 1),
        dena_precision: String(data.dena_precision ?? 6),
        entity_types: Array.isArray(data.entity_types) ? data.entity_types.join(', ') : 'individual',
      })
      setUbiSettingsStatus('UBI settings refreshed.')
    } catch (err) {
      setUbiSettingsStatus(err instanceof Error ? err.message : 'Failed to refresh UBI settings.')
    }
  }

  async function submitUbiSettings(event: FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      const payload = {
        interval_seconds: Number(ubiSettingsForm.interval_seconds),
        dena_annual: Number(ubiSettingsForm.dena_annual),
        dena_precision: Number(ubiSettingsForm.dena_precision),
        entity_types: ubiSettingsForm.entity_types
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      }
      const data = await orgFetch<UbiRuntimeSettings>('/api/ubi/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
      setUbiSettings(data)
      setUbiSettingsStatus('UBI settings updated.')
    } catch (err) {
      setUbiSettingsStatus(err instanceof Error ? err.message : 'Failed to update UBI settings.')
    }
  }

  async function checkUbiEligibility() {
    if (!token) return
    try {
      const data = await orgFetch<UbiEligibility>('/api/ubi/eligibility', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setUbiEligibility(data)
      setUbiEligibilityStatus('Eligibility refreshed.')
    } catch (err) {
      setUbiEligibilityStatus(err instanceof Error ? err.message : 'Failed to load eligibility.')
    }
  }

  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero">
            <div>
              <span className="portal-pill">Economic Operations</span>
              <h1>Dena circulation + account directory</h1>
              <p className="portal-muted">
                Global supply trend over time and a searchable user ledger sorted by Dena balance.
              </p>
              {error && <p className="portal-muted">{error}</p>}
              <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                <a
                  href="/send"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 20px',
                    borderRadius: 999,
                    backgroundColor: 'var(--primary)',
                    color: '#fff',
                    textDecoration: 'none',
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm8-4a1 1 0 00-1 1v3H6a1 1 0 100 2h3v3a1 1 0 102 0v-3h3a1 1 0 100-2h-3V7a1 1 0 00-1-1z" />
                  </svg>
                  Send Dena
                </a>
                <a
                  href="/receive"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 20px',
                    borderRadius: 999,
                    border: '1px solid var(--border)',
                    backgroundColor: 'transparent',
                    color: 'var(--text-primary)',
                    textDecoration: 'none',
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clipRule="evenodd" />
                  </svg>
                  Receive Dena
                </a>
              </div>
            </div>
            <div className="portal-card portal-chart-card">
              <div className="portal-muted">Current Dena in circulation</div>
              <div style={{ fontSize: '2rem', fontWeight: 700 }}>{formatCurrency(currentSupply, currency)}</div>
              <div className="portal-muted">Accounts indexed: {formatNumber(accounts.length)}</div>
              <div className="portal-muted">Admins indexed: {formatNumber(adminAccounts.length)}</div>
            </div>
          </section>

          <section className="portal-section" id="circulation">
            <div className="portal-section-header">
              <h2>Dena in circulation over time</h2>
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
            <div className="portal-card">
              {visibleHistory.length < 2 ? (
                <p className="portal-muted">{isLoading ? 'Loading circulation history...' : 'No circulation history available yet.'}</p>
              ) : (
                <>
                  <svg
                    viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                    width="100%"
                    height="320"
                    role="img"
                    aria-label="Dena circulation history chart"
                    onMouseLeave={onChartMouseLeave}
                    style={{ cursor: 'crosshair' }}
                  >
                    <rect
                      x={CHART_MARGIN_LEFT}
                      y={CHART_MARGIN_TOP}
                      width={chartModel.plotWidth}
                      height={chartModel.plotHeight}
                      fill="#f8fbff"
                    />

                    {chartModel.yTicks.map((tick) => (
                      <g key={`y-${tick.y}`}>
                        <line
                          x1={CHART_MARGIN_LEFT}
                          y1={tick.y}
                          x2={CHART_WIDTH - CHART_MARGIN_RIGHT}
                          y2={tick.y}
                          stroke="rgba(11, 26, 51, 0.12)"
                          strokeDasharray="3 4"
                        />
                        <text
                          x={CHART_MARGIN_LEFT - 10}
                          y={tick.y + 4}
                          textAnchor="end"
                          fontSize="12"
                          fill="rgba(11, 26, 51, 0.72)"
                        >
                          {formatNumber(tick.value)}
                        </text>
                      </g>
                    ))}

                    {chartModel.xTicks.map((tick) => (
                      <g key={`x-${tick.x}`}>
                        <line
                          x1={tick.x}
                          y1={CHART_MARGIN_TOP}
                          x2={tick.x}
                          y2={CHART_HEIGHT - CHART_MARGIN_BOTTOM}
                          stroke="rgba(11, 26, 51, 0.08)"
                        />
                        <text
                          x={tick.x}
                          y={CHART_HEIGHT - CHART_MARGIN_BOTTOM + 18}
                          textAnchor="middle"
                          fontSize="11"
                          fill="rgba(11, 26, 51, 0.72)"
                        >
                          {tick.label}
                        </text>
                      </g>
                    ))}

                    <line
                      x1={CHART_MARGIN_LEFT}
                      y1={CHART_MARGIN_TOP}
                      x2={CHART_MARGIN_LEFT}
                      y2={CHART_HEIGHT - CHART_MARGIN_BOTTOM}
                      stroke="rgba(11, 26, 51, 0.4)"
                    />
                    <line
                      x1={CHART_MARGIN_LEFT}
                      y1={CHART_HEIGHT - CHART_MARGIN_BOTTOM}
                      x2={CHART_WIDTH - CHART_MARGIN_RIGHT}
                      y2={CHART_HEIGHT - CHART_MARGIN_BOTTOM}
                      stroke="rgba(11, 26, 51, 0.4)"
                    />

                    <path d={chartModel.path} fill="none" stroke="#0b1a33" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />

                    {/* Transparent overlay for hover + drag-to-zoom interactions. */}
                    <rect
                      x={CHART_MARGIN_LEFT}
                      y={CHART_MARGIN_TOP}
                      width={chartModel.plotWidth}
                      height={chartModel.plotHeight}
                      className="portal-chart-overlay"
                      fill="transparent"
                      onMouseMove={onChartMouseMove}
                      onPointerDown={onChartPointerDown}
                      onPointerMove={onChartPointerMove}
                      onPointerUp={stopChartPointerDrag}
                      onPointerCancel={stopChartPointerDrag}
                    />

                    {hoveredPoint && (
                      <>
                        <line
                          x1={hoveredPoint.x}
                          y1={CHART_MARGIN_TOP}
                          x2={hoveredPoint.x}
                          y2={CHART_HEIGHT - CHART_MARGIN_BOTTOM}
                          stroke="#16305e"
                          strokeWidth="1.5"
                          strokeDasharray="4 4"
                        />
                        <circle cx={hoveredPoint.x} cy={hoveredPoint.y} r="4.5" fill="#16305e" />
                        <g
                          transform={`translate(${Math.min(
                            CHART_WIDTH - CHART_MARGIN_RIGHT - 190,
                            hoveredPoint.x + 10,
                          )}, ${Math.max(CHART_MARGIN_TOP + 8, hoveredPoint.y - 54)})`}
                        >
                          <rect width="182" height="46" rx="10" fill="#0b1a33" fillOpacity="0.95" />
                          <text x="10" y="18" fontSize="11" fill="#dbe7ff">
                            {tooltipDateFormat.format(new Date(hoveredPoint.timestamp))}
                          </text>
                          <text x="10" y="34" fontSize="13" fill="#ffffff" fontWeight="700">
                            {formatCurrency(hoveredPoint.total_supply, currency)}
                          </text>
                        </g>
                      </>
                    )}

                    {/* Zoom hint rendered when no point is hovered */}
                    {!hoveredPoint && (
                      <text
                        x={CHART_MARGIN_LEFT + chartModel.plotWidth - 8}
                        y={CHART_MARGIN_TOP + 16}
                        textAnchor="end"
                        fontSize="11"
                        fill="rgba(11, 26, 51, 0.35)"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        Scroll to zoom · drag to zoom
                      </text>
                    )}

                    <text
                      x={CHART_MARGIN_LEFT + chartModel.plotWidth / 2}
                      y={CHART_HEIGHT - 8}
                      textAnchor="middle"
                      fontSize="12"
                      fill="rgba(11, 26, 51, 0.75)"
                    >
                      Time
                    </text>
                    <text
                      x="18"
                      y={CHART_MARGIN_TOP + chartModel.plotHeight / 2}
                      transform={`rotate(-90 18 ${CHART_MARGIN_TOP + chartModel.plotHeight / 2})`}
                      textAnchor="middle"
                      fontSize="12"
                      fill="rgba(11, 26, 51, 0.75)"
                    >
                      Total Dena ({currency})
                    </text>
                  </svg>
                  <div className="portal-grid">
                    <div className="portal-card">
                      <div className="portal-muted">Visible min</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{formatCurrency(visibleMin, currency)}</div>
                    </div>
                    <div className="portal-card">
                      <div className="portal-muted">Visible max</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{formatCurrency(visibleMax, currency)}</div>
                    </div>
                    <div className="portal-card">
                      <div className="portal-muted">Latest point</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                        {formatCurrency(visibleHistory[visibleHistory.length - 1]?.total_supply, currency)}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          <section className="portal-section" id="accounts">
            <div className="portal-section-header">
              <h2>UBI options</h2>
              <button type="button" className="portal-timeframe-button" onClick={checkUbiEligibility}>
                Check my eligibility
              </button>
            </div>
            <div className="portal-grid">
              <div className="portal-card">
                <h3>Current UBI status</h3>
                {ubiEligibility ? (
                  <>
                    <p className="portal-muted">Eligible: {ubiEligibility.is_eligible ? 'Yes' : 'No'}</p>
                    <p className="portal-muted">Payment due: {ubiEligibility.payment_due ? 'Yes' : 'No'}</p>
                    <p className="portal-muted">Next payment: {ubiEligibility.next_payment_date ?? '—'}</p>
                    <p className="portal-muted">Estimated amount: {formatCurrency(ubiEligibility.estimated_amount, currency)}</p>
                    <p className="portal-muted">Last payment: {formatCurrency(ubiEligibility.last_payment_amount, currency)}</p>
                    <p className="portal-muted">Total received: {formatCurrency(ubiEligibility.total_payments_received, currency)}</p>
                    {ubiEligibility.reason && <p className="portal-muted">{ubiEligibility.reason}</p>}
                  </>
                ) : (
                  <p className="portal-muted">No eligibility data loaded.</p>
                )}
                {ubiEligibilityStatus && <p className="portal-muted">{ubiEligibilityStatus}</p>}
              </div>
              <form className="portal-card portal-form" onSubmit={submitUbiSettings}>
                <h3>Runtime settings (admin)</h3>
                <label>
                  Interval seconds
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={ubiSettingsForm.interval_seconds}
                    onChange={(event) => setUbiSettingsForm({ ...ubiSettingsForm, interval_seconds: event.target.value })}
                  />
                </label>
                <label>
                  Annual amount
                  <input
                    type="number"
                    min="0"
                    step="0.000001"
                    value={ubiSettingsForm.dena_annual}
                    onChange={(event) => setUbiSettingsForm({ ...ubiSettingsForm, dena_annual: event.target.value })}
                  />
                </label>
                <label>
                  Precision
                  <input
                    type="number"
                    min="0"
                    max="12"
                    step="1"
                    value={ubiSettingsForm.dena_precision}
                    onChange={(event) => setUbiSettingsForm({ ...ubiSettingsForm, dena_precision: event.target.value })}
                  />
                </label>
                <label>
                  Entity types (comma-separated)
                  <input
                    value={ubiSettingsForm.entity_types}
                    onChange={(event) => setUbiSettingsForm({ ...ubiSettingsForm, entity_types: event.target.value })}
                  />
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="submit">Save UBI settings</button>
                  <button type="button" className="secondary" onClick={refreshUbiSettings}>
                    Refresh
                  </button>
                </div>
                {ubiSettings && <p className="portal-muted">Updated by: {ubiSettings.updated_by ?? '—'}</p>}
                {ubiSettingsStatus && <p className="portal-muted">{ubiSettingsStatus}</p>}
              </form>
            </div>
          </section>

          <section className="portal-section" id="transactions">
            <div className="portal-section-header">
              <h2>Last 10 transactions</h2>
            </div>
            <div className="portal-card" style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 860 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Time</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Type</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>From</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>To</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>Amount</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTransactions.map((txn) => (
                    <tr key={txn.id} style={{ borderTop: '1px solid rgba(12, 30, 60, 0.12)' }}>
                      <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>
                        {new Date(txn.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>
                        {String(txn.transaction_type || '').toLowerCase().replaceAll('_', ' ')}
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        {txn.from_account_name || (txn.from_account_id ? `${txn.from_account_id.slice(0, 8)}...` : 'System')}
                      </td>
                      <td style={{ padding: '8px 6px' }}>
                        {txn.to_account_name || (txn.to_account_id ? `${txn.to_account_id.slice(0, 8)}...` : 'System')}
                      </td>
                      <td style={{ padding: '8px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                        {formatCurrency(txn.amount, txn.currency || currency)}
                      </td>
                      <td style={{ padding: '8px 6px' }}>{txn.description || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!isLoading && recentTransactions.length === 0 && <p className="portal-muted">No recent transactions found.</p>}
            </div>
          </section>

          <section className="portal-section" id="accounts">
            <div className="portal-section-header">
              <h2>Users</h2>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Search by name or email"
                  style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid rgba(12, 30, 60, 0.25)', minWidth: 260 }}
                />
                <select
                  value={sortDirection}
                  onChange={(event) => setSortDirection(event.target.value === 'asc' ? 'asc' : 'desc')}
                  style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid rgba(12, 30, 60, 0.25)' }}
                >
                  <option value="desc">Most Dena first</option>
                  <option value="asc">Least Dena first</option>
                </select>
              </div>
            </div>
            <h3 style={{ marginBottom: 10 }}>Admins</h3>
            <div className="portal-card" style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>#</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Name</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Email</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Type</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>Dena</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAdminAccounts.map((account, index) => (
                    <tr key={account.id} style={{ borderTop: '1px solid rgba(12, 30, 60, 0.12)' }}>
                      <td style={{ padding: '8px 6px' }}>{index + 1}</td>
                      <td style={{ padding: '8px 6px', fontWeight: 700 }}>{account.name}</td>
                      <td style={{ padding: '8px 6px' }}>{account.email}</td>
                      <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{account.entity_type}</td>
                      <td style={{ padding: '8px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {formatCurrency(account.balance, currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!isLoading && filteredAdminAccounts.length === 0 && <p className="portal-muted">No admins matched your search.</p>}
            </div>

            <h3 style={{ margin: '18px 0 10px' }}>Non-admin users</h3>
            <div className="portal-card" style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>#</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Name</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Email</th>
                    <th style={{ textAlign: 'left', padding: '8px 6px' }}>Type</th>
                    <th style={{ textAlign: 'right', padding: '8px 6px' }}>Dena</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredNonAdminAccounts.map((account, index) => (
                    <tr key={account.id} style={{ borderTop: '1px solid rgba(12, 30, 60, 0.12)' }}>
                      <td style={{ padding: '8px 6px' }}>{index + 1}</td>
                      <td style={{ padding: '8px 6px', fontWeight: 700 }}>{account.name}</td>
                      <td style={{ padding: '8px 6px' }}>{account.email}</td>
                      <td style={{ padding: '8px 6px', textTransform: 'capitalize' }}>{account.entity_type}</td>
                      <td style={{ padding: '8px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                        {formatCurrency(account.balance, currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!isLoading && filteredNonAdminAccounts.length === 0 && <p className="portal-muted">No users matched your search.</p>}
              {isLoading && <p className="portal-muted">Loading users...</p>}
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
