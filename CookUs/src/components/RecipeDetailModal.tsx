import { createPortal } from 'react-dom'
import api from '../api/axios'
import type { Recipe } from '../api/recipe'
import './RecipeDetailModal.css'

type Props = { recipe: Recipe; onClose: () => void; showSelect?: boolean }

function FramePortal({ children }: { children: React.ReactNode }) {
  const host = document.querySelector('.app-frame')
  if (!host) return <>{children}</>
  return createPortal(children, host)
}

export default function RecipeDetailModal({ recipe, onClose, showSelect }: Props){
  const selectRecipe = async () => {
    await api.post('/me/selected-recipe', { recipe_id: recipe.id })
    alert('선택되었습니다. 캘린더에 기록돼요!')
    onClose()
  }

  const steps = toLines((recipe as any).steps_text)
  const tips  = toLines((recipe as any).step_tip)
  const ings  = toArray((recipe as any).ingredients_text ?? (recipe as any).ingredient_ful)

  return (
    <FramePortal>
      <div className="rec-overlay" onClick={onClose}>
        <div className="rec-modal" onClick={e=>e.stopPropagation()}>
          <div className="rec-head">
            <h3>{recipe.title}</h3>
            <button className="rec-x" onClick={onClose}>×</button>
          </div>

          <div className="rec-sub">
            {recipe.cook_time && <span>조리시간: {recipe.cook_time}분</span>}
            {(recipe as any).difficulty && <span>난이도: {(recipe as any).difficulty}</span>}
          </div>

          {ings.length > 0 && (
            <section className="rec-sec">
              <h4>[필요 재료]</h4>
              <ul className="bullets">{ings.map((t,i)=><li key={i}>{t}</li>)}</ul>
            </section>
          )}

          {steps.length > 0 && (
            <section className="rec-sec">
              <h4>[조리 순서]</h4>
              <ol className="steps">{steps.map((t,i)=><li key={i}>{t}</li>)}</ol>
            </section>
          )}

          {tips.length > 0 && (
            <section className="rec-sec">
              <h4>[팁]</h4>
              <ul className="bullets">{tips.map((t,i)=><li key={i}>{t}</li>)}</ul>
            </section>
          )}

          <div className="rec-foot">
            <button className="btn ghost" onClick={onClose}>닫기</button>
            {showSelect && (
              <button className="btn primary" onClick={selectRecipe}>이 레시피 할래요</button>
            )}
          </div>
        </div>
      </div>
    </FramePortal>
  )
}

function toLines(x: any): string[]{
  if(!x) return []
  if(Array.isArray(x)) return x.map(String).filter(Boolean)
  if(typeof x==='string') return x.split(/\n+/).map(s=>s.trim()).filter(Boolean)
  if(typeof x==='object') return Object.values(x).map(String).filter(Boolean)
  return []
}

function toArray(x: any): string[]{
  if(!x) return []
  if(Array.isArray(x)) return x.map(String).filter(Boolean)
  if(typeof x==='object') return Object.entries(x).map(([k,v])=>{
    const vv = (v==null?'':String(v)).trim()
    return vv ? `${k} ${vv}` : k
  })
  return String(x).split(/,|·|\n/).map(s=>s.trim()).filter(Boolean)
}
