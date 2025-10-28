import { useEffect, useMemo, useState } from 'react'
import { recipeAPI, type SelectedRecipesResponse } from '../api/recipe'
import './Calendar.css'

type CalendarProps = { isLoggedIn: boolean }
type Row = SelectedRecipesResponse['recipes'][number]
type Grouped = Array<[string, Row[]]>

export default function Calendar({ isLoggedIn }: CalendarProps) {
  const [data, setData] = useState<SelectedRecipesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const run = async () => {
      if (!isLoggedIn) { setData(null); return }
      const raw = localStorage.getItem('user')
      const uid = raw ? (JSON.parse(raw)?.user_id as string) : null
      if (!uid) return
      setLoading(true); setError(null)
      try {
        const res = await recipeAPI.getSelected(uid)
        if (alive) setData(res)
      } catch {
        if (alive) setError('기록을 불러오지 못했습니다.')
      } finally {
        if (alive) setLoading(false)
      }
    }
    run()
    return () => { alive = false }
  }, [isLoggedIn])

  const grouped = useMemo<Grouped>(() => {
    const map = new Map<string, Row[]>()
    for (const r of data?.recipes ?? []) {
      const d = (r.selected_date ?? '').slice(0, 10) || '날짜없음'
      const arr = map.get(d) ?? []
      arr.push(r)
      map.set(d, arr)
    }
    // 최신 날짜가 위로 오게 정렬
    return Array.from(map.entries()).sort((a, b) => (a[0] < b[0] ? 1 : -1))
  }, [data])

  return (
    <section className="app-tab cal">
      <div className="card cal-card">
        <h2 className="title">요리 기록</h2>

        {!isLoggedIn && <div className="muted">로그인하면 기록을 볼 수 있어요.</div>}
        {isLoggedIn && loading && <div className="muted">불러오는 중…</div>}
        {isLoggedIn && error && <div className="error">{error}</div>}

        {isLoggedIn && !loading && !error && (data?.count ?? 0) === 0 && (
          <div className="empty">아직 기록이 없습니다. 레시피를 선택해 보세요!</div>
        )}

        {isLoggedIn && !loading && !error && (data?.count ?? 0) > 0 && (
          <div className="days">
            {grouped.map(([day, arr]) => (
              <div key={day} className="day">
                <div className="day-head">{day}</div>
                <ul className="list">
                  {arr.map((r) => (
                    <li key={r.selected_id} className="row">
                      <div className="title clamp-1">{r.title}</div>
                      <div className="meta">
                        {r.difficulty ?? '—'} · {r.cooking_time ?? '—'}분
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
