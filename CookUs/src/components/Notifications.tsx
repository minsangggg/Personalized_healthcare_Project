// src/components/Notifications.tsx
import { useEffect, useRef, useState } from 'react'
import { notificationsAPI, type NotificationRow } from '../api/notifications'
import BadgeAwardPopup from './badges/BadgeAwardPopup'

function dedupeAndSort(list: NotificationRow[]): NotificationRow[] {
  const map = new Map<number, NotificationRow>()
  for (const n of list) map.set(n.notification_id, n)
  return Array.from(map.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
}

export default function Notifications({ isLoggedIn }: { isLoggedIn: boolean }) {
  const [open, setOpen] = useState(false)
  const [list, setList] = useState<NotificationRow[]>([])
  const [badgeQueue, setBadgeQueue] = useState<NotificationRow[]>([])
  const [activeBadge, setActiveBadge] = useState<NotificationRow | null>(null)
  const pollTimerRef = useRef<number | null>(null)
  const closeStreamRef = useRef<(() => void) | null>(null)
  const badgeSeenRef = useRef<Set<number>>(new Set())
  const initialBadgeSnapshotRef = useRef(false)

  const handleBadgeCandidate = (n: NotificationRow) => {
    if (n.type !== 'badge') return
    if (badgeSeenRef.current.has(n.notification_id)) return
    badgeSeenRef.current.add(n.notification_id)
    setBadgeQueue(prev => [...prev, n])
  }

  const fetchOnce = async () => {
    try {
      const rows = await notificationsAPI.list()
      setList(prev => dedupeAndSort([...rows, ...prev])) // 초기 목록 + 중복 제거

      if (!initialBadgeSnapshotRef.current) {
        rows.forEach(n => {
          if (n.type === 'badge') badgeSeenRef.current.add(n.notification_id)
        })
        initialBadgeSnapshotRef.current = true
      } else {
        rows.forEach(handleBadgeCandidate)
      }
    } catch (e) {
      console.log('notifications fetch failed', e)
    }
  }

  useEffect(() => {
    // 로그아웃한 경우: 정리
    if (!isLoggedIn) {
      setList([])
      if (pollTimerRef.current) window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
      if (closeStreamRef.current) closeStreamRef.current()
      closeStreamRef.current = null
      badgeSeenRef.current.clear()
      initialBadgeSnapshotRef.current = false
      setBadgeQueue([])
      setActiveBadge(null)
      return
    }

    // 1) 최초 1회 로드
    fetchOnce()

    // 2) SSE 스트림 듣기 (실시간)
    closeStreamRef.current = notificationsAPI.openStream((n) => {
      setList(prev => dedupeAndSort([n, ...prev]))
      handleBadgeCandidate(n)
    })

    // 3) 보강망으로 30초 간격 폴링(혹시 SSE 가로막힐 경우 대비)
    pollTimerRef.current = window.setInterval(fetchOnce, 30000)

    // 정리
    return () => {
      if (pollTimerRef.current) window.clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
      if (closeStreamRef.current) closeStreamRef.current()
      closeStreamRef.current = null
    }
  }, [isLoggedIn])

  const unread = list.filter(n => !n.is_read).length

  useEffect(() => {
    if (!activeBadge && badgeQueue.length > 0) {
      setActiveBadge(badgeQueue[0])
      setBadgeQueue(prev => prev.slice(1))
    }
  }, [badgeQueue, activeBadge])

  const handleItemClick = async (n: NotificationRow) => {
    if (n.is_read) return
    setList(prev => prev.map(it => it.notification_id === n.notification_id ? { ...it, is_read: 1 } : it))
    try {
      await notificationsAPI.markRead(n.notification_id)
    } catch (e) {
      setList(prev => prev.map(it => it.notification_id === n.notification_id ? { ...it, is_read: 0 } : it))
    }
  }

  return (
    <div className="noti">
      <button className="bell" onClick={() => setOpen(v => !v)} title="알림">
        🔔{unread > 0 && <span className="badge">{unread}</span>}
      </button>
      {open && (
        <div className="dropdown">
          {list.length === 0 ? (
            <div className="empty">알림이 없어요</div>
          ) : (
            list.map(n => (
              <div
                key={n.notification_id}
                className={`item ${n.is_read ? '' : 'unread'}`}
                onClick={() => handleItemClick(n)}
                title={n.is_read ? '읽은 알림' : '읽지 않은 알림'}
              >
                <div className="title">{n.title}</div>
                <div className="body">{n.body}</div>
                <div className="time">{new Date(n.created_at).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
      )}
      {activeBadge && (
        <BadgeAwardPopup notification={activeBadge} onClose={() => setActiveBadge(null)} />
      )}
    </div>
  )
}
