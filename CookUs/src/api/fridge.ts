import api from './axios'

export type Ingredient = {
  name: string
  quantity?: number
  unit?: string
}

export const fridgeAPI = {
  async listFridge() {
    const { data } = await api.get('/me/ingredients')
    return data as Ingredient[]
  },
  async searchIngredients(q: string) {
    const { data } = await api.get('/ingredients/search', { params: { q } })
    return data as { name: string }[]
  },
  async addIngredientName(name: string): Promise<{ registered: boolean }> {
    const trimmed = name.trim()
    if (!trimmed) return { registered: false }
    try {
      await api.post('/ingredients', { name: trimmed })
      return { registered: true }
    } catch (err: any) {
      if (err?.response?.status === 404) {
        // 서버에 등록 엔드포인트가 없을 수도 있으므로 조용히 무시
        return { registered: false }
      }
      throw err
    }
  },
  async saveFridge(items: Ingredient[], mode: 'merge'|'replace', purgeMissing: boolean) {
    await api.post('/me/ingredients', { items, mode, purgeMissing })
  },
}

