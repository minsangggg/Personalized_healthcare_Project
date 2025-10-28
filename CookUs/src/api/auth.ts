import api from './axios'
import { setAccessToken, clearAccessToken } from './session'

export type User = { user_id: string; user_name: string }
export type SignupPayload = { /* 동일 */ }

export const authAPI = {
  login: async (id: string, password: string) => {
    const { data } = await api.post('/auth/login', { id, password })
    const access = data?.accessToken ?? data?.access_token
    if (access) setAccessToken(access)
    return data
  },
  logout: async () => {
    try { await api.post('/auth/logout') } finally { clearAccessToken() }
  },
  signup: async (payload: SignupPayload) => { await api.post('/auth/signup', payload) },
  me: async () => { const { data } = await api.get<User>('/me'); return data },

  init: async () => {
    try {
      const { data } = await api.post('/auth/refresh', {})
      const access = data?.accessToken ?? data?.access_token
      if (access) setAccessToken(access)
      return true
    } catch { return false }
  }
}
