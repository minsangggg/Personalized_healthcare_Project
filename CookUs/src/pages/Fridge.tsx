import { useEffect, useState } from 'react'
import { fridgeAPI } from '../api/fridge'
import { recipeAPI } from '../api/recipe'
import type { Ingredient } from '../api/fridge'
import type { Recipe } from '../api/recipe'
import AddIngredientModal from '../components/AddIngredientModal'
import RecipeCard from '../components/RecipeCard'
import RecipeDetailModal from '../components/RecipeDetailModal'
import './Fridge.css'
import servingBattery from '../assets/서빙 건전지.png'
import { fetchFaq, fetchFaqCategories, type FaqItem } from '../api/faq'

type Props = { isLoggedIn: boolean; onRequireLogin: () => void }

export default function Fridge({ isLoggedIn, onRequireLogin }: Props) {
  const [items, setItems] = useState<Ingredient[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [showRec, setShowRec] = useState(false)
  const [detail, setDetail] = useState<Recipe | null>(null)
  const [showAbout, setShowAbout] = useState(false)
  const [showFAQ, setShowFAQ] = useState(false)

  const load = async () => { try { setItems(await fridgeAPI.listFridge()) } catch {} }
  useEffect(() => { if (isLoggedIn) load(); else { setItems([]) } }, [isLoggedIn])

  const openAdd = () => (isLoggedIn ? setShowAdd(true) : onRequireLogin())
  const recommend = () => (isLoggedIn ? setShowRec(true) : onRequireLogin())

  return (
    <section className="app-tab fri">
      <div className="card hero-one">
        <div className="badge">CookUS</div>
        <h1 className="title">레시피 마켓</h1>
        <p className="desc">우리랑 요리하자!</p>

        {/* 중앙 큰 냉장고 */}
        <div className="illust-wrap">
          <div className="fridge-illust">
            <FridgeArtLarge />
          </div>
          <img
            src={servingBattery}
            alt="서빙 건전지"
            className="illust battery"
          />
        </div>

        {/* 일러스트 아래로 이동 */}
        <div className="counter">내 재료 {items.length}개</div>

        {/* 버튼 */}
        <div className="actions">
          <button className="btn" onClick={openAdd}>재료 추가</button>
          <button className="btn primary" onClick={recommend}>레시피 추천받기</button>
        </div>

        {/* footer links */}
        <div style={{marginTop:16, fontSize:12.5, color:'#6b7280', display:'flex', alignItems:'center', gap:10}}>
          <a role="link" onClick={()=>setShowAbout(true)} style={{cursor:'pointer', color:'#6b7280', textDecoration:'none'}}>쿠커스 소개</a>
          <span style={{width:1, height:14, background:'#d1d5db'}} />
          <a role="link" onClick={()=>setShowFAQ(true)} style={{cursor:'pointer', color:'#6b7280', textDecoration:'none'}}>FAQ</a>
        </div>
      </div>

      {/* 모달 */}
      {showAdd && (
        <div className="modal-backdrop" onClick={() => setShowAdd(false)}>
          <AddIngredientModal onClose={async (saved) => { setShowAdd(false); if (saved) await load() }} />
        </div>
      )}
      {showRec && (
        <RecommendModal
          onClose={() => setShowRec(false)}
          onDetail={(r) => setDetail(r)}
        />
      )}

      {/* 모달: 레시피 상세 */}
      {detail && (
        <div className="inner-overlay" onClick={() => setDetail(null)}>
          <div onClick={e=>e.stopPropagation()}>
            <RecipeDetailModal recipe={detail} onClose={() => setDetail(null)} />
          </div>
        </div>
      )}

      {/* 소개 모달 */}
      {showAbout && (
        <div className="inner-overlay" onClick={()=>setShowAbout(false)}>
          <div className="modal card rec-modal modal-wide" onClick={e=>e.stopPropagation()}>
            <button className="modal-close" onClick={()=>setShowAbout(false)}>×</button>
            <h2 style={{marginTop:0}}>쿠커스 소개</h2>
            <p style={{textAlign:'left', lineHeight:1.6}}>
              쿠커스는 냉장고 재료를 기반으로 맞춤형 레시피를 추천하고,
              한 번의 선택으로 요리 기록까지 관리할 수 있는 요리 도우미입니다.
              캘린더에 요리 기록을 남기고, 대시보드로 나의 요리 습관을 확인해 보세요.
            </p>
            <div style={{display:'flex', justifyContent:'flex-end', marginTop:12}}>
              <button className="btn" onClick={()=>setShowAbout(false)}>닫기</button>
            </div>
          </div>
        </div>
      )}

      {/* FAQ 모달 */}
      {showFAQ && (
        <FAQModal onClose={()=>setShowFAQ(false)} />
      )}
    </section>
  )
}

/* ===== 추천 모달 ===== */
function RecommendModal({ onClose, onDetail }: { onClose: () => void; onDetail: (r: Recipe) => void; }){
  const [loading, setLoading] = useState(true)
  const [list, setList] = useState<Recipe[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true); setError(null)
      try {
        const data = await recipeAPI.recommendTop3()
        if (mounted) setList(data)
      } catch (e:any) {
        if (mounted) setError('추천을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [])

  return (
    <div className="inner-overlay" onClick={onClose}>
      <div className="modal card rec-modal" onClick={e=>e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2 style={{marginTop:0}}>추천 레시피</h2>

        {loading && (
          <div className="rec-loading">
            <div className="spinner" />
            <div className="rec-loading-text">추천 중…</div>
          </div>
        )}

        {!loading && error && (
          <div className="rec-error">{error}</div>
        )}

        {!loading && !error && (
          <div className="rec-grid">
            {list.map(r => (
              <div key={(r as any).recipe_id} className="rec-card">
                <RecipeCard recipe={r} onDetail={() => onDetail(r)} />
              </div>
            ))}
          </div>
        )}

        <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginTop:12}}>
          <button className="btn" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  )
}

function FridgeArtLarge() {
  return (
    <svg width="240" height="250" viewBox="0 0 210 240" fill="none" style={{display:'block'}}>
      <rect x="20" y="10" width="150" height="220" rx="14" fill="#ffffff" stroke="#e5e1d8" />
      <rect x="170" y="10" width="30" height="220" rx="6" fill="#fff3e0" stroke="#e5e1d8" />
      <rect x="50" y="50" width="100" height="6" rx="3" fill="#e9e3d8" />
      <rect x="50" y="90" width="100" height="6" rx="3" fill="#e9e3d8" />
      <rect x="50" y="130" width="100" height="6" rx="3" fill="#e9e3d8" />
      <rect x="50" y="170" width="100" height="6" rx="3" fill="#e9e3d8" />
    </svg>
  )
}

/* ===== FAQ Modal ===== */
function FAQModal({ onClose }: { onClose: () => void }){
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string>('')
  const [items, setItems] = useState<FaqItem[]>([])
  const [cats, setCats] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    let alive = true
    ;(async ()=>{
      setLoading(true)
      try{
        const data = await fetchFaq(query, category)
        if(alive) setItems(data)
      } finally { if(alive) setLoading(false) }
    })()
    return ()=>{ alive=false }
  },[query, category])

  useEffect(()=>{
    let alive = true
    ;(async ()=>{
      try{
        const cs = await fetchFaqCategories()
        if(alive) setCats(cs)
      } catch{}
    })()
    return ()=>{ alive=false }
  },[])

  return (
    <div className="inner-overlay" onClick={onClose}>
      <div className="modal card rec-modal modal-full" onClick={e=>e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2 style={{marginTop:0, textAlign:'center'}}>무엇을 도와드릴까요?</h2>
        <div style={{display:'flex', justifyContent:'center', margin:'8px 0 12px', gap:8}}>
          <input
            value={query}
            onChange={e=>setQuery(e.target.value)}
            placeholder="궁금한 점을 검색해보세요."
            style={{width:'100%', maxWidth:520, padding:'10px 12px', borderRadius:10, border:'1px solid #e5e7eb'}}
          />
          <select value={category} onChange={e=>setCategory(e.target.value)} style={{padding:'10px 8px', borderRadius:10, border:'1px solid #e5e7eb'}}>
            <option value=''>분류 전체</option>
            {cats.map((c,i)=>(<option key={i} value={c}>{c}</option>))}
          </select>
        </div>
        {loading ? (
          <div className="rec-loading"><div className="spinner" />
            <div className="rec-loading-text">검색 중…</div></div>
        ) : (
          <div style={{overflow:'auto'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:14}}>
              <thead>
                <tr style={{background:'#f9fafb'}}>
                  <th style={{textAlign:'left', padding:'8px', borderBottom:'1px solid #e5e7eb', width:'35%'}}>질문</th>
                  <th style={{textAlign:'left', padding:'8px', borderBottom:'1px solid #e5e7eb'}}>답변</th>
                  <th style={{textAlign:'left', padding:'8px', borderBottom:'1px solid #e5e7eb', width:120}}>분류</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.faq_id}>
                    <td style={{padding:'10px 8px', borderBottom:'1px solid #f1f5f9', fontWeight:700, color:'#111827'}}>{it.question}</td>
                    <td style={{padding:'10px 8px', borderBottom:'1px solid #f1f5f9', color:'#4b5563', whiteSpace:'pre-wrap'}}>{it.answer}</td>
                    <td style={{padding:'10px 8px', borderBottom:'1px solid #f1f5f9'}}>{it.category ?? '-'}</td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr><td colSpan={3} style={{textAlign:'center', color:'#6b7280', padding:'16px'}}>검색 결과가 없어요.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <div style={{display:'flex', justifyContent:'flex-end', marginTop:12}}>
          <button className="btn" onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  )
}
