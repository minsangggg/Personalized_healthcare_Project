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
  async saveFridge(items: Ingredient[], mode: 'merge'|'replace', purgeMissing: boolean) {
    await api.post('/me/ingredients', { items, mode, purgeMissing })
  },
}

