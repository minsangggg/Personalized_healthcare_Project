import api from './axios'

export type Recipe = {
  id: number
  title: string
  cook_time?: number | null
  level_nm?: string | null
  ingredient_full?: any
  step_text?: any
  step_tip?: any
}

export type SelectedRecipe = {
  selected_id: number
  recommend_id: number
  recipe_id: number
  title: string
  cooking_time?: number
  difficulty?: string
  selected_date: string
}

export type SelectedRecipesResponse = {
  user_id: string
  count: number
  recipes: SelectedRecipe[]
}

export const normalize = (rec: any): Recipe => ({
  id: Number(rec.id ?? rec.recipe_id),
  title: rec.title ?? rec.recipe_nm_ko ?? '',
  cook_time: rec.cook_time ?? rec.cooking_time ?? null,
  level_nm: rec.level_nm ?? rec.difficulty ?? null,
  ingredient_full: rec.ingredient_full ?? rec.ingredients_text ?? rec.ingredients ?? null,
  step_text: rec.step_text ?? rec.steps_text ?? null,
  step_tip: rec.step_tip ?? rec.tips ?? null,
})

export const recipeAPI = {
  async recommendTop3(): Promise<Recipe[]> {
    const { data } = await api.get('/me/recommendations')
    const list: any[] = Array.isArray(data)
      ? data
      : (data?.recommended_db_candidates ?? data?.recommended ?? [])
    return list.map(normalize).filter(x => Number.isFinite(x.id))
  },

  async selectRecipe(recipeId: number): Promise<void> {
    await api.post('/me/selected-recipe', { recipe_id: recipeId })
  },

  async getSelected(): Promise<SelectedRecipesResponse> {
    const { data } = await api.get('/recipes/selected')
    return data
  },

  async getRecipe(id: number): Promise<Recipe> {
    const { data } = await api.get(`/recipes/${id}`, { withCredentials: true })
    const raw = data?.recipe ?? data
    return normalize(raw)
  },

  async deleteSelected(selectedId: number): Promise<void> {
    await api.delete(`/me/selected-recipe/${selectedId}`)
  },
}
