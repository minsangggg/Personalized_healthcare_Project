import type { Recipe } from '../api/recipe'
import './RecipeCard.css'

type Props = { recipe: Recipe; onDetail: () => void }

export default function RecipeCard({ recipe, onDetail }: Props){
  const top3 = top3Ingredients((recipe as any).ingredients_text ?? (recipe as any).ingredient_ful)

  return (
    <div className="rc-card">
      <h3 className="rc-title clamp-2">{recipe.title}</h3>

      <div className="rc-meta">
        {(recipe as any).difficulty && <span className="chip">{(recipe as any).difficulty}</span>}
        {typeof recipe.cook_time === 'number' && <span className="chip">{recipe.cook_time}분</span>}
      </div>

      <div className="rc-ings clamp-2">
        {top3.length ? top3.join(' · ') : '재료 정보 없음'}
      </div>

      <div className="rc-foot">
        <button className="btn primary" onClick={onDetail}>자세히 보기</button>
      </div>
    </div>
  )
}

function top3Ingredients(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(String).map(clean).filter(Boolean).slice(0, 3)
  }

  if (typeof raw === 'string') {
    const s = raw.trim()
    if ((s.startsWith('{') && s.endsWith('}')) || (s.startsWith('[') && s.endsWith(']'))) {
      try { return top3Ingredients(JSON.parse(s)) } catch {/* fallthrough */}
    }
    return s.split(/[,·\n]+/).map(clean).filter(Boolean).slice(0, 3)
  }

  if (raw && typeof raw === 'object') {
    return Object.entries(raw as Record<string, unknown>)
      .map(([k, v]) => {
        const kk = clean(k)
        const vv = (v == null ? '' : String(v)).trim()
        return vv ? `${kk} ${vv}` : kk
      })
      .map(clean)
      .filter(Boolean)
      .slice(0, 3)
  }

  return []
}

function clean(s: string){ return String(s || '').replace(/\s+/g, ' ').trim() }
