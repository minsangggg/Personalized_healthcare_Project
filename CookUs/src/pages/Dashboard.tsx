import { useEffect, useMemo, useRef, useState } from 'react'
import './DashboardTab.css'
import {
  getProgress,
  getProgressTrend,
  getLevelWeekly,
  getCategoryMonthly,
  type ProgressStat,
  type ProgressTrend,
  type LevelWeekly,
  type CategoryRow,
} from '../api/stats'

import ReactApexChart from 'react-apexcharts'
import type { ApexOptions } from 'apexcharts'
import servingBattery from '../assets/서빙 건전지.png'

type Props = {
  isLoggedIn: boolean
  onRequireLogin: () => void
  userName?: string
}

export default function Dashboard({ isLoggedIn, onRequireLogin, userName }: Props) {
  if (!isLoggedIn) {
    return (
      <section className="app-tab dashboard">
        <div className="card db-card center">
          <h2 className="title">대시보드</h2>
          <p className="sub">로그인이 필요합니다</p>
          <button className="btn primary" onClick={onRequireLogin}>로그인</button>
        </div>
      </section>
    )
  }
  return <DashboardInner userName={userName} onRequireLogin={onRequireLogin} />
}

function DashboardInner({ userName, onRequireLogin }: { userName?: string; onRequireLogin: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [progress, setProgress] = useState<ProgressStat | null>(null)
  const [trend, setTrend] = useState<ProgressTrend | null>(null)
  const [levelWeekly, setLevelWeekly] = useState<LevelWeekly>([])
  const [categories, setCategories] = useState<CategoryRow[]>([])
  const [month, setMonth] = useState<string>(() => formatMonthInput(new Date()))

  const abortRef = useRef<AbortController | null>(null)
  const selectedDateParam = useMemo(() => monthToParam(month), [month])

  const isCurrentMonth = useMemo(() => {
    if (!month) return true
    const [yy, mm] = month.split('-').map(Number)
    const now = new Date()
    return yy === now.getFullYear() && mm === (now.getMonth() + 1)
  }, [month])

  const [weeklyOpen, setWeeklyOpen] = useState<boolean>(true)
  useEffect(() => { setWeeklyOpen(isCurrentMonth) }, [isCurrentMonth])

  const monthLabel = useMemo(() => {
    if (!month) return '이달'
    const m = Number(month.split('-')[1] || '0')
    return `${m}월`
  }, [month])

  const ymButtonLabel = useMemo(() => {
    const fmt = (y: number, m: number) => `${y}년 ${String(m).padStart(2, '0')}월`
    if (!month) {
      const d = new Date()
      return fmt(d.getFullYear(), d.getMonth() + 1)
    }
    const [yRaw, mRaw] = month.split('-')
    const y = Number(yRaw) || new Date().getFullYear()
    const m = Number(mRaw) || (new Date().getMonth() + 1)
    return fmt(y, m)
  }, [month])

  const currentWeekText = useMemo(() => {
    const now = new Date()
    const day = now.getDay() // 0: Sun ~ 6: Sat
    const mondayOffset = (day + 6) % 7
    const start = new Date(now)
    start.setDate(now.getDate() - mondayOffset)
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    const fmt = (d: Date) => `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
    return `${fmt(start)}–${fmt(end)}`
  }, [])

  // Custom month popup state
  const [monthOpen, setMonthOpen] = useState(false)
  const [viewYear, setViewYear] = useState(() => Number((month || '').split('-')[0] || new Date().getFullYear()))
  const monthWrapRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!monthOpen) return
    const onDoc = (e: MouseEvent) => {
      const wrap = monthWrapRef.current
      if (!wrap) return
      if (!wrap.contains(e.target as Node)) setMonthOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [monthOpen])

  const load = async () => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoading(true); setError(null)
    try {
      const [p, t, lw, cat] = await Promise.all([
        getProgress(ac.signal), // weekly summary = current week
        getProgressTrend(ac.signal, selectedDateParam),
        getLevelWeekly(ac.signal, selectedDateParam),
        getCategoryMonthly(ac.signal, selectedDateParam),
      ])
      if (ac.signal.aborted) return
      setProgress(p)
      setTrend(t)
      setLevelWeekly(lw)
      setCategories(cat)
    } catch (e: any) {
      if (ac.signal.aborted) return
      const status = e?.response?.status
      const msg = e?.response?.data?.detail || e?.message || '대시보드를 불러오지 못했습니다'
      setError(msg)
      if (status === 401) onRequireLogin()
    } finally {
      if (!ac.signal.aborted) setLoading(false)
    }
  }

  useEffect(() => {
    load()
    return () => abortRef.current?.abort()
  }, [selectedDateParam])

  // Chart data
  const weeks = trend?.weeks ?? []
  const weekCats = weeks.map((w: any) => w.week)
  const avgWeekRate = weeks.length
    ? Math.round((weeks.reduce((a: number, b: any) => a + (Number(b.rate) || 0), 0) / weeks.length) * 10) / 10
    : 0
  const monthRateRaw = trend?.monthRate ?? (weeks.length ? avgWeekRate : 0)
  const radialValue = Math.max(0, Math.min(100, Number.isFinite(monthRateRaw) ? Number(monthRateRaw) : 0))

  const lvlSeries = useMemo(() => {
    const toPct = (n: number, t: number) => (t ? Math.round((n / t) * 1000) / 10 : 0)
    const lows: number[] = []
    const highs: number[] = []
    for (const w of levelWeekly as any[]) {
      const low = Number((w as any)['하'] ?? (w as any).low ?? 0)
      const high = Number((w as any)['상'] ?? (w as any).high ?? 0)
      const t = Number((w as any).total ?? (low + high))
      lows.push(toPct(low, t))
      highs.push(toPct(high, t))
    }
    return [
      { name: '하', data: lows },
      { name: '상', data: highs },
    ]
  }, [levelWeekly])

  const donutCounts = categories.map(c => Number(c.count || 0))
  const donutByRatio = categories.map(c => Math.round(((c.ratio ?? 0) * 1000)) / 10)
  const donutSeriesRaw = (donutCounts.reduce((a, b) => a + b, 0) > 0) ? donutCounts : donutByRatio
  const donutLabelsRaw = categories.map(c => c.label)
  const donutTotal = donutSeriesRaw.reduce((a, b) => a + Number(b || 0), 0)
  const donutSeries = donutTotal > 0 ? donutSeriesRaw : [100]
  const donutLabels = donutTotal > 0 ? donutLabelsRaw : ['데이터 없음']

  const optsLine: ApexOptions = {
    chart: { type: 'area', toolbar: { show: false }, foreColor: '#3b2a1d' },
    stroke: { curve: 'smooth', width: 3, colors: ['#F39C3A'] },
    fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.02, stops: [0, 90, 100] } },
    dataLabels: { enabled: false },
    grid: { borderColor: '#e9e2d8', strokeDashArray: 4 },
    xaxis: {
      categories: weekCats,
      tickPlacement: 'between',
      axisBorder: { show: false },
      axisTicks: { show: false },
      labels: { rotate: -10, offsetY: 2, style: { fontSize: '11px' } },
    },
    yaxis: { max: 100, min: 0, decimalsInFloat: 0, axisBorder: { show: false }, axisTicks: { show: false }, labels: { formatter: (v) => `${Math.round(Number(v))}%` } },
    tooltip: { y: { formatter: (v) => `${Math.round(Number(v))}%` } },
    markers: { size: 3 },
    annotations: { yaxis: [{ y: 100, strokeDashArray: 6, borderColor: '#c9c7c2', label: { text: '목표 100%', style: { background: '#f3dc93', color: '#3b2a1d' } } }] },
    noData: { text: '데이터 없음' },
  }
  const seriesLine = [{ name: '달성률', type: 'line' as const, data: weeks.map((w: any) => Math.min(100, Math.max(0, Number(w.rate) || 0))) }]

  const optsStack: ApexOptions = {
    chart: { type: 'bar', stacked: true, stackType: '100%', toolbar: { show: false }, foreColor: '#3b2a1d' },
    plotOptions: { bar: { horizontal: false, columnWidth: '38%', borderRadius: 6 } },
    dataLabels: { enabled: false },
    // 두 시리즈(하, 상) 색상만 사용
    colors: ['#9FD3C7', '#8C7AE6'],
    grid: { borderColor: '#e9e2d8', strokeDashArray: 4 },
    xaxis: { categories: (levelWeekly as any[]).map((w: any) => w.week), labels: { rotate: -10, offsetY: 2, style: { fontSize: '11px' } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { max: 100, min: 0, decimalsInFloat: 0, labels: { formatter: (v) => `${Math.round(Number(v))}%` }, axisBorder: { show: false }, axisTicks: { show: false } },
    tooltip: { y: { formatter: (v) => `${Math.round(Number(v))}%` } },
    legend: { position: 'bottom' },
    noData: { text: '데이터 없음' },
  }

  const optsDonut: ApexOptions = {
    chart: { type: 'donut', foreColor: '#3b2a1d' },
    labels: donutLabels,
    colors: ['#F39C3A', '#9FD3C7', '#F8CF61', '#8C7AE6', '#FF9AA2'],
    legend: { position: 'bottom' },
    plotOptions: {
      pie: { donut: { size: '60%', labels: { show: true, total: { show: true, label: '총 건수', formatter: () => donutTotal > 0 ? `${donutTotal}건` : '데이터 없음' }, value: { formatter: (v) => `${Math.round(Number(v))}건` } } } },
    },
    dataLabels: { enabled: false },
    tooltip: { y: { formatter: (v: number) => { const total = donutSeries.reduce((a, b) => a + Number(b || 0), 0); if (total <= 0) return '데이터 없음'; const count = Number(v) || 0; const pct = Math.round((count / total) * 100); return `${pct}% (${count}건)` } } },
    noData: { text: '데이터 없음' },
  }

  const weeklyRatePct = clampPercent(progress?.weeklyRate)

  return (
    <section className="app-tab dashboard">
      <div className="db-header">
        <h2 className="title">{userName ? `${userName}님의 대시보드` : '대시보드'}</h2>
        <div className="db-actions">
          <div className="month-wrap" ref={monthWrapRef}>
            <button
              type="button"
              className="month-picker-btn"
              aria-haspopup="dialog"
              aria-expanded={monthOpen}
              onClick={() => { setViewYear(Number((month || '').split('-')[0] || new Date().getFullYear())); setMonthOpen(v => !v) }}
            >
              {ymButtonLabel}
            </button>
            {monthOpen && (
              <div className="month-popup" role="dialog" aria-label="월 선택">
                <div className="month-nav">
                  <button className="nav-btn" onClick={() => setViewYear(y => y - 1)} aria-label="이전 연도">‹</button>
                  <div className="year">{viewYear}년</div>
                  <button className="nav-btn" onClick={() => setViewYear(y => y + 1)} aria-label="다음 연도">›</button>
                </div>
                <div className="month-grid">
                  {Array.from({ length: 12 }).map((_, i) => {
                    const m = i + 1
                    const ym = `${viewYear}-${String(m).padStart(2, '0')}`
                    const isSel = month === ym
                    return (
                      <button key={m} className={`mcell ${isSel ? 'sel' : ''}`} onClick={() => { setMonth(ym); setMonthOpen(false) }}>
                        {m}월
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
          <button className="btn ghost" onClick={load} disabled={loading} style={{ marginLeft: 8 }}>새로고침</button>
        </div>
      </div>

      {error && (<div className="error" role="alert">{error}</div>)}

      {!isCurrentMonth && (
        <div className="weekly-toggle">
          <button className="btn ghost small" onClick={() => setWeeklyOpen(v => !v)}>
            {weeklyOpen ? '이번주 요약 접기' : '이번주 요약 보기'}
          </button>
        </div>
      )}

      {weeklyOpen && (
        <div className="weekly-sticky">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <div className="sec-title" style={{ margin: 0 }}>현재 주 <span style={{ opacity: .7, fontWeight: 500 }}>({currentWeekText})</span></div>
          </div>
          <div className="weekly-grid kpi-grid">
            <div className="kpi-card"><div className="kpi-label">주간 목표달성</div><div className="kpi-big">{weeklyRatePct != null ? `${weeklyRatePct}%` : '-'}</div></div>
            <div className="kpi-card"><div className="kpi-label">조리 수</div><div className="kpi-big">{progress && progress.cookedCount != null ? progress.cookedCount : '-'}</div></div>
            <div className="kpi-card"><div className="kpi-label">평균 난이도</div><div className="kpi-big">{diffText(progress?.avgDifficulty)}</div></div>
            <div className="kpi-card"><div className="kpi-label">평균 시간</div><div className="kpi-big">{progress && progress.avgMinutes != null ? `${progress.avgMinutes}` : '-'}분</div></div>
          </div>
        </div>
      )}

      {/* Runner gauge */}
      <div className="grid one">
        <div className="card chart-card gauge-card">
          <div className="gauge-header">
            <h3 className="sec-title">{monthLabel} 목표 달성률</h3>
            <RunnerGauge value={radialValue} />
          </div>
        </div>
      </div>

      <div className="grid one">
        <div className="card chart-card">
          <h3 className="sec-title">{monthLabel} 주차별 목표 달성률 추이</h3>
          <div style={{ height: 260 }}>
            <ReactApexChart key={`line-${weeks.map((w: any) => w.rate).join('-')}`} options={optsLine} series={seriesLine} type="line" height={260} />
          </div>
        </div>

        <div className="card chart-card">
          <h3 className="sec-title">{monthLabel} 주별 난이도별 조리 비율</h3>
          <div style={{ height: 260 }}>
            <ReactApexChart options={optsStack} series={lvlSeries} type="bar" height={260} />
          </div>
        </div>
      </div>

      <div className="grid one">
        <div className="card chart-card">
          <h3 className="sec-title">{monthLabel} 카테고리 비율 (Top 5)</h3>
          <div style={{ height: 240 }}>
            <ReactApexChart key={`donut-${donutSeries.join('-')}`} options={optsDonut} series={donutSeries} type="donut" height={240} />
          </div>
        </div>
      </div>
    </section>
  )
}

function diffText(d?: number | string | null) {
  if (d == null) return '-'
  const map: Record<string, number> = { '하': 1, '중': 2, '상': 3 }
  const n = typeof d === 'string' ? (map[d] ?? Number(d)) : d
  const v = Number(n)
  if (!Number.isFinite(v)) return '-'
  // 이 프로젝트에서는 난이도에서 '중'을 사용하지 않으므로 이진 표기
  return v < 2 ? '하' : '상'
}

function formatMonthInput(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

function monthToParam(mm: string | undefined) {
  if (!mm) return undefined
  if (/^\d{4}-\d{2}$/.test(mm)) return `${mm}-01`
  return undefined
}

function clampPercent(value: number | string | null | undefined) {
  if (value == null) return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  return Math.max(0, Math.min(100, Math.round(num)))
}

function RunnerGauge({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
  const rabbitLeft = pct <= 2 ? 0 : pct >= 98 ? 'calc(100% - 32px)' : `calc(${pct}% - 16px)`
  return (
    <div className="runner-gauge" aria-label={`목표 달성률 ${pct}%`}>
      <div className="runner-track">
        <div className="runner-fill" style={{ width: `${pct}%` }} />
        <div className="runner-rabbit" style={{ left: rabbitLeft }} aria-hidden>
          <img src={servingBattery} alt="달리는 마스코트" />
        </div>
        <span className="runner-pct">{pct}%</span>
      </div>
    </div>
  )
}
