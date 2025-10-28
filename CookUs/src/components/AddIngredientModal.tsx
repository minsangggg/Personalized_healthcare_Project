import { useEffect, useMemo, useState } from 'react'
import { fridgeAPI } from '../api/fridge'
import type { Ingredient } from '../api/fridge'
import './AddIngredientModal.css'

type Props = { onClose: (saved: boolean) => void }

export default function AddIngredientModal({ onClose }: Props) {
  // 검색
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Ingredient[]>([])

  const [picked, setPicked] = useState<Record<string, number>>({})

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

  // 검색 호출
  useEffect(() => {
    let cancel = false
    const run = async () => {
      if (!q.trim()) { setResults([]); return }
      setLoading(true)
      try {
        const r = await fridgeAPI.searchIngredients(q.trim())
        if (!cancel) setResults(r)
      } finally { if (!cancel) setLoading(false) }
    }
    run()
    return () => { cancel = true }
  }, [q])

  // 화면 표시용
  const pickedList: Ingredient[] = useMemo(
    () => Object.entries(picked).map(([name, quantity]) => ({ name, quantity })),
    [picked]
  )

  // 수량 조작
  const inc = (name: string, d = 1) =>
    setPicked(p => {
      const n = Math.max(1, (p[name] ?? 0) + d)
      return { ...p, [name]: n }
    })

  const setQty = (name: string, v: number) =>
    setPicked(p => ({ ...p, [name]: Math.max(1, v || 1) }))

  const remove = (name: string) =>
    setPicked(p => {
      const { [name]: _, ...rest } = p
      return rest
    })

  const addFromSearch = (name: string) =>
    setPicked(p => ({ ...p, [name]: p[name] ? p[name] + 1 : 1 }))

  const save = async () => {
    const items = pickedList
    await fridgeAPI.saveFridge(items, 'replace', true)
    onClose(true)
  }

  return (
    <div className="modal-backdrop" onClick={() => onClose(false)}>
      <div className="modal card" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={() => onClose(false)}>×</button>
        <h2>재료 관리</h2>

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
            <div style={{ opacity: .7 }}>검색 결과가 없습니다.</div>
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
        </div>

        {/* 내 재료 목록(수정/삭제) */}
        <h3 style={{ marginTop: 16 }}>내 재료</h3>
        {pickedList.length === 0 ? (
          <div style={{ opacity: .7 }}>현재 담긴 재료가 없습니다.</div>
        ) : (
          <div style={{ display: 'grid', gap: 4, marginTop: 8 }}>
            {pickedList.map(it => (
              <div key={it.name} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <div style={{ minWidth: 120 }}>{it.name}</div>
                <button className="btn secondary" onClick={() => inc(it.name, -1)}>-</button>
                <input
                  type="number"
                  min={1}
                  value={it.quantity ?? 1}
                  onChange={e => setQty(it.name, Number(e.target.value))}
                  style={{ width: 70, padding: '8px 10px', borderRadius: 8, border: '1px solid #e6e1d8' }}
                />
                <button className="btn secondary" onClick={() => inc(it.name, +1)}>+</button>
                <button className="btn" onClick={() => remove(it.name)}>삭제</button>
              </div>
            ))}
          </div>
        )}

        {/* 액션 */}
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button className="btn" onClick={save}>저장</button>
          <button className="btn secondary" onClick={() => onClose(false)}>취소</button>
        </div>
      </div>
    </div>
  )
}
