// src/api/notifications.ts  (새 파일)
import api from './axios'

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
}
