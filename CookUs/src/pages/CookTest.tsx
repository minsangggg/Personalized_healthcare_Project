import { useEffect, useMemo, useState } from 'react'
import { cooktestAPI, type EventSummary } from '../api/cooktest'
import './CookTest.css'
import CookTestDetailModal from '../components/CookTestDetailModal'

type EventStatus = 'ongoing' | 'upcoming' | 'closed'

const STATUS_LABELS: Record<EventStatus, string> = {
  ongoing: '진행중',
  upcoming: '진행예정',
  closed: '마감',
}

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
  const [statusFilter, setStatusFilter] = useState<EventStatus | 'all'>('all')
  const [participatedOnly, setParticipatedOnly] = useState(false)
  const [participatedEventIds, setParticipatedEventIds] = useState<Set<number>>(new Set())
  const [needsParticipationProbe, setNeedsParticipationProbe] = useState(false)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const list = await cooktestAPI.listEvents()
        setEvents(list)
      } catch (e: any) {
        setError(e?.message ?? '이벤트를 불러오는 데 실패했습니다.')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!isLoggedIn || !userId) {
      setParticipatedEventIds(new Set())
      setNeedsParticipationProbe(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const { events: myEvents, posts } = await cooktestAPI.listUserPosts(userId)
        if (cancelled) return
        const next = new Set<number>()
        if (Array.isArray(myEvents)) myEvents.forEach(ev => next.add(Number(ev.event_id)))
        if (Array.isArray(posts)) posts.forEach(p => next.add(Number(p.event_id)))
        setParticipatedEventIds(next)
        setNeedsParticipationProbe(false)
      } catch (err: any) {
        if (cancelled) return
        if (err?.response?.status === 404) {
          setParticipatedEventIds(new Set())
          setNeedsParticipationProbe(true)
        } else {
          setParticipatedEventIds(new Set())
          setNeedsParticipationProbe(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isLoggedIn, userId])

  useEffect(() => {
    if (!needsParticipationProbe || !isLoggedIn || !userId) return
    if (!Array.isArray(events) || events.length === 0) return
    let cancelled = false
    ;(async () => {
      const next = new Set<number>()
      const eventIds = events.map(ev => Number(ev.event_id)).filter(id => Number.isFinite(id))
      for (const eventId of eventIds) {
        if (cancelled) return
        try {
          const mine = await cooktestAPI.listPosts(eventId, 'mine')
          if (mine && mine.length > 0) next.add(eventId)
        } catch (err: any) {
          if (err?.response?.status === 401) {
            if (!cancelled) {
              setNeedsParticipationProbe(false)
              onRequireLogin()
            }
            return
          }
        }
      }
      if (!cancelled) {
        setParticipatedEventIds(next)
        setNeedsParticipationProbe(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [needsParticipationProbe, events, isLoggedIn, userId, onRequireLogin])

  const filteredEvents = useMemo(
    () => filterEvents(events, statusFilter, participatedOnly, participatedEventIds),
    [events, statusFilter, participatedOnly, participatedEventIds],
  )

  const noEvents = !loading && filteredEvents.length === 0

  return (
    <section className="app-tab cooktest">
      <div className="cooktest-header">
        <h2>Cooktest</h2>
        <p className="muted">나만의 요리를 뽐내보세요!</p>
      </div>

      {loading && <div className="hint">불러오는 중...</div>}
      {error && <div className="error">{error}</div>}

      <div className="cooktest-controls">
        <label className="filter-select">
          <span>진행 상태</span>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as EventStatus | 'all')}>
            <option value="all">전체</option>
            <option value="ongoing">진행중</option>
            <option value="upcoming">진행예정</option>
            <option value="closed">마감</option>
          </select>
        </label>
        <button
          type="button"
          className={`filter-toggle ${participatedOnly ? 'active' : ''}`}
          onClick={() => {
            if (!isLoggedIn) {
              onRequireLogin()
              return
            }
            setParticipatedOnly(prev => !prev)
          }}
        >
          내가 참여한 대회만
        </button>
      </div>

      <div className="event-grid">
        {filteredEvents.map(ev => {
          const status = getEventStatus(ev)
          const participated = hasParticipated(ev, participatedEventIds)
          return (
            <button key={ev.event_id} className="event-card" onClick={() => setActiveEventId(ev.event_id)}>
              <div className={`event-ribbon status-${status}`}>
                <span>{STATUS_LABELS[status]}</span>
              </div>
              <div className="event-title">{ev.event_name}</div>
              <div className="event-dates">
                <span>
                  {formatDate(ev.start_date)} ~ {formatDate(ev.end_date)}
                </span>
              </div>
              <div className="event-meta">
                <span>참여글 {ev.post_count}건</span>
                {participated && <span className="event-badge">내가 참여</span>}
              </div>
            </button>
          )
        })}
        {noEvents && <div className="hint">조건에 맞는 대회가 없습니다.</div>}
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

function filterEvents(
  events: EventSummary[],
  statusFilter: EventStatus | 'all',
  participatedOnly: boolean,
  participatedIds: Set<number>,
) {
  return (Array.isArray(events) ? events : []).filter(ev => {
    const status = getEventStatus(ev)
    if (statusFilter !== 'all' && status !== statusFilter) return false
    const participated = hasParticipated(ev, participatedIds)
    if (participatedOnly && !participated) return false
    return true
  })
}

function getEventStatus(ev: Pick<EventSummary, 'start_date' | 'end_date'>): EventStatus {
  const now = Date.now()
  const start = Date.parse(ev.start_date)
  const end = Date.parse(ev.end_date)
  if (Number.isFinite(end) && now > end) return 'closed'
  if (Number.isFinite(start) && now < start) return 'upcoming'
  return 'ongoing'
}

function formatDate(s: string) {
  try {
    const d = new Date(s)
    return d.toLocaleDateString()
  } catch {
    return s
  }
}

function hasParticipated(ev: EventSummary, participatedIds?: Set<number>) {
  if (participatedIds?.has(Number(ev.event_id))) return true
  const candidates = [
    ev.participated,
    (ev as any)?.is_participated,
    (ev as any)?.joined,
    (ev as any)?.has_participated,
    (ev as any)?.participated_flag,
  ]
  return candidates.some(value => interpretParticipation(value))
}

function interpretParticipation(value: unknown) {
  if (value === null || value === undefined) return false
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (!normalized) return false
    return normalized !== '0' && normalized !== 'false' && normalized !== 'no' && normalized !== 'n'
  }
  return Boolean(value)
}
