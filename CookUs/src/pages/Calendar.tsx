import { useEffect, useMemo, useState } from 'react'
import { recipeAPI, type SelectedRecipesResponse } from '../api/recipe'
import RecipeDetailModal from '../components/RecipeDetailModal'
import type { Recipe } from '../api/recipe'
import './Calendar.css'

type CalendarProps = { isLoggedIn: boolean }
type Row = SelectedRecipesResponse['recipes'][number]

function ymd(d: Date) {
  if (!(d instanceof Date) || isNaN(d.getTime())) return ''
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function toLocalDate(s?: string | null): Date | null {
  if (!s) return null
  const d = new Date(s)
  if (!isNaN(d.getTime())) return new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const t = String(s).trim().slice(0, 10).replace(/[./]/g, '-')
  const m = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (!m) return null
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

function firstDayOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1) }
function lastDayOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth() + 1, 0) }

function getCalendarGrid(base: Date) {
  const first = firstDayOfMonth(base)
  const last = lastDayOfMonth(base)
  const firstWeekdayMonStart = ((first.getDay() + 6) % 7)
  const daysInMonth = last.getDate()

  const cells: Date[] = []
  for (let i = 0; i < firstWeekdayMonStart; i++) {
    const d = new Date(first)
    d.setDate(first.getDate() - (firstWeekdayMonStart - i))
    cells.push(d)
  }
  for (let i = 1; i <= daysInMonth; i++) {
    cells.push(new Date(base.getFullYear(), base.getMonth(), i))
  }
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

  const [detail, setDetail] = useState<Recipe | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // 삭제 진행 중 표시(선택된 레코드 id)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const refetch = async () => {
    setLoading(true); setError(null)
    try {
      const res = await recipeAPI.getSelected()
      setData(res)
    } catch (e) {
      console.error('[Calendar] getSelected failed:', e)
      setError('기록을 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const openDetail = async (recipeId: number) => {
    setDetailLoading(true)
    try {
      const r = await recipeAPI.getRecipe(recipeId)
      setDetail(r)
    } finally {
      setDetailLoading(false)
    }
  }

  const closeDetail = async () => {
    setDetail(null)
    await refetch()
  }

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

  const monthBuckets = useMemo(() => {
    const map = new Map<number, Row[]>()
    const yy = month.getFullYear()
    const mm = month.getMonth()
    for (const r of data?.recipes ?? []) {
      const d = toLocalDate(r.selected_date)
      if (!d) continue
      if (d.getFullYear() !== yy || d.getMonth() !== mm) continue
      const day = d.getDate()
      const arr = map.get(day) ?? []
      arr.push(r)
      map.set(day, arr)
    }
    return map
  }, [data, month])

  const cells = useMemo(() => getCalendarGrid(month), [month])
  const selectedRecipes = useMemo(() => {
    if (!selectedDay) return []
    const d = toLocalDate(selectedDay)
    if (!d) return []
    if (d.getFullYear() !== month.getFullYear() || d.getMonth() !== month.getMonth()) return []
    return monthBuckets.get(d.getDate()) ?? []
  }, [selectedDay, month, monthBuckets])

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

  // 선택 항목 삭제
  const deleteSelected = async (r: Row) => {
    if (!confirm('이 기록을 삭제할까요?')) return
    try {
      setDeletingId(r.selected_id)
      await recipeAPI.deleteSelected(r.selected_id) // api/recipe.ts에 구현 필요
      // 상세 모달이 해당 레시피를 보고 있었다면 닫기
      if (detail?.id === r.recipe_id) setDetail(null)
      await refetch()
    } catch (e) {
      console.error('[Calendar] deleteSelected failed:', e)
      alert('삭제에 실패했습니다.')
    } finally {
      setDeletingId(null)
    }
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
                  const inMonth = isSameMonth(d)
                  const count = inMonth ? (monthBuckets.get(d.getDate())?.length ?? 0) : 0

                  const classes = [
                    'cell','day',
                    inMonth ? 'cur' : 'dim',
                    dayStr === todayStr ? 'today' : '',
                    count > 0 ? 'has' : '',
                    selectedDay === dayStr ? 'sel' : ''
                  ].join(' ').trim()

                  return (
                    <button
                      key={`${d.getTime()}-${i}`}
                      className={classes}
                      onClick={() => setSelectedDay(dayStr)}
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
                <div className="day-body">
                  {selectedRecipes.length === 0 ? (
                    <div className="muted small">이 날의 기록이 없어요.</div>
                  ) : (
                    <ul className="list">
                      {selectedRecipes.map((r) => (
                        <li key={r.selected_id} className="row">
                          <div className="title clamp-1">{r.title}</div>
                          <div className="meta">{r.difficulty ?? '—'} · {r.cooking_time ?? '—'}분</div>
                          <div className="actions" style={{ display:'flex', gap:8 }}>
                            <button className="btn sm" onClick={() => openDetail(r.recipe_id)}>
                              자세히 보기
                            </button>
                            <button
                              className="btn danger outline sm"
                              onClick={() => deleteSelected(r)}
                              disabled={deletingId === r.selected_id}
                              aria-label="삭제"
                              title="삭제"
                            >
                              {deletingId === r.selected_id ? '삭제 중…' : '×'}
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            {!selectedDay && (data?.count ?? 0) === 0 && (
              <div className="empty">아직 기록이 없습니다. 레시피를 선택해 보세요!</div>
            )}
          </>
        )}
      </div>

      {detailLoading && <div className="muted">상세 불러오는 중…</div>}
      {detail && (
        <RecipeDetailModal
          recipe={detail}
          onClose={closeDetail}
          showSelect={false}
        />
      )}
    </section>
  )
}
