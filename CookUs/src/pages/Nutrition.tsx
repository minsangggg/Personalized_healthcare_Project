import { useEffect, useMemo, useState } from 'react'
import './Nutrition.css'
import { nutritionAPI, type DayPlan, type DayStatus, type SupplementPlan } from '../api/nutrition'
import SupplementRecommenderModal from '../components/SupplementRecommenderModal'
import AddSupplementPlanModal from '../components/AddSupplementPlanModal'
import NutritionCalendar from './NutritionCalendar'
import chefBattery from '../assets/요리사 건전지.png'

const isFutureDate = (dateStr: string) => {
  const d = new Date(dateStr)
  const today = new Date()
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  return target > todayOnly
}

type Props = {
  isLoggedIn: boolean
  onRequireLogin: () => void
  userName?: string
}

export default function Nutrition({ isLoggedIn, onRequireLogin, userName }: Props) {
  const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const ym = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`

  const [monthStatus, setMonthStatus] = useState<Map<string, DayStatus>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [editPlan, setEditPlan] = useState<SupplementPlan | null>(null)
  const [showRecommender, setShowRecommender] = useState(false)
  const [month, setMonth] = useState(() => { const d=new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [selectedDay, setSelectedDay] = useState<string | null>(() => ymd(new Date()))
  const [daily, setDaily] = useState<DayPlan[] | null>(null)

  const nickname = useMemo(() => {
    const base = userName?.trim()
    if (!base) return '건강 메이트'
    return base
  }, [userName])
  const nickLabel = useMemo(() => (nickname.endsWith('님') ? nickname : `${nickname}님`), [nickname])

  const slotLabel = (slot: string): string => {
    const cleaned = slot.replace(/\s+/g, '')
    if (/아침|모닝|morning|오전/i.test(cleaned)) return '아침'
    if (/점심|런치|lunch|정오/i.test(cleaned)) return '점심'
    if (/저녁|dinner|evening|밤|취침/i.test(cleaned)) return '저녁'
    if (/간식|snack|티타임/i.test(cleaned)) return '간식'
    return '기타'
  }

  const dailySummary = useMemo(() => {
    if (!daily || daily.length === 0) {
      return {
        total: 0,
        taken: 0,
        missingPlans: [] as DayPlan[],
        missingSlots: [] as string[],
      }
    }
    const missingPlans = daily.filter((p) => !p.taken)
    const missingSlots = Array.from(new Set(missingPlans.map((p) => slotLabel(p.time_slot))))
    return {
      total: daily.length,
      taken: daily.filter((p) => p.taken).length,
      missingPlans,
      missingSlots,
    }
  }, [daily])

  const nutritionMotivation = useMemo(() => {
    if (!selectedDay) return null
    if (isFutureDate(selectedDay)) {
      return { tone: 'future' as const, text: '미래의 건강 루틴도 기대하고 있을게요! 알람 맞춰두는 건 어떨까요?' }
    }
    if (!daily || daily.length === 0) {
      return { tone: 'empty' as const, text: '이 날 등록된 영양제가 없어요. 플랜을 추가해서 건강 루틴을 만들어보세요!' }
    }
    const checkedCount = dailySummary.taken
    const totalCount = dailySummary.total
    if (checkedCount === 0) {
      const missingList = dailySummary.missingSlots.join(', ')
      return { tone: 'warn' as const, text: `오늘 영양제를 안드셨어요🥺 ${missingList || '아침'}부터 천천히 챙겨볼까요?` }
    }
    if (checkedCount === totalCount) {
      return { tone: 'celebrate' as const, text: `오늘도 건강한 하루! 모든 영양제 체크 완료!` }
    }
    const firstMissing = dailySummary.missingPlans[0]
    const firstLabel = firstMissing ? slotLabel(firstMissing.time_slot) : null
    const missingList = dailySummary.missingSlots.join(', ')
    return { tone: 'encourage' as const, text: firstLabel ? `아직 ${missingList} 영양제를 안드셨어요! 오늘도 파이팅!` : `아직 ${missingList} 영양제를 안드셨어요! 오늘도 파이팅!` }
  }, [daily, dailySummary, nickLabel, selectedDay])

  const load = async () => {
    if (!isLoggedIn) { setMonthStatus(new Map()); return }
    setLoading(true); setError(null)
    try {
      const s = await nutritionAPI.getMonthStatus(ym(month))
      const map = new Map<string, DayStatus>()
      for (const row of s) map.set(row.date, row)
      setMonthStatus(map)
      if (selectedDay) await loadDaily(selectedDay)
    } catch (e: any) {
      setError(e?.message ?? '데이터를 불러오지 못했어요.')
    } finally { setLoading(false) }
  }

  const loadDaily = async (dateStr: string) => {
    try { setDaily(await nutritionAPI.getDaily(dateStr)) }
    catch { setDaily([]) }
  }

  useEffect(() => { load() }, [isLoggedIn, month])

  const fetchRecs = async () => {
    if (!isLoggedIn) return onRequireLogin()
    setShowRecommender(true)
  }

  return (
    <section className="app-tab nutrition">
      <div className="nt-header">
        <h2 className="title">나의 영양관리</h2>
        <div className="actions">
          <button className="btn ghost" onClick={fetchRecs} disabled={recLoading}>{recLoading ? '추천 중…' : '영양제 추천받으러 가기'}</button>
        </div>
      </div>

      {!isLoggedIn && <div className="muted">로그인하면 영양제를 관리할 수 있어요.</div>}
      {isLoggedIn && loading && <div className="muted">불러오는 중…</div>}
      {isLoggedIn && error && <div className="error">{error}</div>}

      {isLoggedIn && !loading && (
        <div className="nt-grid">
          <div className="nt-calendar">
            <div className="nt-calendar-inner">
              <NutritionCalendar
                month={month}
                onMonthChange={setMonth}
                monthStatus={monthStatus}
                onSelectDay={async (s)=>{ setSelectedDay(s); await loadDaily(s) }}
                selectedDay={selectedDay}
              />
            </div>
          </div>
          {selectedDay && nutritionMotivation && (
            <div className={`nut-note nut-note--${nutritionMotivation.tone}`}>
              <img src={chefBattery} alt="" aria-hidden className="nut-note__avatar" />
              <div className="nut-note__bubble">
                <span className="nut-note__text">{nutritionMotivation.text}</span>
              </div>
            </div>
          )}
          <div className="card daily-card">
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom: '7px'}}>
              <h3 className="sec-title" style={{ margin:0 }}>{selectedDay ? `${selectedDay} 체크` : '하루 체크'}</h3>
              <button className="btn" onClick={() => isLoggedIn ? setShowAdd(true) : onRequireLogin()}>영양제 등록</button>
            </div>
            {!selectedDay && <div className="muted">날짜를 선택해 주세요.</div>}
            {selectedDay && (
              <div className="check-list-wrap">
                <div className="check-list">
                  {(daily ?? []).map(dp => (
                    <div
                      key={dp.plan_id}
                      className={`check-item ${dp.taken ? 'on' : ''} ${isFutureDate(selectedDay) ? 'disabled' : ''}`}
                    >
                      <div className="info">
                        <div className="name">{dp.supplement_name}</div>
                        <div className="slot">{dp.time_slot}</div>
                      </div>
                      <button
                        className={`chkbox ${dp.taken ? 'on' : ''}`}
                        disabled={isFutureDate(selectedDay)}
                        onClick={async () => {
                          setDaily(prev => prev ? prev.map(p => p.plan_id === dp.plan_id ? { ...p, taken: !dp.taken } : p) : prev)
                          await nutritionAPI.setTaken(dp.plan_id, selectedDay!, !dp.taken)
                          await load()
                          await loadDaily(selectedDay!)
                        }}
                        aria-pressed={dp.taken}
                        aria-label={dp.taken ? '완료' : '체크'}
                      >
                        {dp.taken ? '✓' : ''}
                      </button>
                      <div style={{ display:'flex', gap:6 }}>
                        <button
                          className="icon-btn small"
                          title="수정"
                          onClick={() => {
                            setEditPlan({ plan_id: dp.plan_id, supplement_name: dp.supplement_name, time_slot: dp.time_slot })
                            setShowAdd(true)
                          }}
                        >
                          ✎
                        </button>
                        <button
                          className="icon-btn small"
                          title="삭제"
                          onClick={async () => {
                            await nutritionAPI.deletePlan(dp.plan_id)
                            await load()
                            await loadDaily(selectedDay!)
                          }}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                  {(!daily || daily.length === 0) && <div className="muted">등록된 영양제가 없어요. 상단에서 등록해 보세요.</div>}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {showAdd && (
        <AddSupplementPlanModal
          plan={editPlan || undefined}
          onClose={() => setShowAdd(false)}
          onAdded={() => { setShowAdd(false); setEditPlan(null); load(); if (selectedDay) loadDaily(selectedDay) }}
        />
      )}

      {showRecommender && (
        <SupplementRecommenderModal onClose={() => setShowRecommender(false)} />
      )}
    </section>
  )
}

