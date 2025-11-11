import api from './axios'
import { setAccessToken, clearAccessToken } from './session'

export type User = {
  user_id: string
  user_name: string
  email?: string
  gender?: 'male' | 'female' | string
  date_of_birth?: string | null
  goal?: number | null
  displayed_badge_id?: number | null
  cooking_level?: '초보' | '중수' | string
}

export type UpdateMePayload = Partial<{
  user_name: string
  email: string
  gender: 'male' | 'female'
  date_of_birth: string | null   // 'YYYY-MM-DD'
  goal: number | null
  cooking_level: '상' | '하'
}>

export const authAPI = {
  login: async (id: string, password: string) => {
    const { data } = await api.post('/auth/login', { id, password })
    const access = data?.accessToken ?? data?.access_token
    if (access) setAccessToken(access)
    return data
  },
  logout: async () => { try { await api.post('/auth/logout') } finally { clearAccessToken() } },
  deleteMe: async (password: string, password_confirm: string) => {
    await api.delete('/me/delete', { data: { password, password_confirm } })
    clearAccessToken()
  },
  signup: async (payload: any) => { await api.post('/auth/signup', payload) },
  me: async () => { const { data } = await api.get<User>('/me'); return data },

  init: async () => {
    try {
      const { data } = await api.post('/auth/refresh', {})
      const access = data?.accessToken ?? data?.access_token
      if (access) setAccessToken(access)
      return true
    } catch { return false }
  },

  updateMe: async (payload: UpdateMePayload) => {
    const { data } = await api.put<User>('/me', payload)
    return data
  },

  // ── 아이디 찾기 ──────────────────────────
  sendFindIdCode: async (email: string, username?: string) => {
    const { data } = await api.post('/auth/find-id', { email, username })
    return data as { ok: boolean; dev_code?: string; expires_in_sec?: number }
  },
  verifyFindIdCode: async (email: string, code: string) => {
    const { data } = await api.post('/auth/find-id/verify', { email, code })
    return data as { user_id: string }
  },

  // ── 비밀번호 찾기/변경 ───────────────────
  sendFindPwCode: async (id: string, email: string) => {
    const { data } = await api.post('/auth/find-password', { id, email })
    return data as { ok: boolean; dev_code?: string; expires_in_sec?: number }
  },
  setNewPassword: async (id: string, email: string, code: string, new_password: string) => {
    const { data } = await api.put('/auth/password-set', { id, email, code, new_password })
    return data as { ok: boolean }
  },
}



