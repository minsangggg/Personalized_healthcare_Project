import api from './axios'

export type FaqItem = {
  faq_id: number
  question: string
  answer: string
  category?: string | null
  created_at: string
  updated_at?: string
  is_visible?: number
}

export async function fetchFaq(query = '', category?: string, limit = 30): Promise<FaqItem[]> {
  const { data } = await api.get('/faq', { params: { query: query || undefined, category: category || undefined, limit } })
  return (data?.items ?? []) as FaqItem[]
}

export async function fetchFaqCategories(): Promise<string[]> {
  const { data } = await api.get('/faq/categories')
  return (data?.items ?? []) as string[]
}
