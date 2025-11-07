// src/api/axios.ts
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { getAccessToken, setAccessToken, clearAccessToken } from './session'

// Vite 프록시를 쓰면 baseURL은 빈 문자열이어도 됨.
const baseURL = ''

// 우리 앱에서 쓰는 공용 axios 인스턴스
const api = axios.create({
  baseURL,
  withCredentials: true, // refresh 쿠키 등 포함
})

// --- 요청 인터셉터: 항상 Authorization 헤더 붙이기 ---
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken?.()
  if (token) {
    config.headers = config.headers || {}
    ;(config.headers as any).Authorization = `Bearer ${token}`
  }
  return config
})

// --- 응답 인터셉터: 401이면 한 번만 refresh한 뒤 재시도 ---
let isRefreshing = false
let waitQueue: Array<(token: string | null) => void> = []

async function doRefresh(): Promise<string | null> {
  try {
    const resp = await axios.post(
      '/auth/refresh',
      {},
      { baseURL, withCredentials: true }
    )
    const access = resp.data?.accessToken ?? resp.data?.access_token ?? null
    if (access) setAccessToken(access)
    return access
  } catch {
    clearAccessToken()
    return null
  }
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean })

    // 401 아니면 그대로 던짐
    if (error.response?.status !== 401 || original?._retry) {
      throw error
    }

    // 중복 리프레시 방지
    original._retry = true

    if (!isRefreshing) {
      isRefreshing = true
      const newToken = await doRefresh()
      isRefreshing = false
      // 대기 중이던 요청들 재개
      waitQueue.forEach((resume) => resume(newToken))
      waitQueue = []
      if (!newToken) throw error // 리프레시 실패 → 그대로 401
      // 토큰 붙여 재시도
      original.headers = original.headers || {}
      ;(original.headers as any).Authorization = `Bearer ${newToken}`
      return api(original)
    }

    // 이미 리프레시 중이면 대기 후 재시도
    return new Promise((resolve, reject) => {
      waitQueue.push((token) => {
        if (!token) return reject(error)
        try {
          original.headers = original.headers || {}
          ;(original.headers as any).Authorization = `Bearer ${token}`
          resolve(api(original))
        } catch (e) {
          reject(e)
        }
      })
    })
  }
)

export default api
