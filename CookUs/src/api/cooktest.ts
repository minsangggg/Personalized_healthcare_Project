import api from './axios'

export type EventSummary = {
  event_id: number
  event_name: string
  event_description?: string
  start_date: string
  end_date: string
  post_count: number
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
  likes: number
  created_at: string
}

export type CreatePostDto = {
  content_title: string
  content_text: string
  img_url?: string | null
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

  async listPosts(eventId: number): Promise<CookPost[]> {
    const { data } = await api.get(`/events/${eventId}/posts`)
    return data
  },

  async createPost(eventId: number, body: CreatePostDto): Promise<CookPost> {
    const { data } = await api.post(`/events/${eventId}/posts`, body)
    return data
  },

  async likePost(postId: number): Promise<{ likes: number }> {
    const { data } = await api.post(`/posts/${postId}/like`)
    return data
  },
}
