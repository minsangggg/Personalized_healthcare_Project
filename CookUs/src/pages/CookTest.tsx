import { useEffect, useState } from 'react'
import { cooktestAPI, type EventSummary } from '../api/cooktest'
import './CookTest.css'
import CookTestDetailModal from '../components/CookTestDetailModal'

type Props = {
  isLoggedIn: boolean
  onRequireLogin: () => void
  userId?: string
}

export default function CookTest({ isLoggedIn, onRequireLogin, userId }: Props) {
  const [events, setEvents] = useState<EventSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeEventId, setActiveEventId] = useState<number | null>(null)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const list = await cooktestAPI.listEvents()
        setEvents(list)
      } catch (e: any) {
        setError(e?.message ?? '이벤트를 불러오지 못했습니다')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <section className="app-tab cooktest">
      <div className="cooktest-header">
        <h2>Cooktest</h2>
        <p className="muted">자신만의 레시피를 뽐내보세요!</p>
      </div>

      {loading && <div className="hint">불러오는 중…</div>}
      {error && <div className="error">{error}</div>}

      <div className="event-grid">
        {(Array.isArray(events) ? events : []).map(ev => (
          <button key={ev.event_id} className="event-card" onClick={() => setActiveEventId(ev.event_id)}>
            <div className="event-title">{ev.event_name}</div>
            <div className="event-dates">
              <span>{formatDate(ev.start_date)} ~ {formatDate(ev.end_date)}</span>
            </div>
            <div className="event-meta">참가수 {ev.post_count}개</div>
          </button>
        ))}
        {!loading && (!Array.isArray(events) || events.length === 0) && (
          <div className="hint">진행 중인 대회가 없습니다.</div>
        )}
      </div>

      {activeEventId !== null && (
        <CookTestDetailModal
          eventId={activeEventId}
          onClose={() => setActiveEventId(null)}
          isLoggedIn={isLoggedIn}
          onRequireLogin={onRequireLogin}
          userId={userId}
        />
      )}
    </section>
  )
}

function formatDate(s: string) {
  try {
    const d = new Date(s)
    return d.toLocaleDateString()
  } catch {
    return s
  }
}
