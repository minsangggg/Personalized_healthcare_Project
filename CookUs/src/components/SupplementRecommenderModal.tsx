import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { nutritionAPI, type RecommendFilters } from '../api/nutrition'
import './SupplementRecommenderModal.css'

type Props = { onClose: () => void }

const AGE_OPTIONS: RecommendFilters['age_band'][] = ['10대','20대','30대','40대','50대 이상']
const GOAL_OPTIONS = [
  '수면/이완','에너지/피로','집중/인지','관절/뼈','피부/모발','눈 건강','간 건강','혈당/대사','면역/항산화'
]
const SHAPE_OPTIONS = ['캡슐','정','가루','액상','젤리','스틱','츄어블','환']

export default function SupplementRecommenderModal({ onClose }: Props) {
  const [age, setAge] = useState<RecommendFilters['age_band']>('20대')
  const [sex, setSex] = useState<RecommendFilters['sex']>('F')
  const [pregnant, setPregnant] = useState(false)
  const [shapes, setShapes] = useState<string[]>([])
  const [goals, setGoals] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<ReturnType<typeof formatResults>['data']>([])
  const [detail, setDetail] = useState<{ goal: string; item: any } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canRun = goals.length > 0

  const run = async () => {
    if (!canRun || running) return
    setRunning(true); setError(null)
    try {
      const payload: RecommendFilters = {
        age_band: age, sex, pregnant_possible: sex === 'F' ? pregnant : false,
        shapes, goals,
      }
      const data = await nutritionAPI.recommend(payload)
      const { data: formatted } = formatResults(data)
      // limit 5 items per goal (client-side safety)
      setResults(formatted.map(g => ({ ...g, items: (g.items || []).slice(0,5) })))
    } catch (e: any) {
      setError(e?.message ?? '추천을 불러오지 못했어요.')
    } finally { setRunning(false) }
  }

  return (
    <ModalFrame onClose={onClose} title="영양제 추천" desc="연령/성별/목표/제형을 선택해 추천을 받아보세요.">
      <div className="reco-body" style={{ display:'grid', gridTemplateColumns:'minmax(0,1fr)', gap:12 }}>
        <div className="card" style={{ textAlign:'left' }}>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(2, minmax(0,1fr))', gap:10 }}>
            <label>
              <div className="label">연령대</div>
              <select value={age} onChange={e=>setAge(e.target.value as any)}>
                {AGE_OPTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </label>
            <label>
              <div className="label">성별</div>
              <select value={sex} onChange={e=>setSex(e.target.value as any)}>
                <option value="F">여성(F)</option>
                <option value="M">남성(M)</option>
              </select>
            </label>
            {sex === 'F' && (
              <label style={{ display:'flex', alignItems:'end', gap:8 }}>
                <input type="checkbox" checked={pregnant} onChange={e=>setPregnant(e.target.checked)} />
                <span>임신 가능성 있음</span>
              </label>
            )}
          </div>

          <div style={{ marginTop:10 }}>
            <div className="label">선호 제형</div>
            <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
              {SHAPE_OPTIONS.map(s => (
                <label key={s} style={{ display:'inline-flex', alignItems:'center', gap:6 }}>
                  <input type="checkbox" checked={shapes.includes(s)} onChange={(e)=>{
                    setShapes(prev => e.target.checked ? [...prev, s] : prev.filter(x=>x!==s))
                  }} />
                  <span>{s}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ marginTop:10 }}>
            <div className="label">개선 목표</div>
            <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
              {GOAL_OPTIONS.map(g => (
                <label key={g} style={{ display:'inline-flex', alignItems:'center', gap:6 }}>
                  <input type="checkbox" checked={goals.includes(g)} onChange={(e)=>{
                    setGoals(prev => e.target.checked ? [...prev, g] : prev.filter(x=>x!==g))
                  }} />
                  <span>{g}</span>
                </label>
              ))}
            </div>
          </div>

          <div style={{ display:'flex', justifyContent:'flex-end', marginTop:12, gap:8 }}>
            <button className="btn" onClick={run} disabled={!canRun || running}>{running ? '추천 중…' : '결과 보기'}</button>
          </div>
          {error && <div className="error" style={{ marginTop:6 }}>{error}</div>}
        </div>

        {results.length > 0 && (
          <div className="card" style={{ textAlign:'left' }}>
            <h4 className="sec-title" style={{ marginTop:0 }}>추천 결과</h4>
            <div className="reco-sections">
              {results.map((g, idx) => (
                <section key={idx} className="reco-section">
                  <div className="reco-goal">🎯 {g.goal}</div>
                  <div className="reco-grid">
                    {g.items.map((it: any, i2: number) => (
                      <button key={i2} className="reco-card" onClick={()=>setDetail({ goal: g.goal, item: it })}>
                        <div className="r-name">{it.product_name}</div>
                        <div className="r-meta">
                          <span className="badge">{it.shape || '제형'}</span>
                          {it.timing && <span className="timing">{it.timing}</span>}
                        </div>
                      </button>
                    ))}
                    {g.items.length === 0 && <div className="muted">결과가 없어요.</div>}
                  </div>
                </section>
              ))}
            </div>
          </div>
        )}
      </div>
      {detail && (
        <SupplementDetailModal goal={detail.goal} item={detail.item} onClose={()=>setDetail(null)} />
      )}
    </ModalFrame>
  )
}

function formatResults(raw: any) {
  // Accepts array of { goal, items: [{ category, product_name, function, shape, timing? }] }
  if (!Array.isArray(raw)) return { data: [] as Array<{ goal:string; items:any[] }> }
  return { data: raw }
}

// inline detail modal
export function SupplementDetailModal({ goal, item, onClose }: { goal: string; item: any; onClose: () => void }){
  return (
    <ModalFrame title={item.product_name || '상세정보'} onClose={onClose}>
      <div style={{ textAlign:'left', display:'grid', gap:8 }}>
        <div><strong>목표</strong> · {goal}</div>
        {item.category && <div><strong>카테고리</strong> · {item.category}</div>}
        {item.shape && <div><strong>제형</strong> · {item.shape}</div>}
        {item.timing && <div><strong>섭취 타이밍</strong> · {item.timing}</div>}
        {item.function && (
          <div>
            <div style={{ fontWeight:800, marginTop:6 }}>기능성</div>
            <div style={{ whiteSpace:'pre-wrap', lineHeight:1.5 }}>{item.function}</div>
          </div>
        )}
      </div>
    </ModalFrame>
  )
}
