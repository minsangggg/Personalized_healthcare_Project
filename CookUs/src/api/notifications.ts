// src/api/notifications.ts  
import api from './axios'
import { getAccessToken } from './session'  // 토큰 꺼내오는 기존 헬퍼

export type NotificationRow = {
  notification_id: number
  user_id: string
  type: string
  related_id: number | null
  title: string
  body: string
  link_url: string | null
  created_at: string
  is_read: 0 | 1
}

export const notificationsAPI = {
  async list(): Promise<NotificationRow[]> {
    const { data } = await api.get('/me/notifications')
    return Array.isArray(data) ? data : []
  },
  async markRead(id: number): Promise<void> {
    await api.post(`/me/notifications/${id}/read`)
  },
  // ⬇️ 추가: SSE 스트림
  openStream(onMessage: (n: NotificationRow) => void) {
    const token = getAccessToken()
    const base = (api.defaults.baseURL || '').replace(/\/+$/, '')
    const url = `${base}/me/notifications/stream?access_token=${encodeURIComponent(token || '')}`
    const es = new EventSource(url)  // 헤더 불필요, 쿼리로 인증

    es.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data))
      } catch { /* ignore */ }
    }
    es.onerror = () => {
      // 네트워크가 끊기면 브라우저가 자동 재연결 시도
    }
    return () => es.close()
  },
}