import type { Recipe } from '../api/recipe'
import './RecipeCard.css'
import { useState } from 'react'
import { buildShortsOpenUrl } from '../api/shorts'

type Props = {
  recipe: Recipe
  onDetail: () => void
  onDelete?: () => Promise<void> | void // 옵션: 대시보드 등에서는 X 버튼 표시
  onSelect?: () => void
  selected?: boolean
}

export default function RecipeCard({ recipe, onDetail, onDelete, onSelect, selected = false }: Props){
  const [deleting, setDeleting] = useState(false)
  const top3 = top3Ingredients((recipe as any).ingredient_full)
  const selectable = typeof onSelect === 'function'

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onDelete) return
    if (!confirm('이 레시피를 삭제하시겠어요?')) return
    try {
      setDeleting(true)
      await onDelete()
    } finally {
      setDeleting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!selectable || !onSelect) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect()
    }
  }

  return (
    <div
      className={`rc-card${selectable ? ' selectable' : ''}${selected ? ' selected' : ''}`}
      onClick={selectable ? onSelect : undefined}
      role={selectable ? 'button' : undefined}
      tabIndex={selectable ? 0 : undefined}
      aria-pressed={selectable ? selected : undefined}
      onKeyDown={handleKeyDown}
    >
      <h3 className="rc-title clamp-2" style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:8}}>
        <span>{(recipe as any).recipe_nm_ko}</span>
      </h3>

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
        <a
          href={buildShortsOpenUrl((recipe as any).recipe_nm_ko)}
          target="_blank"
          rel="noreferrer"
          className="btn sm"
          onClick={(e)=>e.stopPropagation()}
          title="YouTube Shorts 열기"
        >
          Shorts
        </a>
        <button className="btn primary" onClick={(e)=>{ e.stopPropagation(); onDetail(); }}>자세히 보기</button>
        {onDelete && (
          <button
            className="btn danger outline"
            onClick={handleDelete}
            disabled={deleting}
            aria-label="삭제"
            title="삭제"
          >
            {deleting ? '삭제 중…' : 'X'}
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

