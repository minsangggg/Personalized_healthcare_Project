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

type Props = { isLoggedIn: boolean; onRequireLogin: () => void }

export default function Fridge({ isLoggedIn, onRequireLogin }: Props) {
  const [items, setItems] = useState<Ingredient[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [showRec, setShowRec] = useState(false)
  const [detail, setDetail] = useState<Recipe | null>(null)

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
              <div key={r.id} className="rec-card">
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
