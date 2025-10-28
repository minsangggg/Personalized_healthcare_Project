import { useEffect, useMemo, useState } from 'react'
import { recipeAPI, type SelectedRecipesResponse } from '../api/recipe'
import './Calendar.css'

type CalendarProps = { isLoggedIn: boolean }
type Row = SelectedRecipesResponse['recipes'][number]

function ymd(d: Date) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return ''
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function firstDayOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}
function lastDayOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0)
}
// 월요일 시작 그리드(총 42칸)
function getCalendarGrid(base: Date) {
  const first = firstDayOfMonth(base)
  const last = lastDayOfMonth(base)
  const firstWeekdayMonStart = ((first.getDay() + 6) % 7) // (월=0~일=6)
  const daysInMonth = last.getDate()

  const cells: Date[] = []
  // 앞 패딩
  for (let i = 0; i < firstWeekdayMonStart; i++) {
    const d = new Date(first)
    d.setDate(first.getDate() - (firstWeekdayMonStart - i))
    cells.push(d)
  }
  // 해당 월
  for (let i = 1; i <= daysInMonth; i++) {
    cells.push(new Date(base.getFullYear(), base.getMonth(), i))
  }
  // 뒤 패딩
  while (cells.length < 42) {
    const d = new Date(cells[cells.length - 1])
    d.setDate(d.getDate() + 1)
    cells.push(d)
  }
  return cells
}

export default function Calendar({ isLoggedIn }: CalendarProps) {
  const [data, setData] = useState<SelectedRecipesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 현재 달/선택 날짜
  const [month, setMonth] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const run = async () => {
      if (!isLoggedIn) { setData(null); return }
      setLoading(true); setError(null)
      try {
        const res = await recipeAPI.getSelected()
        if (alive) setData(res)
      } catch (e) {
        console.error('[Calendar] getSelected failed:', e)
        if (alive) setError('기록을 불러오지 못했습니다.')
      } finally {
        if (alive) setLoading(false)
      }
    }
    run()
    return () => { alive = false }
  }, [isLoggedIn])

  // 날짜별 그룹
  const byDate = useMemo(() => {
    const m = new Map<string, Row[]>()
    for (const r of data?.recipes ?? []) {
      const d = (r.selected_date ?? '').slice(0, 10)
      if (!d) continue
      const arr = m.get(d) ?? []
      arr.push(r)
      m.set(d, arr)
    }
    return m
  }, [data])

  const cells = useMemo(() => getCalendarGrid(month), [month])
  const selectedRecipes = selectedDay ? (byDate.get(selectedDay) ?? []) : []

  const now = new Date()
  const todayStr = ymd(now)
  const monthLabel = `${month.getFullYear()}년 ${month.getMonth() + 1}월`
  const isSameMonth = (d: Date) =>
    d.getFullYear() === month.getFullYear() && d.getMonth() === month.getMonth()

  const goPrev = () => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))
  const goNext = () => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))
  const goToday = () => {
    const base = new Date(now.getFullYear(), now.getMonth(), 1)
    setMonth(base)
    setSelectedDay(todayStr)
  }

  return (
    <section className="app-tab cal">
      <div className="card cal-card">
        <div className="cal-header">
          <h2 className="title">요리 기록</h2>
          <div className="cal-controls">
            <button className="btn ghost" onClick={goPrev} aria-label="이전 달">‹</button>
            <div className="month-label">{monthLabel}</div>
            <button className="btn ghost" onClick={goNext} aria-label="다음 달">›</button>
            <button className="btn" onClick={goToday}>오늘</button>
          </div>
        </div>

        {!isLoggedIn && <div className="muted">로그인하면 기록을 볼 수 있어요.</div>}
        {isLoggedIn && loading && <div className="muted">불러오는 중…</div>}
        {isLoggedIn && error && <div className="error">{error}</div>}

        {isLoggedIn && !loading && !error && (
          <>
            {/* 캘린더 */}
            <div className="calendar">
              <div className="week-head">
                {['월','화','수','목','금','토','일'].map((w) => (
                  <div key={w} className="cell head">{w}</div>
                ))}
              </div>
              <div className="weeks">
                {cells.map((d, i) => {
                  const dayStr = ymd(d)
                  const count = dayStr ? (byDate.get(dayStr)?.length ?? 0) : 0
                  const classes = [
                    'cell','day',
                    isSameMonth(d) ? 'cur' : 'dim',
                    dayStr === todayStr ? 'today' : '',
                    count > 0 ? 'has' : '',
                    selectedDay === dayStr ? 'sel' : ''
                  ].join(' ').trim()

                  return (
                    <button
                      key={`${d.getTime()}-${i}`}
                      className={classes}
                      onClick={() => dayStr && setSelectedDay(dayStr)}
                      title={count > 0 ? `${count}개 기록` : undefined}
                    >
                      <span className="dnum">{d.getDate()}</span>
                      {count > 0 && <span className="dot" aria-hidden />}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* 선택 날짜 상세 */}
            {selectedDay && (
              <div className="day-detail">
                <div className="day-head">{selectedDay}의 레시피</div>
                {selectedRecipes.length === 0 ? (
                  <div className="muted small">이 날의 기록이 없어요.</div>
                ) : (
                  <ul className="list">
                    {selectedRecipes.map((r) => (
                      <li key={r.selected_id} className="row">
                        <div className="title clamp-1">{r.title}</div>
                        <div className="meta">
                          {r.difficulty ?? '—'} · {r.cooking_time ?? '—'}분
                        </div>
                        <div className="actions">
                          {/* 안전 내비게이션: 훅 없이 이동 */}
                          <a className="btn sm" href={`/recipes/${r.recipe_id}`}>
                            자세히 보기
                          </a>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {!selectedDay && (data?.count ?? 0) === 0 && (
              <div className="empty">아직 기록이 없습니다. 레시피를 선택해 보세요!</div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
