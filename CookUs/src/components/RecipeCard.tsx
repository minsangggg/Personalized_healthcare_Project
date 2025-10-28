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

/** 상위 3개 재료 추출: dict -> key 순서, array -> 앞에서 3개, string -> 구분자 기준 */
function top3Ingredients(raw: unknown): string[] {
  // 이미 배열
  if (Array.isArray(raw)) {
    return raw.map(String).map(clean).filter(Boolean).slice(0, 3)
  }

  // 문자열(JSON일 수도, 그냥 나열일 수도)
  if (typeof raw === 'string') {
    const s = raw.trim()
    // JSON 형태면 파싱 시도
    if ((s.startsWith('{') && s.endsWith('}')) || (s.startsWith('[') && s.endsWith(']'))) {
      try { return top3Ingredients(JSON.parse(s)) } catch {/* fallthrough */}
    }
    // 나열 문자열: 쉼표/점/개행 등 구분
    return s.split(/[,·\n]+/).map(clean).filter(Boolean).slice(0, 3)
  }

  // 객체(dict)면 key 기준(값이 있으면 양 옆 공백 제거해서 붙여줌)
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
