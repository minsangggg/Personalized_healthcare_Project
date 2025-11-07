import { useEffect, useState } from 'react'
import './Nutrition.css'
import { nutritionAPI, type DayPlan, type DayStatus, type SupplementPlan } from '../api/nutrition'
import SupplementRecommenderModal from '../components/SupplementRecommenderModal'
import AddSupplementPlanModal from '../components/AddSupplementPlanModal'
import NutritionCalendar from './NutritionCalendar'

type Props = {
  isLoggedIn: boolean
  onRequireLogin: () => void
}

export default function Nutrition({ isLoggedIn, onRequireLogin }: Props) {
  // plans list is not needed in UI (daily fetch provides items)
  const [monthStatus, setMonthStatus] = useState<Map<string, DayStatus>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [editPlan, setEditPlan] = useState<SupplementPlan | null>(null)
  const [showRecommender, setShowRecommender] = useState(false)
  const [month, setMonth] = useState(() => { const d=new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [daily, setDaily] = useState<DayPlan[] | null>(null)

  const ym = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`

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

  const isFuture = (dateStr: string) => {
    const d = new Date(dateStr)
    const today = new Date()
    const t = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()
    const dd = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
    return dd > t
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
          <div>
            <NutritionCalendar
              month={month}
              onMonthChange={setMonth}
              monthStatus={monthStatus}
              onSelectDay={async (s)=>{ setSelectedDay(s); await loadDaily(s) }}
              selectedDay={selectedDay}
            />
          </div>
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
                    <div key={dp.plan_id} className={`check-item ${dp.taken ? 'on' : ''} ${isFuture(selectedDay) ? 'disabled' : ''}`}>
                      <div className="info">
                        <div className="name">{dp.supplement_name}</div>
                        <div className="slot">{dp.time_slot}</div>
                      </div>
                    <button className={`chkbox ${dp.taken ? 'on' : ''}`} disabled={isFuture(selectedDay)} onClick={async ()=>{
                      // optimistic toggle
                      setDaily(prev => prev ? prev.map(p => p.plan_id === dp.plan_id ? { ...p, taken: !dp.taken } : p) : prev)
                      await nutritionAPI.setTaken(dp.plan_id, selectedDay!, !dp.taken)
                      await load()
                      await loadDaily(selectedDay!)
                    }} aria-pressed={dp.taken} aria-label={dp.taken ? '완료' : '체크'}>{dp.taken ? '✓' : ''}</button>
                    <div style={{ display:'flex', gap:6 }}>
                      <button className="icon-btn small" title="수정" onClick={()=>{
                        setEditPlan({ plan_id: dp.plan_id, supplement_name: dp.supplement_name, time_slot: dp.time_slot })
                        setShowAdd(true)
                      }}>✎</button>
                      <button className="icon-btn small" title="삭제" onClick={async ()=>{
                        await nutritionAPI.deletePlan(dp.plan_id)
                        await load()
                        await loadDaily(selectedDay!)
                      }}>🗑️</button>
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
        <SupplementRecommenderModal
          onClose={() => setShowRecommender(false)}
        />
      )}
    </section>
  )
}
