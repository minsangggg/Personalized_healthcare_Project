import api from './axios'

export const usersAPI = {
  async getDisplayedBadge(userId: string | number) {
    const { data } = await api.get<{ badge_id: number | null }>(`/users/${encodeURIComponent(String(userId))}/displayed-badge`)
    return data
  },
}
