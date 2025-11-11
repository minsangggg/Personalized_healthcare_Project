import api from './axios'
import { extractCookUserId } from '../utils/cooktest'

export type EventSummary = {
  event_id: number
  event_name: string
  event_description?: string
  start_date: string
  end_date: string
  post_count: number
  participated?: boolean
}

export type EventDetail = {
  event_id: number
  event_name: string
  event_description: string
  start_date: string
  end_date: string
}

export type CookPost = {
  post_id: number
  event_id: number
  user_id: number
  user_name?: string
  content_title: string
  content_text: string
  img_url: string | null
  img_urls?: string[]
  likes: number
  created_at: string
}

export type UserCookPost = CookPost & {
  event_name?: string
  liked_by_me?: boolean
}

export type UserCookEvent = {
  event_id: number
  event_name: string
  start_date?: string
  end_date?: string
}

export type UserCookPostsResponse = {
  posts: UserCookPost[]
  events: UserCookEvent[]
}

export type CreatePostDto = {
  content_title: string
  content_text: string
  img_url?: string | null
  img_urls?: string[]
}

export const cooktestAPI = {
  async listEvents(): Promise<EventSummary[]> {
    const { data } = await api.get('/events')
    if (Array.isArray(data)) return data
    if (Array.isArray((data as any)?.items)) return (data as any).items
    return []
  },

  async getEvent(eventId: number): Promise<EventDetail> {
    const { data } = await api.get(`/events/${eventId}`)
    return data
  },

  async listPosts(eventId: number, view: 'all' | 'mine' | 'liked' = 'all'): Promise<CookPost[]> {
    const params = view !== 'all' ? { view } : undefined
    const { data } = await api.get(`/events/${eventId}/posts`, { params })
    return data
  },

  async getPost(eventId: number, postId: number): Promise<CookPost> {
    const { data } = await api.get(`/events/${eventId}/posts/${postId}`)
    return data
  },

  async getPostGlobal(postId: number): Promise<CookPost> {
    const { data } = await api.get(`/posts/${postId}`)
    return data
  },

  async createPost(eventId: number, body: CreatePostDto): Promise<CookPost> {
    const { data } = await api.post(`/events/${eventId}/posts`, body)
    return data
  },

  async updatePost(eventId: number, postId: number, body: { content_title: string; content_text: string }): Promise<CookPost> {
    const { data } = await api.put(`/events/${eventId}/posts/${postId}`, body)
    return data
  },

  async deletePost(eventId: number, postId: number): Promise<void> {
    await api.delete(`/events/${eventId}/posts/${postId}`)
  },

  async likePost(postId: number): Promise<{ likes: number }> {
    const { data } = await api.post(`/posts/${postId}/like`)
    return data
  },

  async unlikePost(postId: number): Promise<{ likes: number }> {
    const { data } = await api.delete(`/posts/${postId}/like`)
    return data
  },

  async myLikes(eventId: number): Promise<number[]> {
    const { data } = await api.get(`/events/${eventId}/likes/me`)
    return (data?.liked_post_ids ?? []) as number[]
  },

  async presignUploads(eventId: number, fileExts: string[]): Promise<{ upload_list: Array<{ upload_url: string; file_url: string; file_name: string }>; expires_in: number }>{
    const { data } = await api.post(`/events/${eventId}/presigned-urls`, { file_exts: fileExts })
    return data
  },

  async listUserPosts(userId: number | string): Promise<UserCookPostsResponse> {
    const cleanId = extractCookUserId(userId) || String(userId ?? '').trim()
    const normalize = (data: any): UserCookPostsResponse => {
      const posts = Array.isArray(data?.posts) ? data.posts : Array.isArray(data) ? data : []
      const events = Array.isArray(data?.events) ? data.events : []
      return { posts, events }
    }
    try {
      const { data } = await api.get(`/users/${cleanId}/cooktest-posts`)
      return normalize(data)
    } catch (err: any) {
      if (err?.response?.status !== 404) throw err
      const { data } = await api.get(`/cooktest/users/${cleanId}/posts`)
      return normalize(data)
    }
  },
}
