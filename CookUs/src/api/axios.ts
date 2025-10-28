import axios, { AxiosHeaders } from 'axios'
import { getAccessToken, setAccessToken, clearAccessToken } from './session'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const t = getAccessToken()
  if (t) {
    if (!config.headers) config.headers = new AxiosHeaders()
    ;(config.headers as AxiosHeaders).set('Authorization', `Bearer ${t}`)
  }
  return config
})

let isRefreshing = false
let queue: Array<() => void> = []
const flush = () => { queue.forEach(fn=>fn()); queue=[] }

api.interceptors.response.use(
  (r)=>r,
  async (err)=>{
    const original = err.config
    if (err?.response?.status === 401 && !original?._retry) {
      original._retry = true
      if (isRefreshing) {
        await new Promise<void>(resolve => queue.push(resolve))
        return api(original)
      }
      try {
        isRefreshing = true
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        )
        const access = data?.accessToken ?? data?.access_token
        if (!access) throw new Error('no access token')
        setAccessToken(access)
        flush()
        return api(original)
      } catch (e) {
        clearAccessToken()
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(err)
  }
)

export default api
