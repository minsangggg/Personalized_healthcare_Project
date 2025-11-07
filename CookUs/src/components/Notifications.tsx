// src/components/Notifications.tsx
import { useEffect, useRef, useState } from 'react'
import { notificationsAPI, type NotificationRow } from '../api/notifications'

export default function Notifications({ isLoggedIn }: { isLoggedIn: boolean }) {
  const [open, setOpen] = useState(false)
  const [list, setList] = useState<NotificationRow[]>([])
  const timerRef = useRef<number | null>(null)

  const fetchOnce = async () => {
    try {
      const rows = await notificationsAPI.list()
      setList(rows)
    } catch (e) {
      // 네트워크 탭에서 /me/notifications 확인해봐
      console.log('notifications fetch failed', e)
    }
  }

  useEffect(() => {
    // 로그인 전엔 폴링 X
    if (!isLoggedIn) {
      setList([])
      if (timerRef.current) window.clearInterval(timerRef.current)
      timerRef.current = null
      return
    }
    // 즉시 1회 + 주기 폴링
    fetchOnce()
    timerRef.current = window.setInterval(fetchOnce, 5000)
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [isLoggedIn])

  const unread = list.filter(n => !n.is_read).length

  const handleItemClick = async (n: NotificationRow) => {
    // 이미 읽은 항목이면 무시
    if (n.is_read) return
    // 낙관적 업데이트: UI 먼저 반영
    setList(prev => prev.map(it => it.notification_id === n.notification_id ? { ...it, is_read: 1 } : it))
    try {
      await notificationsAPI.markRead(n.notification_id)
    } catch (e) {
      // 실패 시 되돌리기 (조용히)
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
    </div>
  )
}
