import { useEffect, useMemo, useState } from 'react'
import { cooktestAPI, type EventSummary } from '../api/cooktest'
import './CookTest.css'
import CookTestDetailModal from '../components/CookTestDetailModal'

type Props = {
  isLoggedIn: boolean
  onRequireLogin: () => void
  userId?: string
}

type StatusFilter = 'all' | 'ongoing' | 'upcoming' | 'closed'

export default function CookTest({ isLoggedIn, onRequireLogin, userId }: Props) {
  const [events, setEvents] = useState<EventSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeEventId, setActiveEventId] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [mineOnly, setMineOnly] = useState(false)

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

  const filteredEvents = useMemo(() => {
    const list = Array.isArray(events) ? events : []
    return list.filter(ev => {
      const status = getEventStatus(ev)
      if (statusFilter !== 'all' && status !== statusFilter) return false
      if (mineOnly && !isParticipated(ev)) return false
      return true
    })
  }, [events, statusFilter, mineOnly])

  return (
    <section className="app-tab cooktest">
      <div className="cooktest-header">
        <h2>Cooktest</h2>
        <p className="muted">자신만의 레시피를 뽐내보세요!</p>
      </div>

      <div className="cooktest-controls">
        <label className="filter-select">
          <span>대회 상태</span>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as StatusFilter)}>
            <option value="all">전체</option>
            <option value="ongoing">진행중</option>
            <option value="upcoming">진행예정</option>
            <option value="closed">마감</option>
          </select>
        </label>
        <button type="button" className={`filter-toggle ${mineOnly ? 'active' : ''}`} onClick={() => setMineOnly(v => !v)}>
          내가 참여한 대회 보기
        </button>
      </div>

      {loading && <div className="hint">불러오는 중…</div>}
      {error && <div className="error">{error}</div>}

      <div className="event-grid">
        {filteredEvents.map(ev => {
          const status = getEventStatus(ev)
          const statusLabel = getStatusLabel(status)
          const participated = isParticipated(ev)
          return (
            <button key={ev.event_id} className="event-card" onClick={() => setActiveEventId(ev.event_id)}>
              <div className={`event-ribbon status-${status}`}>
                <span>{statusLabel}</span>
              </div>
              <div className="event-title">{ev.event_name}</div>
              <div className="event-dates">
                <span>{formatDate(ev.start_date)} ~ {formatDate(ev.end_date)}</span>
              </div>
              <div className="event-meta">
                <span>참여글 {ev.post_count}건</span>
                {participated && <span className="event-badge">내가 참여</span>}
              </div>
            </button>
          )
        })}
        {!loading && filteredEvents.length === 0 && (
          <div className="hint">현재 조회할 대회가 없습니다.</div>
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

type EventStatus = 'ongoing' | 'upcoming' | 'closed'

function formatDate(s: string) {
  try {
    const d = new Date(s)
    return d.toLocaleDateString()
  } catch {
    return s
  }
}

function getEventStatus(ev: EventSummary): EventStatus {
  const now = Date.now()
  const start = new Date(ev.start_date).getTime()
  const end = new Date(ev.end_date).getTime()
  if (Number.isFinite(start) && now < start) return 'upcoming'
  if (Number.isFinite(end) && now > end) return 'closed'
  return 'ongoing'
}

function getStatusLabel(status: EventStatus) {
  switch (status) {
    case 'upcoming':
      return '진행예정'
    case 'closed':
      return '마감'
    default:
      return '진행중'
  }
}

function isParticipated(ev: EventSummary) {
  const flags = [
    (ev as any).participated,
    (ev as any).is_participated,
    (ev as any).joined,
    ev.participated,
  ]
  return flags.some(v => v === true || v === 1 || v === '1')
}
