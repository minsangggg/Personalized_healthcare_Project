import type { Recipe } from '../api/recipe'
import './RecipeCard.css'
import { useState } from 'react'

type Props = {
  recipe: Recipe
  onDetail: () => void
  onDelete?: () => Promise<void> | void // 옵션: 삭제 콜백이 있으면 X 버튼 노출
}

export default function RecipeCard({ recipe, onDetail, onDelete }: Props){
  const [deleting, setDeleting] = useState(false)
  const top3 = top3Ingredients((recipe as any).ingredient_full)

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onDelete) return
    if (!confirm('이 항목을 삭제하시겠어요?')) return
    try {
      setDeleting(true)
      await onDelete()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="rc-card">
      <h3 className="rc-title clamp-2">{(recipe as any).recipe_nm_ko}</h3>

      <div className="rc-meta">
        {(recipe as any).level_nm && (
          <span className="chip">{(recipe as any).level_nm}</span>
        )}
        {typeof (recipe as any).cooking_time === 'number' && <span className="chip">{(recipe as any).cooking_time}분</span>}
      </div>

      <div className="rc-ings clamp-2">
        {top3.length ? top3.join(' · ') : '재료 정보 없음'}
      </div>

      <div className="rc-foot">
        <button className="btn primary" onClick={onDetail}>자세히 보기</button>
        {onDelete && (
          <button
            className="btn danger outline"
            onClick={handleDelete}
            disabled={deleting}
            aria-label="삭제"
            title="삭제"
          >
            {deleting ? '삭제 중…' : '×'}
          </button>
        )}
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
