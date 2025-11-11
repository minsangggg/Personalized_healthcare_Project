import { useEffect, useMemo, useState } from 'react'
import { fridgeAPI } from '../api/fridge'
import type { Ingredient } from '../api/fridge'
import './AddIngredientModal.css'

type Props = { onClose: (saved: boolean) => void }

type UnitMeta = {
  unit: '개' | 'g' | 'ml'
  step: number
}

const SPECIFIC_UNIT_MAP: Record<string, UnitMeta> = {
  파스타면: { unit: 'g', step: 100 },
  '소고기 안심': { unit: 'g', step: 100 },
  '돼지고기 안심': { unit: 'g', step: 100 },
  닭가슴살: { unit: 'g', step: 100 },
  휘핑크림: { unit: 'ml', step: 100 },
  생크림: { unit: 'ml', step: 100 },
}

const LIQUID_KEYWORDS = ['물', '주스', '소스', '오일', '식용유', '식초', '청', '육수', '국물', '우유', '크림', '액', '드레싱']
const WEIGHT_KEYWORDS = ['고기', '살', '육', '가루', '분말', '쌀', '파스타', '면', '버터', '치즈', '햄', '베이컨']
const defaultMeta: UnitMeta = { unit: '개', step: 1 }

const getUnitMeta = (name: string): UnitMeta => {
  if (!name) return defaultMeta
  const exact = SPECIFIC_UNIT_MAP[name.trim()]
  if (exact) return exact
  const normalized = name.replace(/\s+/g, '').toLowerCase()
  if (LIQUID_KEYWORDS.some(k => normalized.includes(k))) {
    return { unit: 'ml', step: 100 }
  }
  if (WEIGHT_KEYWORDS.some(k => normalized.includes(k))) {
    return { unit: 'g', step: 100 }
  }
  return defaultMeta
}

export default function AddIngredientModal({ onClose }: Props) {
  // 검색
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Ingredient[]>([])
  const [showCustomPrompt, setShowCustomPrompt] = useState(false)
  const [addingCustom, setAddingCustom] = useState(false)
  const [customError, setCustomError] = useState<string | null>(null)
  const [customInfo, setCustomInfo] = useState<string | null>(null)

  const [picked, setPicked] = useState<Record<string, number>>({})
  const trimmedQuery = q.trim()

  useEffect(() => {
    (async () => {
      try {
        const cur = await fridgeAPI.listFridge()
        const map: Record<string, number> = {}
        cur.forEach(it => {
          const qty = typeof it.quantity === 'number' && it.quantity! > 0 ? it.quantity! : 1
          if (it.name) map[it.name] = qty
        })
        setPicked(map)
      } catch {}
    })()
  }, [])

  useEffect(() => {
    setShowCustomPrompt(false)
    setCustomError(null)
    setCustomInfo(null)
  }, [trimmedQuery])

  // 검색 호출
  useEffect(() => {
    let cancel = false
    const run = async () => {
      if (!trimmedQuery) { setResults([]); return }
      setLoading(true)
      try {
        const r = await fridgeAPI.searchIngredients(trimmedQuery)
        if (!cancel) setResults(r)
      } finally { if (!cancel) setLoading(false) }
    }
    run()
    return () => { cancel = true }
  }, [trimmedQuery])

  const pickedList = useMemo(
    () => Object.entries(picked).map(([name, quantity]) => ({ name, quantity, meta: getUnitMeta(name) })),
    [picked]
  )

  const adjustQty = (name: string, stepDelta: number) =>
    setPicked(p => {
      const meta = getUnitMeta(name)
      const current = p[name] ?? meta.step
      const next = Math.max(meta.step, current + stepDelta * meta.step)
      return { ...p, [name]: next }
    })

  const setQty = (name: string, v: number) =>
    setPicked(p => {
      const meta = getUnitMeta(name)
      const step = meta.step
      const valid = Number.isFinite(v) ? Math.max(step, v) : step
      const rounded = Math.round(valid / step) * step
      return { ...p, [name]: rounded || step }
    })

  const remove = (name: string) =>
    setPicked(p => {
      const { [name]: _, ...rest } = p
      return rest
    })

  const addFromSearch = (name: string) =>
    setPicked(p => {
      const meta = getUnitMeta(name)
      const current = p[name]
      const next = current ? current + meta.step : meta.step
      return { ...p, [name]: next }
    })

  const confirmCustomIngredient = async () => {
    if (!trimmedQuery) return
    setAddingCustom(true)
    setCustomError(null)
    try {
      const { registered } = await fridgeAPI.addIngredientName(trimmedQuery)
      addFromSearch(trimmedQuery)
      setResults([{ name: trimmedQuery } as Ingredient])
      if (!registered) {
        setCustomInfo('검색 목록에는 추후에 반영될 수 있어요.')
      } else {
        setCustomInfo(null)
      }
      setShowCustomPrompt(false)
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? '추가에 실패했어요.'
      setCustomError(detail)
    } finally {
      setAddingCustom(false)
    }
  }

  const save = async () => {
    const items: Ingredient[] = pickedList.map(({ name, quantity }) => ({ name, quantity }))
    await fridgeAPI.saveFridge(items, 'replace', true)
    onClose(true)
  }

  return (
    <div className="modal-backdrop" onClick={() => onClose(false)}>
      <div className="modal card" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={() => onClose(false)}>×</button>
        <h2>[재료 관리]</h2>

        {/* 검색 */}
        <div className="form" style={{ marginTop: 8 }}>
          <label>재료 검색</label>
          <input
            placeholder="예) 양파, 당근, 파"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>

        {/* 검색 결과 */}
        <div style={{ marginTop: 10 }}>
          {loading ? (
            <div>검색 중…</div>
          ) : results.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, opacity: .9 }}>
              <div>검색 결과가 없습니다.</div>
              {trimmedQuery && (
                showCustomPrompt ? (
                  <div className="custom-add-panel">
                    <div>새 재료 '{trimmedQuery}'를 추가할까요?</div>
                    <div className="custom-add-actions">
                      <button className="btn" onClick={confirmCustomIngredient} disabled={addingCustom}>
                        {addingCustom ? '추가 중…' : '추가'}
                      </button>
                      <button className="btn secondary" onClick={() => setShowCustomPrompt(false)} disabled={addingCustom}>
                        취소
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    className="btn"
                    style={{ alignSelf: 'flex-start' }}
                    onClick={() => setShowCustomPrompt(true)}
                  >
                    {`+'${trimmedQuery}' 추가`}
                  </button>
                )
              )}
              {customError && <div className="error">{customError}</div>}
              {customInfo && <div className="hint small">{customInfo}</div>}
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 4 }}>
              {results.map(r => (
                <button
                  key={r.name}
                  className="btn"
                  style={{ justifySelf: 'start' }}
                  onClick={() => addFromSearch(r.name)}
                >
                  + {r.name}
                </button>
              ))}
            </div>
          )}
          {results.length > 0 && customInfo && (
            <div className="hint small" style={{ marginTop: 6 }}>{customInfo}</div>
          )}
        </div>

        {/* 내 재료 목록 */}
        <h3 style={{ marginTop: 16 }}>내 재료</h3>
        {pickedList.length === 0 ? (
          <div style={{ opacity: .7 }}>현재 담긴 재료가 없습니다.</div>
        ) : (
          <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
            {pickedList.map(it => (
              <div key={it.name} className="ingredient-row">
                <div className="ingredient-name">{it.name}</div>
                <button className="btn secondary" onClick={() => adjustQty(it.name, -1)}>-</button>
                <input
                  type="number"
                  min={it.meta.step}
                  step={it.meta.step}
                  value={it.quantity ?? it.meta.step}
                  onChange={e => setQty(it.name, Number(e.target.value))}
                  className="qty-input"
                />
                <span className="ingredient-unit">{it.meta.unit}</span>
                <button className="btn secondary" onClick={() => adjustQty(it.name, +1)}>+</button>
                <button className="btn" onClick={() => remove(it.name)}>삭제</button>
              </div>
            ))}
          </div>
        )}

        {/* 액션 */}
        <div style={{ display: 'flex', gap: 8, marginTop: 20, marginLeft: 130 }}>
          <button className="btn" onClick={save}>저장</button>
          <button className="btn secondary" onClick={() => onClose(false)}>취소</button>
        </div>
      </div>
    </div>
  )
}
