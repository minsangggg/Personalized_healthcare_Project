import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import api from '../api/axios'
import type { Recipe } from '../api/recipe'
import './RecipeDetailModal.css'

type Props = { recipe: Recipe; onClose: () => void; showSelect?: boolean; cooked?: boolean }

function FramePortal({ children }: { children: React.ReactNode }) {
  const host = document.querySelector('.app-frame')
  if (!host) return <>{children}</>
  return createPortal(children, host)
}

export default function RecipeDetailModal({ recipe, onClose, showSelect=true, cooked=false }: Props){
  const [selecting, setSelecting] = useState(false)
  const [selected, setSelected] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const check = async () => {
      try {
        const { data } = await api.get('/me/selected-recipe/status', {
          params: { recipe_id: recipe.recipe_id }
        })
        if (!alive) return
        if (data?.selected) {
          setSelected(true)
          setNotice('이미 캘린더에 기록된 레시피예요.')
        } else {
          setSelected(false)
          setNotice(null)
        }
      } catch {
      }
    }
    check()
    return () => { alive = false }
  }, [recipe.recipe_id])

  const selectRecipe = async () => {
    if (selected || selecting) return
    try {
      setSelecting(true)
      await api.post('/me/selected-recipe', { recipe_id: recipe.recipe_id })
      setSelected(true)
      setNotice('캘린더에 기록했어요!')
    } catch (e) {
      setNotice('기록에 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSelecting(false)
    }
  }

  const steps = toLines((recipe as any).step_text)
  const tips  = toLines((recipe as any).step_tip)
  const ings  = toArray((recipe as any).ingredient_full)

  return (
    <FramePortal>
      <div className="rec-overlay" onClick={onClose}>
        <div className="rec-modal" onClick={e=>e.stopPropagation()}>
          <div className="rec-head">
            <h3>
              {recipe.recipe_nm_ko}
              {selected && <span className="chip ok">선택됨</span>}
              {cooked && <span className="chip cooked">요리함</span>}
            </h3>
            <button className="rec-x" onClick={onClose}>×</button>
          </div>

          {/* 인앱 안내 영역: 캘린더 탭에서 열렸다면(showSelect=false) 노출하지 않음 */}
          {showSelect && notice && (
            <div className={`inline-note ${selected ? 'ok' : 'warn'}`}>{notice}</div>
          )}

          <div className="rec-sub">
            {typeof (recipe as any).cooking_time === 'number' && <span>조리시간: {(recipe as any).cooking_time}분</span>}
            {(recipe as any).level_nm && (
              <span>난이도: {(recipe as any).level_nm}</span>
            )}
          </div>

          {/* 이하 기존 섹션들 그대로 */}
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
              <button
                className="btn primary"
                onClick={selectRecipe}
                disabled={selecting || selected}
              >
                {selected ? '이미 캘린더에 있어요' : (selecting ? '기록 중…' : '이 레시피 할래요')}
              </button>
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
