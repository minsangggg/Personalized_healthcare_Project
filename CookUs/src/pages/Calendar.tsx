import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { recipeAPI, type SelectedRecipesResponse } from '../api/recipe'
import RecipeDetailModal from '../components/RecipeDetailModal'
import type { Recipe } from '../api/recipe'
import chefBattery from '../assets/요리사 건전지.png'
import './Calendar.css'

type CalendarProps = { isLoggedIn: boolean; userName?: string }
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

export default function Calendar({ isLoggedIn, userName }: CalendarProps) {
  const [data, setData] = useState<SelectedRecipesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [detail, setDetail] = useState<Recipe | null>(null)
  const [detailCooked, setDetailCooked] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  // 인앱 토스트 메시지 (오버레이)
  const [toast, setToast] = useState<string | null>(null)
  const [toastKind, setToastKind] = useState<'ok'|'warn'>('ok')
  const showToast = (msg: string, kind: 'ok'|'warn' = 'ok', ms = 1800) => {
    setToastKind(kind)
    setToast(msg)
    window.setTimeout(() => setToast(null), ms)
  }
  // 삭제 확인 모달 상태
  const [confirmRow, setConfirmRow] = useState<Row | null>(null)
  const [showFull, setShowFull] = useState(false)
  const [togglingId, setTogglingId] = useState<number | null>(null)

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

  const openDetailByRecommend = async (recommendId: number, cooked?: boolean) => {
    setDetailLoading(true)
    try {
      setDetailCooked(!!cooked)
      const r = await recipeAPI.getRecommendation(recommendId)
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
  const [selectedDay, setSelectedDay] = useState<string | null>(() => ymd(new Date()))

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
  const todayAnchor = useMemo(() => {
    const base = new Date()
    return new Date(base.getFullYear(), base.getMonth(), base.getDate())
  }, [todayStr])
  const monthLabel = `${month.getFullYear()}년 ${month.getMonth() + 1}월`
  const isSameMonth = (d: Date) =>
    d.getFullYear() === month.getFullYear() && d.getMonth() === month.getMonth()
  const isFutureSelected = useMemo(() => {
    if (!selectedDay) return false
    const d = toLocalDate(selectedDay)
    if (!d) return false
    const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    return target.getTime() > todayAnchor.getTime()
  }, [selectedDay, todayAnchor])
  const checkedDaySet = useMemo(() => {
    const set = new Set<string>()
    for (const row of data?.recipes ?? []) {
      if ((row.action ?? 0) !== 1) continue
      const d = toLocalDate(row.selected_date)
      if (!d) continue
      set.add(ymd(d))
    }
    return set
  }, [data])
  const streakCount = useMemo(() => {
    if (!selectedDay) return 0
    const base = toLocalDate(selectedDay)
    if (!base) return 0
    let cnt = 0
    const cursor = new Date(base.getFullYear(), base.getMonth(), base.getDate())
    while (true) {
      const key = ymd(cursor)
      if (!checkedDaySet.has(key)) break
      cnt += 1
      cursor.setDate(cursor.getDate() - 1)
    }
    return cnt
  }, [selectedDay, checkedDaySet])
  const nickname = useMemo(() => userName?.trim() || '셰프', [userName])
  const motivation = useMemo(() => {
    if (!selectedDay) return null
    if (isFutureSelected) {
      return {
        text: '또 오실거죠? 요리를 기대하고 있을게요!',
        tone: 'future' as const,
        toastKind: 'ok' as const
      }
    }
    const isToday = selectedDay === todayStr
    if (selectedRecipes.length === 0) {
      const emptyDayLabel = isToday ? '오늘은' : `${selectedDay}에는`
      return {
        text: `${emptyDayLabel} 저장된 요리가 없어요! 추천을 받아서 선택해보세요!`,
        tone: 'empty' as const,
        toastKind: 'warn' as const
      }
    }
    const checkedCount = selectedRecipes.filter((r) => (r.action ?? 0) === 1).length
    if (checkedCount === 0) {
      return {
        text: isToday
          ? `오늘도 요리하는 멋진 ${nickname}님을 기록해주세요!`
          : `그날에도 요리하는 멋진 ${nickname}님을 기록해주세요!`,
        tone: 'encourage' as const,
        toastKind: 'ok' as const
      }
    }
    const streak = streakCount > 0 ? streakCount : 1
    const prefix = streak >= 10 ? '대단해요! ' : ''
    return {
      text: `${prefix}🔥 ${streak}일 연속 요리중이에요! 꾸준히 파이팅!!!`,
      tone: 'celebrate' as const,
      toastKind: 'ok' as const
    }
  }, [nickname, selectedDay, selectedRecipes, streakCount, todayStr, isFutureSelected])
  const lastMotivationKey = useRef<string | null>(null)
  useEffect(() => {
    if (!motivation || !isLoggedIn || !selectedDay || loading) return
    if (selectedDay !== todayStr) return
    const key = `${selectedDay}-${motivation.text}`
    if (lastMotivationKey.current === key) return
    lastMotivationKey.current = key
    showToast(motivation.text, motivation.toastKind, motivation.tone === 'celebrate' ? 2800 : 2200)
  }, [motivation, isLoggedIn, selectedDay, loading, todayStr])

  const goPrev = () => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))
  const goNext = () => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))
  const goToday = () => {
    const base = new Date(now.getFullYear(), now.getMonth(), 1)
    setMonth(base)
    setSelectedDay(todayStr)
  }

  // 선택 항목 삭제
  const deleteSelected = async (r: Row) => {
    try {
      setDeletingId(r.selected_id)
      await recipeAPI.deleteSelected(r.selected_id) // api/recipe.ts에 구현 필요
      // 상세 모달이 해당 레시피를 보고 있었다면 닫기
      if (detail?.recipe_id === r.recipe_id) setDetail(null)
      await refetch()
      // 인앱 알림 (오버레이)
      showToast('기록을 삭제했어요.', 'ok')
    } catch (e) {
      console.error('[Calendar] deleteSelected failed:', e)
      showToast('삭제에 실패했어요. 잠시 후 다시 시도해 주세요.', 'warn', 2200)
    } finally {
      setDeletingId(null)
    }
  }

  // action 토글
  const toggleAction = async (r: Row) => {
    const next = (r.action ?? 0) === 1 ? 0 : 1
    try {
      setTogglingId(r.selected_id)
      await recipeAPI.setSelectedAction(r.selected_id, next as 0|1)
      await refetch()
      showToast(next === 1 ? '체크했어요.' : '체크 해제했어요.', 'ok')
    } catch (e) {
      console.error('[Calendar] toggleAction failed:', e)
      showToast('변경에 실패했어요.', 'warn', 2200)
    } finally {
      setTogglingId(null)
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
                  const dayRows = inMonth ? (monthBuckets.get(d.getDate()) ?? []) : []
                  const count = dayRows.length
                  const hasCooked = dayRows.some((row) => (row.action ?? 0) === 1)

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
                      onClick={() => { if (!inMonth) { setMonth(new Date(d.getFullYear(), d.getMonth(), 1)) } setSelectedDay(dayStr) }}
                      title={count > 0 ? `${count}개 기록` : undefined}
                    >
                      <span className="dnum">{d.getDate()}</span>
                      {count > 0 && (
                        <span className={`dot ${hasCooked ? 'dot--cooked' : ''}`} aria-hidden />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            {motivation && !loading && (
              <div className={`cal-note cal-note--${motivation.tone}`}>
                <img src={chefBattery} alt="" aria-hidden className="cal-note__avatar" />
                <div className="cal-note__bubble">
                  <span className="cal-note__text">{motivation.text}</span>
                </div>
              </div>
            )}

            {/* 선택 날짜 상세 */}
            {selectedDay && (
              <div className="day-detail">
                <div className="day-head">
                  <span>{selectedDay}</span>
                  <div className="head-actions">
                    <button className="btn sm" onClick={()=> setShowFull(true)} title="전체 보기">모든 레시피</button>
                  </div>
                </div>
                <div className="day-body">
                  {selectedRecipes.length === 0 ? (
                    <div className="muted small">해당 날에는 아직 기록이 없어요.</div>
                  ) : (
                    <ul className="list">
                      {selectedRecipes.map((r) => (
                        <li key={r.selected_id} className={`row ${r.action === 1 ? 'done' : ''}`}>
                          <button
                            className={`btn check sm ${r.action === 1 ? 'active' : ''}`}
                            onClick={() => toggleAction(r)}
                            disabled={togglingId === r.selected_id}
                            title={r.action === 1 ? '체크 해제' : '체크'}
                          >
                            {r.action === 1 ? '☑' : '☐'}
                          </button>
                          <div className="title clamp-1">{r.recipe_nm_ko}</div>
                          <div className="actions" style={{ display:'flex', gap:12 }}>
                            <button className="btn sm" onClick={() => openDetailByRecommend(r.recommend_id, r.action === 1)}>
                              자세히 보기
                            </button>
                            <button
                              className="btn danger outline sm"
                              onClick={() => setConfirmRow(r)}
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

      {/* 토스트 오버레이 (앱 프레임 최상단에 렌더) */}
      {toast && typeof document !== 'undefined' && document.querySelector('.app-tab') && (
        createPortal(
          <div className={`cal-toast ${toastKind}`}>{toast}</div>,
          document.querySelector('.app-tab') as Element
        )
      )}

      {/* 삭제 확인 오버레이 */}
      {confirmRow && typeof document !== 'undefined' && document.querySelector('.app-tab') && (
        createPortal(
          <div className="cal-overlay" onClick={() => setConfirmRow(null)}>
            <div className="cal-confirm" onClick={(e) => e.stopPropagation()}>
              <div className="cal-confirm-title">이 기록을 삭제할까요?</div>
              <div className="cal-confirm-meta clamp-1">{confirmRow.recipe_nm_ko}</div>
              <div className="cal-confirm-actions">
                <button className="btn" onClick={() => setConfirmRow(null)}>취소</button>
                <button
                  className="btn primary"
                  onClick={async () => { const r = confirmRow; setConfirmRow(null); await deleteSelected(r!); }}
                >
                  삭제
                </button>
              </div>
            </div>
          </div>,
          document.querySelector('.app-tab') as Element
        )
      )}

      {detailLoading && <div className="muted">상세 불러오는 중…</div>}
      {detail && (
        <RecipeDetailModal
          recipe={detail}
          onClose={closeDetail}
          showSelect={false}
          cooked={detailCooked}
        />
      )}

      {/* 전체보기 모달 */}
      {showFull && typeof document !== 'undefined' && document.querySelector('.app-tab') && (
        createPortal(
          <div className="cal-full-overlay" onClick={()=> setShowFull(false)}>
            <div className="cal-full" onClick={(e)=> e.stopPropagation()}>
              <button className="cal-x" onClick={()=> setShowFull(false)}>×</button>
              <h3 className="title">{selectedDay ? `${selectedDay}의 레시피` : '전체 보기'}</h3>
              {!selectedDay || selectedRecipes.length === 0 ? (
                <div className="muted">표시할 기록이 없어요.</div>
              ) : (
                <ul className="list">
                  {selectedRecipes.map((r) => (
                    <li key={`full-${r.selected_id}`} className={`row ${r.action === 1 ? 'done' : ''}`}>
                      <button
                        className={`btn check sm ${r.action === 1 ? 'active' : ''}`}
                        onClick={() => toggleAction(r)}
                        disabled={togglingId === r.selected_id}
                        title={r.action === 1 ? '체크 해제' : '체크'}
                      >
                        {r.action === 1 ? '☑' : '☐'}
                      </button>
                      <div className="title clamp-1">{r.recipe_nm_ko}</div>
                      <div className="actions" style={{ display:'flex', gap:12 }}>
                        <button className="btn sm" onClick={() => openDetailByRecommend(r.recommend_id, r.action === 1)}>
                          자세히 보기
                        </button>
                        <button
                          className="btn danger outline sm"
                          onClick={() => setConfirmRow(r)}
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
              <div style={{display:'flex', justifyContent:'flex-end', marginTop:10}}>
                <button className="btn" onClick={()=> setShowFull(false)}>닫기</button>
              </div>
            </div>
          </div>,
          document.querySelector('.app-tab') as Element
        )
      )}
    </section>
  )
}
