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
  const [plans, setPlans] = useState<SupplementPlan[]>([])
  const [monthStatus, setMonthStatus] = useState<Map<string, DayStatus>>(new Map())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [showRecommender, setShowRecommender] = useState(false)
  const [month, setMonth] = useState(() => { const d=new Date(); return new Date(d.getFullYear(), d.getMonth(), 1) })
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [daily, setDaily] = useState<DayPlan[] | null>(null)

  const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  const ym = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`

  const load = async () => {
    if (!isLoggedIn) { setPlans([]); setMonthStatus(new Map()); return }
    setLoading(true); setError(null)
    try {
      const [p, s] = await Promise.all([
        nutritionAPI.listPlans(),
        nutritionAPI.getMonthStatus(ym(month)),
      ])
      setPlans(p)
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
          <button className="btn ghost" onClick={fetchRecs} disabled={recLoading}>{recLoading ? '추천 중…' : '영양제 추천받으러 가보기'}</button>
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
          <div className="card">
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
              <h3 className="sec-title" style={{ margin:0 }}>{selectedDay ? `${selectedDay} 체크` : '하루 체크'}</h3>
              <button className="btn" onClick={() => isLoggedIn ? setShowAdd(true) : onRequireLogin()}>영양제 등록</button>
            </div>
            {!selectedDay && <div className="muted">날짜를 선택해 주세요.</div>}
            {selectedDay && (
              <div className="intake-list">
                {(daily ?? []).map(dp => (
                  <label key={dp.plan_id} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'6px 0' }}>
                    <span>{dp.supplement_name} <span style={{ color:'#777', fontSize:12 }}>· {dp.time_slot}</span></span>
                    <input type="checkbox" checked={dp.taken} onChange={async (e)=>{
                      await nutritionAPI.setTaken(dp.plan_id, selectedDay!, e.target.checked)
                      await load()
                      await loadDaily(selectedDay!)
                    }} />
                  </label>
                ))}
                {(!daily || daily.length === 0) && <div className="muted">등록된 영양제가 없어요. 상단에서 등록해 보세요.</div>}
              </div>
            )}
          </div>
        </div>
      )}

      {showAdd && (
        <AddSupplementPlanModal
          onClose={() => setShowAdd(false)}
          onAdded={() => { setShowAdd(false); load() }}
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

function fmt(s: string) {
  try { return new Date(s).toLocaleString() } catch { return s }
}
